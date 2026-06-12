<template>
  <section v-if="analysis" class="trust-analysis-digest">
    <div class="trust-analysis-digest-head">
      <div>
        <span class="section-kicker">系统简短判断</span>
        <strong>{{ digestHeadline }}</strong>
      </div>
      <span>{{ scoreLabel }} - {{ analysis.trust_score.score }}</span>
    </div>

    <p>{{ evidenceSummary }}</p>

    <div class="trust-analysis-pills">
      <span>{{ stageLabel }}</span>
      <span>{{ analysis.context_completeness.percent }}% 上下文</span>
      <span>{{ analysis.hidden_depth_count }} 条细节已收起</span>
    </div>

    <details>
      <summary>
        <span>会影响什么</span>
        <strong>{{ previewCount }} 个动作</strong>
      </summary>
      <div class="trust-analysis-impact-list">
        <article v-for="preview in decisionPreviews" :key="preview.action">
          <span>{{ preview.label }}</span>
          <strong>{{ preview.description }}</strong>
          <p>{{ previewText(preview.recall_effect) }}</p>
        </article>
      </div>
    </details>

    <details>
      <summary>
        <span>证据摘要</span>
        <strong>{{ analysis.evidence_compression.path_count }} 条路径</strong>
      </summary>
      <div class="trust-analysis-evidence-columns">
        <div>
          <span>支持这条判断</span>
          <p v-for="line in analysis.evidence_compression.supporting" :key="line">{{ line }}</p>
        </div>
        <div>
          <span>还需要确认</span>
          <p v-for="line in analysis.evidence_compression.needs_confirmation" :key="line">{{ line }}</p>
        </div>
      </div>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { decisionActionDescription, decisionActionLabel } from './trustCenterCopy'
import type { TrustDecisionPreview, TrustReviewDetailPayload, TrustReviewStatus } from './trustCenterTypes'

const props = defineProps<{
  detail: TrustReviewDetailPayload
}>()

const analysis = computed(() => props.detail.analysis || props.detail.item.analysis)
const digestHeadline = computed(() => {
  if (props.detail.item.why_saved_status === 'AI-inferred') return '这条保存理由来自 AI 猜测，建议你确认后再长期使用。'
  if (props.detail.item.has_open_loops) return '这条材料还连着未闭环问题，适合顺手整理。'
  return '这条保存理由可以快速确认，必要时再展开证据。'
})

const evidenceSummary = computed(() => {
  const compression = analysis.value?.evidence_compression
  if (!compression) return '这里会把证据压缩成支持点和待确认点。'
  return `系统找到 ${compression.path_count} 条证据路径，其中 ${compression.supporting.length} 条支持判断，${compression.needs_confirmation.length} 条还需要你确认。`
})

const scoreLabel = computed(() => {
  const label = analysis.value?.trust_score.label || ''
  if (label.includes('critical')) return '必须先看'
  if (label.includes('high')) return '高优先级'
  if (label.includes('needs')) return '需要确认'
  if (label.includes('stable')) return '比较稳定'
  return '需要确认'
})

const stageLabel = computed(() => {
  const stage = analysis.value?.review_path.current_stage || ''
  if (stage.includes('evidence')) return '先看证据'
  if (stage.includes('decision')) return '等待判断'
  if (stage.includes('complete')) return '已完成'
  return '等待判断'
})

const decisionPreviews = computed(() => {
  const previews = analysis.value?.decision_preview || {}
  return (Object.entries(previews) as Array<[Exclude<TrustReviewStatus, 'unreviewed'>, TrustDecisionPreview]>).map(
    ([action, preview]) => ({
      action,
      label: decisionActionLabel(action),
      description: decisionActionDescription(action),
      ...preview,
    }),
  )
})

const previewCount = computed(() => decisionPreviews.value.length)

function previewText(text: string) {
  if (!text) return '这个动作会影响以后怎么找回这条材料。'
  return text
    .replace(/\brecall\b/gi, '找回')
    .replace(/\bgraph\b/gi, '关系')
    .replace(/\bopen loops?\b/gi, '未闭环问题')
    .replace(/\bAI-inferred\b/g, 'AI 猜测')
}
</script>
