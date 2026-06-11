<template>
  <section class="trust-review-inbox">
    <div class="trust-panel-head">
      <div>
        <span class="section-kicker">确认队列</span>
        <h3>需要你确认的材料</h3>
      </div>
      <strong>{{ items.length }} 条</strong>
    </div>

    <div class="trust-filter-row">
      <input v-model="query" placeholder="搜索材料、保存理由或未闭环问题" @input="emitFilters" />
      <select v-model="risk" @change="emitFilters">
        <option value="">全部优先级</option>
        <option value="critical">必须先看</option>
        <option value="high">高优先级</option>
        <option value="medium">需要复核</option>
        <option value="low">低压力</option>
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
        {{ onlyAi ? '只看 AI 猜测' : '同时看用户原话' }}
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
          <small>{{ reviewStatusLabel(item.review_status) }}</small>
        </label>
        <button class="trust-review-main" type="button" @click="$emit('selectReview', item.source_id)">
          <strong>{{ item.title }}</strong>
          <p>{{ compactReason(item) }}</p>
        </button>
        <div class="trust-review-micro-meta">
          <span>{{ boundaryLabel(item.why_saved_status) }}</span>
          <span>{{ trustSpaceLabel(item.space_name) }}</span>
          <span>{{ Math.round(item.confidence * 100) }}%</span>
          <span>{{ item.evidence_count }} 证据</span>
          <span v-if="item.open_loops.length">{{ item.open_loops.length }} 个未闭环问题</span>
        </div>
      </article>
      <p v-if="!items.length" class="trust-empty">当前筛选下没有待审查项。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { cleanTrustText, reviewStatusLabel, trustSpaceLabel } from './trustCenterCopy'
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
const compactReasonLimit = 64

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
  if (level === 'critical') return '必须先看'
  if (level === 'high') return '高优先级'
  if (level === 'medium') return '需要复核'
  return '低压力'
}

function compactReason(item: TrustReviewItem) {
  const text = cleanTrustText(item.why_saved || item.summary || '这条材料还没有稳定的保存理由。')
  return text.length > compactReasonLimit ? `${text.slice(0, compactReasonLimit)}...` : text
}

function boundaryLabel(status: string) {
  if (status === 'user-stated') return '用户原话'
  if (status === 'AI-inferred') return 'AI 猜测'
  return status || '边界未知'
}

</script>
