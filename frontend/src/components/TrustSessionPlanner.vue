<template>
  <section class="trust-session-planner" aria-label="Trust review session planner">
    <div class="trust-session-copy">
      <span class="section-kicker">Review Session</span>
      <h2>{{ sessionModeLabel(mode) }}</h2>
      <p>{{ sessionModeDescription(mode) }}</p>
    </div>

    <div class="trust-session-modes" role="tablist" aria-label="选择审查模式">
      <button
        v-for="option in modeOptions"
        :key="option.id"
        type="button"
        :class="{ active: option.id === mode }"
        :aria-selected="option.id === mode"
        @click="$emit('modeChanged', option.id)"
      >
        <strong>{{ option.label }}</strong>
        <span>{{ option.count }} 条</span>
      </button>
    </div>

    <div class="trust-session-next-step">
      <span>建议下一步</span>
      <strong>{{ nextStepHeadline }}</strong>
      <p>{{ nextStepDetail }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { sessionModeDescription, sessionModeLabel } from './trustCenterCopy'
import type {
  TrustDiagnostics,
  TrustOpenLoopPayload,
  TrustReviewPayload,
  TrustReviewSessionMode,
} from './trustCenterTypes'

const props = defineProps<{
  mode: TrustReviewSessionMode
  review: TrustReviewPayload
  openLoops: TrustOpenLoopPayload
  diagnostics: TrustDiagnostics | null
}>()

defineEmits<{
  modeChanged: [mode: TrustReviewSessionMode]
}>()

const urgentCount = computed(() => props.review.summary.critical + props.review.summary.high)

const modeOptions = computed(() => [
  {
    id: 'high-risk' as const,
    label: '高风险',
    count: urgentCount.value,
  },
  {
    id: 'quick-clear' as const,
    label: '快速清理',
    count: props.review.summary.low + props.review.summary.medium,
  },
  {
    id: 'open-loops' as const,
    label: 'Open loop',
    count: props.openLoops.summary.total,
  },
  {
    id: 'all' as const,
    label: '全部',
    count: props.review.summary.total,
  },
])

const nextStepHeadline = computed(() => {
  if (props.mode === 'high-risk' && urgentCount.value) return `先处理 ${urgentCount.value} 条高优先级判断`
  if (props.mode === 'quick-clear') return '用低压力项目降低队列噪音'
  if (props.mode === 'open-loops') return `把 ${props.openLoops.summary.total} 个悬而未决问题变成下一步`
  if (props.diagnostics?.warnings.length) return '先扫一眼诊断警告'
  return '从第一条待审查材料开始'
})

const nextStepDetail = computed(() => {
  if (props.mode === 'high-risk') return '优先看 AI 推断、低可信度和缺少用户确认的材料。'
  if (props.mode === 'quick-clear') return '适合一次处理多条低风险记录，但仍保留改写和拒绝出口。'
  if (props.mode === 'open-loops') return '先判断问题是否还有效，再决定 next、resolved 或 dismissed。'
  return '完整模式不会隐藏信息，适合最终复盘或提交前检查。'
})
</script>
