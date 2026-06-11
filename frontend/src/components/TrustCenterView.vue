<template>
  <section class="trust-center-view">
    <header class="trust-center-header">
      <div>
        <p class="eyebrow">Trust Operations</p>
        <h1>信任工作台</h1>
        <p>先处理高风险判断，证据、open loop 和诊断按需展开。</p>
      </div>
      <button class="paper-button" type="button" :disabled="busy" @click="$emit('refresh')">刷新</button>
    </header>

    <section class="trust-focus-strip" aria-label="信任工作台焦点">
      <div class="trust-focus-primary">
        <span class="section-kicker">今日焦点</span>
        <h2>{{ focusHeadline }}</h2>
        <p>{{ focusCaption }}</p>
      </div>
      <div class="trust-focus-stats">
        <article v-for="metric in compactMetrics" :key="metric.label" :class="metric.tone">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.caption }}</small>
        </article>
      </div>
    </section>

    <TrustSessionPlanner
      :mode="selectedSessionMode"
      :review="review"
      :open-loops="openLoops"
      :diagnostics="diagnostics"
      @mode-changed="selectedSessionMode = $event"
    />

    <TrustQuietReport :session="review.session" :report="review.report" />

    <TrustReviewProgress
      :mode="selectedSessionMode"
      :items="sessionItems"
      :selected-source-ids="selectedSourceIds"
      :summary="review.summary"
    />

    <TrustBatchActionBar
      :source-ids="selectedSourceIds"
      :busy="busy"
      @batch-action="$emit('batchAction', $event)"
    />

    <div class="trust-workbench-grid">
      <TrustReviewInbox
        :items="sessionItems"
        :selected-source-ids="selectedSourceIds"
        :filters="filters"
        @select-review="$emit('selectReview', $event)"
        @toggle-selection="$emit('toggleReviewSelection', $event)"
        @filter-changed="$emit('filterChanged', $event)"
      />

      <TrustReviewDetail
        :detail="detail"
        :busy="busy"
        @close="$emit('selectReview', '')"
        @batch-action="$emit('batchAction', $event)"
      />
    </div>

    <div class="trust-secondary-grid">
      <TrustOpenLoopPanel
        :payload="openLoops"
        :busy="busy"
        @update-loop="(loopId, payload) => $emit('updateOpenLoop', loopId, payload)"
      />
      <TrustDiagnosticsPanel :diagnostics="diagnostics" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import TrustBatchActionBar from './TrustBatchActionBar.vue'
import TrustDiagnosticsPanel from './TrustDiagnosticsPanel.vue'
import TrustOpenLoopPanel from './TrustOpenLoopPanel.vue'
import TrustQuietReport from './TrustQuietReport.vue'
import TrustReviewProgress from './TrustReviewProgress.vue'
import TrustReviewDetail from './TrustReviewDetail.vue'
import TrustReviewInbox from './TrustReviewInbox.vue'
import TrustSessionPlanner from './TrustSessionPlanner.vue'
import type {
  TrustBatchPayload,
  TrustDiagnostics,
  TrustOpenLoopPayload,
  TrustOpenLoopUpdatePayload,
  TrustReviewDetailPayload,
  TrustReviewFilters,
  TrustReviewItem,
  TrustReviewPayload,
  TrustReviewSessionMode,
} from './trustCenterTypes'

const props = defineProps<{
  review: TrustReviewPayload
  detail: TrustReviewDetailPayload | null
  openLoops: TrustOpenLoopPayload
  diagnostics: TrustDiagnostics | null
  selectedSourceIds: string[]
  filters: TrustReviewFilters
  busy: boolean
}>()

defineEmits<{
  refresh: []
  selectReview: [sourceId: string]
  toggleReviewSelection: [sourceId: string]
  filterChanged: [filters: TrustReviewFilters]
  batchAction: [payload: TrustBatchPayload]
  updateOpenLoop: [loopId: string, payload: TrustOpenLoopUpdatePayload]
}>()

const selectedSessionMode = ref<TrustReviewSessionMode>('high-risk')
const urgentReviewCount = computed(() => props.review.summary.critical + props.review.summary.high)

const sessionItems = computed(() => {
  const items = props.review.items
  const filtered = items.filter((item) => matchesSessionMode(item, selectedSessionMode.value))
  return filtered.length ? filtered : items
})

function matchesSessionMode(item: TrustReviewItem, mode: TrustReviewSessionMode) {
  if (mode === 'high-risk') {
    return item.risk_level === 'critical' || item.risk_level === 'high' || item.needs_review
  }
  if (mode === 'quick-clear') {
    return item.risk_level === 'medium' || item.risk_level === 'low' || item.review_status !== 'unreviewed'
  }
  if (mode === 'open-loops') {
    return item.has_open_loops
  }
  return true
}

const focusHeadline = computed(() => {
  if (props.review.summary.critical) {
    return `先确认 ${props.review.summary.critical} 条 critical 推断`
  }
  if (props.review.summary.high) {
    return `先扫完 ${props.review.summary.high} 条高风险判断`
  }
  if (props.openLoops.summary.total) {
    return `把 ${props.openLoops.summary.total} 个 open loop 变成下一步`
  }
  return '当前没有高压审查项'
})

const focusCaption = computed(() => {
  if (urgentReviewCount.value) {
    return '默认只展示最能帮助你做决定的信息；需要证据、历史和诊断时再展开。'
  }
  if (props.review.summary.unreviewed) {
    return '剩余项目风险较低，可以按空间或关键词慢慢清理，不需要一次看完所有细节。'
  }
  return '信任边界已经比较干净，后续重点是继续沉淀用户确认过的理由。'
})

const compactMetrics = computed(() => [
  {
    label: '需判断',
    value: props.review.summary.unreviewed,
    caption: `${urgentReviewCount.value} 条高优先级`,
    tone: 'tone-critical',
  },
  {
    label: 'AI 推断',
    value: props.review.summary.ai_inferred,
    caption: `${props.review.summary.user_stated} 条用户原话`,
    tone: 'tone-high',
  },
  {
    label: 'open loop',
    value: props.openLoops.summary.total,
    caption: `${props.openLoops.summary.by_state.next || 0} 个下一步`,
    tone: 'tone-loop',
  },
  {
    label: '已审查',
    value: props.diagnostics?.history_count || 0,
    caption: '可追溯记录',
    tone: 'tone-history',
  },
])
</script>
