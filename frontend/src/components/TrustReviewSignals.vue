<template>
  <div class="trust-review-signals" :data-compact="compact ? 'true' : 'false'">
    <span :class="`risk-${item.risk_level}`">{{ riskToneLabel(item.risk_level) }}</span>
    <span>{{ boundaryLabel(item.why_saved_status) }}</span>
    <span>{{ confidenceLabel(item.confidence) }}</span>
    <span>{{ item.evidence_count }} 条证据</span>
    <span v-if="item.trust_signals.open_loop_count">{{ item.trust_signals.open_loop_count }} 个 open loop</span>
    <span v-if="item.trust_signals.topic_count">{{ item.trust_signals.topic_count }} 个主题</span>
    <span v-if="item.trust_signals.has_review_note">有审查备注</span>
  </div>
</template>

<script setup lang="ts">
import { boundaryLabel, confidenceLabel, riskToneLabel } from './trustCenterCopy'
import type { TrustReviewItem } from './trustCenterTypes'

withDefaults(
  defineProps<{
    item: TrustReviewItem
    compact?: boolean
  }>(),
  {
    compact: false,
  },
)
</script>
