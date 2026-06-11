<template>
  <section class="trust-risk-lens" :data-risk="item.risk_level">
    <div class="trust-risk-lens-head">
      <div>
        <span class="section-kicker">Risk Lens</span>
        <h4>{{ item.review_focus.headline }}</h4>
      </div>
      <strong>{{ riskToneLabel(item.risk_level) }}</strong>
    </div>

    <p>{{ item.review_focus.detail }}</p>

    <div class="trust-risk-reasons">
      <span v-for="reason in riskReasons" :key="reason">{{ translateReason(reason) }}</span>
    </div>

    <div class="trust-risk-evidence-prompt">
      <span>看证据时先问</span>
      <strong>{{ item.review_focus.evidence_prompt }}</strong>
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

function translateReason(reason: string) {
  if (reason.includes('AI-inferred')) return '保存理由来自 AI 推断'
  if (reason.includes('user-stated')) return '保存理由来自用户原话'
  if (reason.includes('unreviewed')) return '还没有被用户确认'
  if (reason.includes('deferred')) return '之前被稍后处理'
  if (reason.includes('rejected')) return '曾经被拒绝'
  if (reason.includes('below 55')) return '可信度低于 55%'
  if (reason.includes('moderate')) return '可信度中等'
  if (reason.includes('open loop')) return '仍有关联 open loop'
  if (reason.includes('no graph evidence')) return '缺少图谱证据路径'
  if (reason.includes('graph evidence path')) return '已有图谱证据路径'
  if (reason.includes('no user review note')) return '还没有用户审查备注'
  return reason
}
</script>
