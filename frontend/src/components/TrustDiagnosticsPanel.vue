<template>
  <section class="trust-diagnostics-panel">
    <div class="trust-panel-head">
      <div>
        <span class="section-kicker">Diagnostics</span>
        <h3>信任诊断</h3>
      </div>
      <strong>{{ diagnostics?.queue_total || 0 }}</strong>
    </div>

    <p class="trust-diagnostics-summary">{{ diagnosticsSummary }}</p>
    <p class="trust-diagnostics-guidance">{{ diagnosticsGuidance }}</p>

    <div class="trust-diagnostics-grid">
      <div>
        <span>AI 未审查</span>
        <strong>{{ diagnostics?.ai_inferred_unreviewed || 0 }}</strong>
      </div>
      <div>
        <span>critical</span>
        <strong>{{ diagnostics?.critical_count || 0 }}</strong>
      </div>
      <div>
        <span>high</span>
        <strong>{{ diagnostics?.high_count || 0 }}</strong>
      </div>
      <div>
        <span>history</span>
        <strong>{{ diagnostics?.history_count || 0 }}</strong>
      </div>
    </div>

    <details class="trust-detail-disclosure">
      <summary>
        <span>诊断警告</span>
        <strong>{{ diagnostics?.warnings.length || 0 }} 条</strong>
      </summary>
      <div class="trust-warning-list">
        <p v-for="warning in diagnostics?.warnings || []" :key="warning">{{ warning }}</p>
        <p v-if="!(diagnostics?.warnings || []).length" class="trust-empty">没有诊断警告。</p>
      </div>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TrustDiagnostics } from './trustCenterTypes'

const props = defineProps<{
  diagnostics: TrustDiagnostics | null
}>()

const diagnosticsSummary = computed(() => {
  const diagnostics = props.diagnostics
  if (!diagnostics) return '还没有诊断数据。'
  if (diagnostics.critical_count) {
    return `${diagnostics.critical_count} 条 critical 项需要先处理，其余诊断已收起。`
  }
  if (diagnostics.ai_inferred_unreviewed) {
    return `${diagnostics.ai_inferred_unreviewed} 条 AI 推断还没被用户确认。`
  }
  if (diagnostics.warnings.length) {
    return '有少量诊断警告，展开后再逐条检查。'
  }
  return '当前没有诊断警告，信任边界状态稳定。'
})

const diagnosticsGuidance = computed(() => {
  const diagnostics = props.diagnostics
  if (!diagnostics) return '刷新工作台后会重新计算队列、open loop 和历史记录。'
  if (diagnostics.critical_count) return '先回到上方高风险会话，把 critical 项处理掉。'
  if (diagnostics.ai_inferred_unreviewed) return '这些 AI 推断不是错误，但需要用户确认后才适合长期复用。'
  if (diagnostics.open_loop_total) return '如果没有急迫审查项，可以继续清理下方 open loop。'
  return '当前更适合继续收集材料或从 Recall 里验证旧判断。'
})
</script>
