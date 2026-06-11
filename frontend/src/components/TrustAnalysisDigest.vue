<template>
  <section v-if="analysis" class="trust-analysis-digest">
    <div class="trust-analysis-digest-head">
      <div>
        <span class="section-kicker">Compressed analysis</span>
        <strong>{{ analysis.quiet_summary }}</strong>
      </div>
      <span>{{ analysis.trust_score.label }} - {{ analysis.trust_score.score }}</span>
    </div>

    <p>{{ analysis.evidence_compression.summary }}</p>

    <div class="trust-analysis-pills">
      <span>{{ analysis.review_path.current_stage }}</span>
      <span>{{ analysis.context_completeness.percent }}% context</span>
      <span>{{ analysis.hidden_depth_count }} hidden details</span>
    </div>

    <details>
      <summary>
        <span>Decision impact</span>
        <strong>{{ previewCount }} actions</strong>
      </summary>
      <div class="trust-analysis-impact-list">
        <article v-for="preview in decisionPreviews" :key="preview.action">
          <span>{{ preview.action }}</span>
          <strong>{{ preview.summary }}</strong>
          <p>{{ preview.recall_effect }}</p>
        </article>
      </div>
    </details>

    <details>
      <summary>
        <span>Evidence compression</span>
        <strong>{{ analysis.evidence_compression.path_count }} paths</strong>
      </summary>
      <div class="trust-analysis-evidence-columns">
        <div>
          <span>Supporting</span>
          <p v-for="line in analysis.evidence_compression.supporting" :key="line">{{ line }}</p>
        </div>
        <div>
          <span>Needs confirmation</span>
          <p v-for="line in analysis.evidence_compression.needs_confirmation" :key="line">{{ line }}</p>
        </div>
      </div>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TrustDecisionPreview, TrustReviewDetailPayload, TrustReviewStatus } from './trustCenterTypes'

const props = defineProps<{
  detail: TrustReviewDetailPayload
}>()

const analysis = computed(() => props.detail.analysis || props.detail.item.analysis)

const decisionPreviews = computed(() => {
  const previews = analysis.value?.decision_preview || {}
  return (Object.entries(previews) as Array<[Exclude<TrustReviewStatus, 'unreviewed'>, TrustDecisionPreview]>).map(
    ([action, preview]) => ({
      action,
      ...preview,
    }),
  )
})

const previewCount = computed(() => decisionPreviews.value.length)
</script>
