<template>
  <section class="trust-diagnostics-panel">
    <div class="trust-panel-head">
      <div>
        <span class="section-kicker">Diagnostics</span>
        <h3>信任诊断</h3>
      </div>
      <strong>{{ diagnostics?.queue_total || 0 }}</strong>
    </div>

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

    <div class="trust-warning-list">
      <p v-for="warning in diagnostics?.warnings || []" :key="warning">{{ warning }}</p>
      <p v-if="!(diagnostics?.warnings || []).length" class="trust-empty">没有诊断警告。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { TrustDiagnostics } from './trustCenterTypes'

defineProps<{
  diagnostics: TrustDiagnostics | null
}>()
</script>
