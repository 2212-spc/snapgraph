<template>
  <section class="trust-center-view">
    <header class="trust-center-header">
      <div>
        <p class="eyebrow">Trust Operations</p>
        <h1>信任运营中心</h1>
        <p>把 AI 推断、证据路径、open loop 和审查历史放在一个可操作的工作台里。</p>
      </div>
      <button class="paper-button" type="button" :disabled="busy" @click="$emit('refresh')">刷新</button>
    </header>

    <section class="trust-summary-grid">
      <article v-for="metric in metrics" :key="metric.label" :class="metric.tone">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.caption }}</small>
      </article>
    </section>

    <TrustBatchActionBar
      :source-ids="selectedSourceIds"
      :busy="busy"
      @batch-action="$emit('batchAction', $event)"
    />

    <div class="trust-workbench-grid">
      <TrustReviewInbox
        :items="review.items"
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
import { computed } from 'vue'
import TrustBatchActionBar from './TrustBatchActionBar.vue'
import TrustDiagnosticsPanel from './TrustDiagnosticsPanel.vue'
import TrustOpenLoopPanel from './TrustOpenLoopPanel.vue'
import TrustReviewDetail from './TrustReviewDetail.vue'
import TrustReviewInbox from './TrustReviewInbox.vue'
import type {
  TrustBatchPayload,
  TrustDiagnostics,
  TrustOpenLoopPayload,
  TrustOpenLoopUpdatePayload,
  TrustReviewDetailPayload,
  TrustReviewFilters,
  TrustReviewPayload,
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

const metrics = computed(() => [
  {
    label: 'critical',
    value: props.review.summary.critical,
    caption: '必须先判断的 AI 推断',
    tone: 'tone-critical',
  },
  {
    label: 'high',
    value: props.review.summary.high,
    caption: '高风险证据或未审查项',
    tone: 'tone-high',
  },
  {
    label: 'open loops',
    value: props.openLoops.summary.total,
    caption: '还没有闭环的问题',
    tone: 'tone-loop',
  },
  {
    label: 'history',
    value: props.diagnostics?.history_count || 0,
    caption: '已经写入的审查记录',
    tone: 'tone-history',
  },
])
</script>
