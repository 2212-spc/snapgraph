<template>
  <section v-if="report || session" class="trust-quiet-report">
    <div>
      <span class="section-kicker">Trust report</span>
      <strong>{{ headline }}</strong>
      <p>{{ quietSummary }}</p>
    </div>

    <details>
      <summary>
        <span>Report detail</span>
        <strong>{{ sectionCount }} sections</strong>
      </summary>
      <div class="trust-quiet-report-grid">
        <article v-for="section in visibleSections" :key="section.id">
          <span>{{ section.title }}</span>
          <strong>{{ section.count }}</strong>
          <p>{{ section.summary }}</p>
        </article>
      </div>
      <div v-if="visibleActions.length" class="trust-quiet-action-list">
        <p v-for="action in visibleActions" :key="action.source_id">
          {{ action.title }} - {{ action.risk_level }} - {{ action.summary }}
        </p>
      </div>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TrustReportPayload, TrustSessionPayload } from './trustCenterTypes'

const props = defineProps<{
  report?: TrustReportPayload
  session?: TrustSessionPayload
}>()

const headline = computed(() => {
  if (props.report?.headline) return props.report.headline
  if (props.session?.next_step?.title) return `Next: ${props.session.next_step.title}`
  return 'Trust context is ready.'
})

const quietSummary = computed(() => {
  if (props.report?.quiet_summary) return props.report.quiet_summary
  if (props.session?.quiet_summary) return props.session.quiet_summary
  return 'Details stay collapsed so the review queue remains easy to scan.'
})

const sectionCount = computed(() => props.report?.sections.length || 0)
const visibleSections = computed(() => props.report?.sections.slice(0, props.report.display_policy.max_visible_sections || 2) || [])
const visibleActions = computed(() => props.report?.action_queue.slice(0, props.report.display_policy.max_visible_actions || 3) || [])
</script>
