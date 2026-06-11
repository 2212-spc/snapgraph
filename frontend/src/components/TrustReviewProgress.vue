<template>
  <section class="trust-review-progress" aria-label="Trust review progress">
    <div>
      <span>本轮范围</span>
      <strong>{{ items.length }} 条</strong>
      <p>{{ modeSummary }}</p>
    </div>
    <div>
      <span>已选择</span>
      <strong>{{ selectedCount }} 条</strong>
      <p>{{ selectedHint }}</p>
    </div>
    <div>
      <span>下一步</span>
      <strong>{{ nextStep }}</strong>
      <p>{{ nextStepDetail }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { sessionModeLabel } from './trustCenterCopy'
import type { TrustReviewItem, TrustReviewSessionMode, TrustSummary } from './trustCenterTypes'

const props = defineProps<{
  mode: TrustReviewSessionMode
  items: TrustReviewItem[]
  selectedSourceIds: string[]
  summary: TrustSummary
}>()

const selectedCount = computed(() => props.selectedSourceIds.length)
const highPressureCount = computed(() => props.summary.critical + props.summary.high)

const modeSummary = computed(() => {
  if (!props.items.length) return `${sessionModeLabel(props.mode)}下没有待处理项目。`
  return `${sessionModeLabel(props.mode)}正在展示 ${props.items.length} 条材料。`
})

const selectedHint = computed(() => {
  if (selectedCount.value) return '可以批量确认、拒绝或稍后处理。'
  return '先勾选队列项，或直接打开右侧单条审查。'
})

const nextStep = computed(() => {
  if (!props.items.length) return '切换模式'
  if (selectedCount.value) return '执行批量判断'
  if (highPressureCount.value) return '打开第一条高风险'
  return '继续清理队列'
})

const nextStepDetail = computed(() => {
  if (!props.items.length) return '当前筛选没有结果，可以切到全部或收集更多材料。'
  if (selectedCount.value) return '批量动作适合确定性较高的项目，拿不准时用单条审查。'
  if (highPressureCount.value) return '优先处理会影响未来回答可信度的 AI 推断。'
  return '剩余项目压力较低，可以按空间或关键词慢慢处理。'
})
</script>
