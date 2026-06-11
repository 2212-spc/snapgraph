<template>
  <section v-if="report || session" class="trust-quiet-report">
    <div>
      <span class="section-kicker">信任概览</span>
      <strong>{{ headline }}</strong>
      <p>{{ quietSummary }}</p>
    </div>

    <details>
      <summary>
        <span>展开详细概览</span>
        <strong>{{ sectionCount }} 类信息</strong>
      </summary>
      <div class="trust-quiet-report-grid">
        <article v-for="section in visibleSections" :key="section.id">
          <span>{{ sectionTitle(section.title) }}</span>
          <strong>{{ section.count }}</strong>
          <p>{{ section.quiet_copy || section.summary }}</p>
        </article>
      </div>
      <div v-if="visibleActions.length" class="trust-quiet-action-list">
        <p v-for="action in visibleActions" :key="action.source_id">
          {{ action.title }} - {{ riskLabel(action.risk_level) }} - {{ actionSummary(action.summary) }}
        </p>
      </div>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { riskToneLabel } from './trustCenterCopy'
import type { TrustReportPayload, TrustRiskLevel, TrustSessionPayload } from './trustCenterTypes'

const props = defineProps<{
  report?: TrustReportPayload
  session?: TrustSessionPayload
}>()

const headline = computed(() => {
  const highCount = Number(props.report?.metrics.risk_count || 0)
  const aiCount = Number(props.report?.metrics.ai_count || 0)
  if (highCount) return `还有 ${highCount} 条内容需要优先确认`
  if (aiCount) return `还有 ${aiCount} 条 AI 猜测需要你看一眼`
  if (props.session?.next_step?.title) return `下一步：${props.session.next_step.title}`
  return '当前没有急着处理的信任问题'
})

const quietSummary = computed(() => {
  const total = Number(props.report?.metrics.total_count || props.session?.total_count || 0)
  const aiCount = Number(props.report?.metrics.ai_count || 0)
  const loopCount = Number(props.report?.metrics.loops_count || 0)
  if (total) return `这轮共有 ${total} 条材料，${aiCount} 条来自 AI 猜测，${loopCount} 条连着未闭环问题。详细内容默认收起。`
  return '详细内容默认收起，避免一打开就看到太多信息。'
})

const sectionCount = computed(() => props.report?.sections.length || 0)
const visibleSections = computed(() => props.report?.sections.slice(0, props.report.display_policy.max_visible_sections || 2) || [])
const visibleActions = computed(() => props.report?.action_queue.slice(0, props.report.display_policy.max_visible_actions || 3) || [])

function riskLabel(level: TrustRiskLevel) {
  return riskToneLabel(level)
}

function sectionTitle(title: string) {
  if (title.toLowerCase().includes('risk')) return '需要优先确认'
  if (title.toLowerCase().includes('ai')) return 'AI 猜测'
  if (title.toLowerCase().includes('loop')) return '未闭环问题'
  if (title.toLowerCase().includes('history')) return '审查记录'
  if (title.toLowerCase().includes('evidence')) return '证据情况'
  return title || '概览'
}

function actionSummary(summary: string) {
  if (!summary) return '建议先看右侧材料详情。'
  return summary
    .replace(/\bAI-inferred\b/g, 'AI 猜测')
    .replace(/\bopen loops?\b/gi, '未闭环问题')
    .replace(/\breview\b/gi, '确认')
}
</script>
