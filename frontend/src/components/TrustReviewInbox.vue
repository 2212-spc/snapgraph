<template>
  <section class="trust-review-inbox">
    <div class="trust-panel-head">
      <div>
        <span class="section-kicker">Review Inbox</span>
        <h3>待判断</h3>
      </div>
      <strong>{{ items.length }} 条</strong>
    </div>

    <div class="trust-filter-row">
      <input v-model="query" placeholder="搜索标题、理由、open loop" @input="emitFilters" />
      <select v-model="risk" @change="emitFilters">
        <option value="">全部风险</option>
        <option value="critical">critical</option>
        <option value="high">high</option>
        <option value="medium">medium</option>
        <option value="low">low</option>
      </select>
      <select v-model="status" @change="emitFilters">
        <option value="">全部状态</option>
        <option value="unreviewed">未审查</option>
        <option value="deferred">稍后</option>
        <option value="confirmed">已确认</option>
        <option value="rewritten">已改写</option>
        <option value="rejected">已拒绝</option>
      </select>
      <button class="ghost-button" type="button" @click="onlyAi = !onlyAi; emitFilters()">
        {{ onlyAi ? '只看 AI 推断' : '包含用户原话' }}
      </button>
    </div>

    <div class="trust-review-list">
      <article
        v-for="item in items"
        :key="item.source_id"
        class="trust-review-card"
        :class="[`risk-${item.risk_level}`, { selected: selectedSourceIds.includes(item.source_id) }]"
      >
        <label class="trust-select-line">
          <input
            type="checkbox"
            :checked="selectedSourceIds.includes(item.source_id)"
            @change="$emit('toggleSelection', item.source_id)"
          />
          <span>{{ riskLabel(item.risk_level) }}</span>
          <small>{{ item.review_status }}</small>
        </label>
        <button class="trust-review-main" type="button" @click="$emit('selectReview', item.source_id)">
          <strong>{{ item.title }}</strong>
          <p>{{ compactReason(item) }}</p>
        </button>
        <div class="trust-review-action-hint">
          {{ actionHint(item) }}
        </div>
        <div class="trust-review-compact-meta">
          <span>{{ boundaryLabel(item.why_saved_status) }}</span>
          <span>{{ item.space_name || '未分配空间' }}</span>
          <span>可信度 {{ Math.round(item.confidence * 100) }}%</span>
          <span v-if="item.open_loops.length">{{ item.open_loops.length }} 个 open loop</span>
        </div>
      </article>
      <p v-if="!items.length" class="trust-empty">当前筛选下没有待审查项。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { TrustReviewFilters, TrustReviewItem, TrustRiskLevel } from './trustCenterTypes'

const props = defineProps<{
  items: TrustReviewItem[]
  selectedSourceIds: string[]
  filters: TrustReviewFilters
}>()

const emit = defineEmits<{
  selectReview: [sourceId: string]
  toggleSelection: [sourceId: string]
  filterChanged: [filters: TrustReviewFilters]
}>()

const query = ref(props.filters.q || '')
const risk = ref(props.filters.risk || '')
const status = ref(props.filters.status || '')
const onlyAi = ref(props.filters.inferred === 'ai')

watch(
  () => props.filters,
  (filters) => {
    query.value = filters.q || ''
    risk.value = filters.risk || ''
    status.value = filters.status || ''
    onlyAi.value = filters.inferred === 'ai'
  },
)

function emitFilters() {
  emit('filterChanged', {
    q: query.value.trim(),
    risk: risk.value,
    status: status.value,
    inferred: onlyAi.value ? 'ai' : '',
  })
}

function riskLabel(level: TrustRiskLevel) {
  if (level === 'critical') return 'critical'
  if (level === 'high') return 'high'
  if (level === 'medium') return 'medium'
  return 'low'
}

function compactReason(item: TrustReviewItem) {
  const text = item.why_saved || item.summary || '这条材料还没有稳定的保存理由。'
  return text.length > 108 ? `${text.slice(0, 108)}...` : text
}

function boundaryLabel(status: string) {
  if (status === 'user-stated') return '用户原话'
  if (status === 'AI-inferred') return 'AI 推断'
  return status || '边界未知'
}

function actionHint(item: TrustReviewItem) {
  if (item.risk_level === 'critical') return '建议现在处理：确认、改写或拒绝这条推断。'
  if (item.risk_level === 'high') return '建议优先扫一眼证据，再决定是否确认。'
  if (item.open_loops.length) return '可以转成下一步，避免问题继续悬空。'
  return item.recommended_action || '低压力项目，可以稍后批量处理。'
}
</script>
