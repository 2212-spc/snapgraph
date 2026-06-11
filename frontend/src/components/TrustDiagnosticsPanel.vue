<template>
  <section class="trust-diagnostics-panel">
    <div class="trust-panel-head">
      <div>
        <span class="section-kicker">系统检查</span>
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
        <span>必须先看</span>
        <strong>{{ diagnostics?.critical_count || 0 }}</strong>
      </div>
      <div>
        <span>高优先级</span>
        <strong>{{ diagnostics?.high_count || 0 }}</strong>
      </div>
      <div>
        <span>审查记录</span>
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
    return `${diagnostics.critical_count} 条必须先看的项目需要处理，其余诊断已收起。`
  }
  if (diagnostics.ai_inferred_unreviewed) {
    return `${diagnostics.ai_inferred_unreviewed} 条 AI 猜测还没被用户确认。`
  }
  if (diagnostics.warnings.length) {
    return '有少量诊断警告，展开后再逐条检查。'
  }
  return '当前没有诊断警告，信任边界状态稳定。'
})

const diagnosticsGuidance = computed(() => {
  const diagnostics = props.diagnostics
  if (!diagnostics) return '刷新后会重新计算队列、未闭环问题和历史记录。'
  if (diagnostics.critical_count) return '先回到上方重点检查，把必须先看的项目处理掉。'
  if (diagnostics.ai_inferred_unreviewed) return '这些 AI 猜测不是错误，但需要用户确认后才适合长期复用。'
  if (diagnostics.open_loop_total) return '如果没有急迫审查项，可以继续清理下方未闭环问题。'
  return '当前更适合继续收集材料或从 Recall 里验证旧判断。'
})
</script>
