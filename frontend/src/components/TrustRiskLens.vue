<template>
  <section class="trust-risk-lens" :data-risk="item.risk_level">
    <div class="trust-risk-lens-head">
      <div>
        <span class="section-kicker">为什么需要你看</span>
        <h4>{{ riskHeadline }}</h4>
      </div>
      <strong>{{ riskToneLabel(item.risk_level) }}</strong>
    </div>

    <p>{{ riskDetail }}</p>

    <div class="trust-risk-reasons">
      <span v-for="reason in riskReasons" :key="reason">{{ translateReason(reason) }}</span>
    </div>

    <div class="trust-risk-evidence-prompt">
      <span>看证据时先问</span>
      <strong>{{ evidenceQuestion }}</strong>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { riskToneLabel } from './trustCenterCopy'
import type { TrustReviewItem } from './trustCenterTypes'

const props = defineProps<{
  item: TrustReviewItem
}>()

const riskReasons = computed(() => props.item.risk_reasons.slice(0, 5))
const riskHeadline = computed(() => {
  if (props.item.why_saved_status === 'AI-inferred') return '这条保存理由是系统猜出来的'
  if (props.item.risk_level === 'critical') return '这条会影响后续回答是否可信'
  if (props.item.has_open_loops) return '这条还连着未闭环问题'
  return '这条理由需要你确认一下'
})

const riskDetail = computed(() => {
  if (props.item.why_saved_status === 'AI-inferred') {
    return '系统可以先猜一个保存理由，但不能把它当成你的真实想法。你确认后，它才适合长期用于找回和回答。'
  }
  if (props.item.has_open_loops) {
    return '这条材料后面还有问题没处理完。确认保存理由后，后续整理会更容易接上。'
  }
  if (props.item.confidence < 0.55) {
    return '这条理由的可信度偏低，最好先看一眼证据再决定。'
  }
  return '这里帮你快速判断这条保存理由能不能继续使用。'
})

const evidenceQuestion = computed(() => {
  if (props.item.why_saved_status === 'AI-inferred') return '这些证据真的能说明你当时为什么保存它吗？'
  if (props.item.has_open_loops) return '这些未闭环问题现在还值得继续追吗？'
  return '这条理由和材料内容是否一致？'
})

function translateReason(reason: string) {
  if (reason.includes('AI-inferred')) return '保存理由来自 AI 猜测'
  if (reason.includes('user-stated')) return '保存理由来自用户原话'
  if (reason.includes('unreviewed')) return '还没有被用户确认'
  if (reason.includes('deferred')) return '之前被稍后处理'
  if (reason.includes('rejected')) return '曾经被拒绝'
  if (reason.includes('below 55')) return '可信度低于 55%'
  if (reason.includes('moderate')) return '可信度中等'
  if (reason.includes('open loop')) return '仍有关联未闭环问题'
  if (reason.includes('no graph evidence')) return '缺少图谱证据路径'
  if (reason.includes('graph evidence path')) return '已有图谱证据路径'
  if (reason.includes('no user review note')) return '还没有用户审查备注'
  return reason
}
</script>
