<template>
  <section class="trust-center-view">
    <header class="trust-center-header">
      <div>
        <p class="eyebrow">信任</p>
        <h1>检查 AI 猜测有没有冒充你的想法</h1>
        <p>把 AI 推断、证据路径、open loop 和审查历史放在一个可操作的工作台里。</p>
      </div>
      <button class="paper-button" type="button" :disabled="busy" @click="$emit('refresh')">刷新</button>
    </header>

    <section class="memory-quick-actions trust-home-actions" aria-label="信任检查快捷入口">
      <button
        :class="quickActionClass('high-risk')"
        type="button"
        :aria-pressed="selectedSessionMode === 'high-risk'"
        :aria-label="trustSessionModeLabel('high-risk')"
        :disabled="busy"
        @click="selectSessionMode('high-risk')"
      >
        <span>先确认 AI 猜测</span>
        <strong>{{ urgentReviewCount ? `${urgentReviewCount} 条最该看` : '没有高压项' }}</strong>
        <b v-if="selectedSessionMode === 'high-risk'" class="trust-quick-action-state">当前</b>
        <small>看系统有没有替你乱猜保存理由。</small>
      </button>
      <button
        :class="quickActionClass('open-loops')"
        type="button"
        :aria-pressed="selectedSessionMode === 'open-loops'"
        :aria-label="trustSessionModeLabel('open-loops')"
        :disabled="busy"
        @click="selectSessionMode('open-loops')"
      >
        <span>处理未闭环问题</span>
        <strong>{{ props.openLoops.summary.total ? `${props.openLoops.summary.total} 个问题` : '暂时没有问题' }}</strong>
        <b v-if="selectedSessionMode === 'open-loops'" class="trust-quick-action-state">当前</b>
        <small>把悬着的问题变成下一步或标记已解决。</small>
      </button>
      <button
        :class="quickActionClass('all')"
        type="button"
        :aria-pressed="selectedSessionMode === 'all'"
        :aria-label="trustSessionModeLabel('all')"
        :disabled="busy"
        @click="selectSessionMode('all')"
      >
        <span>查看全部材料</span>
        <strong>{{ props.review.summary.total }} 条记录</strong>
        <b v-if="selectedSessionMode === 'all'" class="trust-quick-action-state">当前</b>
        <small>需要复盘时，再看完整队列和诊断。</small>
      </button>
    </section>

    <section class="trust-focus-strip trust-simple-path" aria-label="这页要做什么">
      <div class="trust-focus-primary">
        <span class="section-kicker">现在要做什么</span>
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

    <details class="trust-how-it-works">
      <summary>
        <span>这页怎么用</span>
        <strong>3 步确认</strong>
      </summary>
      <section class="trust-simple-steps" aria-label="信任检查步骤">
        <article v-for="step in simpleSteps" :key="step.title">
          <span>{{ step.kicker }}</span>
          <strong>{{ step.title }}</strong>
          <p>{{ step.detail }}</p>
        </article>
      </section>
    </details>

    <TrustBatchActionBar
      v-if="selectedSourceIds.length"
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

    <details class="trust-advanced-review">
      <summary>
        <div>
          <span>高级检查</span>
          <strong>证据报告、诊断和未闭环问题</strong>
          <p>平时不用打开；当你想复盘原因、检查证据或处理系统诊断时再看。</p>
        </div>
        <span>{{ advancedItemCount }} 项</span>
      </summary>

      <div class="trust-advanced-content">
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

        <div class="trust-secondary-grid">
          <TrustOpenLoopPanel
            :payload="openLoops"
            :busy="busy"
            @update-loop="(loopId, payload) => $emit('updateOpenLoop', loopId, payload)"
          />
          <TrustDiagnosticsPanel :diagnostics="diagnostics" />
        </div>
      </div>
    </details>
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
const advancedItemCount = computed(() => {
  return props.openLoops.summary.total + (props.diagnostics?.warnings.length || 0) + (props.review.report?.sections.length || 0)
})

function selectSessionMode(mode: TrustReviewSessionMode) {
  selectedSessionMode.value = mode
}

function quickActionClass(mode: TrustReviewSessionMode) {
  return {
    'memory-quick-action': true,
    active: selectedSessionMode.value === mode,
    primary: selectedSessionMode.value === mode && mode === 'high-risk',
  }
}

function trustSessionModeLabel(mode: TrustReviewSessionMode) {
  if (mode === 'high-risk') return '先确认 AI 猜测'
  if (mode === 'open-loops') return '处理未闭环问题'
  if (mode === 'all') return '查看全部材料'
  return '快速清理'
}

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
    return `先确认 ${props.review.summary.critical} 条最敏感的 AI 猜测`
  }
  if (props.review.summary.high) {
    return `先看 ${props.review.summary.high} 条最容易误导你的材料`
  }
  if (props.openLoops.summary.total) {
    return `把 ${props.openLoops.summary.total} 个未闭环问题变成下一步`
  }
  return '当前没有急着处理的信任问题'
})

const focusCaption = computed(() => {
  if (urgentReviewCount.value) {
    return '先确认这些保存理由是不是你的真实想法。确认后，未来找回和回答才不会把系统猜测当成事实。'
  }
  if (props.review.summary.unreviewed) {
    return '剩下的内容压力不高，可以像整理知识库一样慢慢确认。'
  }
  return '信任边界已经比较干净，继续收集材料时再补充用户确认过的理由。'
})

const compactMetrics = computed(() => [
  {
    label: '未判断',
    value: props.review.summary.unreviewed,
    caption: `${urgentReviewCount.value} 条先看`,
    tone: 'tone-critical',
  },
  {
    label: 'AI 猜测',
    value: props.review.summary.ai_inferred,
    caption: `${props.review.summary.user_stated} 条用户原话`,
    tone: 'tone-high',
  },
  {
    label: '未闭环',
    value: props.openLoops.summary.total,
    caption: `${props.openLoops.summary.by_state.next || 0} 个已成下一步`,
    tone: 'tone-loop',
  },
  {
    label: '已确认',
    value: props.review.summary.confirmed + props.review.summary.rewritten,
    caption: `${props.diagnostics?.history_count || 0} 条记录`,
    tone: 'tone-history',
  },
])

const simpleSteps = computed(() => [
  {
    kicker: '第一步',
    title: '看系统猜了什么',
    detail: '左侧只列需要你确认的材料，不先展开全部证据。',
  },
  {
    kicker: '第二步',
    title: '确认、改写或拒绝',
    detail: '右侧给出当前材料和判断按钮，拿不准再展开证据。',
  },
  {
    kicker: '结果',
    title: '以后找回更可靠',
    detail: '确认过的理由会进入记忆，AI 猜测会继续保持标记。',
  },
])
</script>
