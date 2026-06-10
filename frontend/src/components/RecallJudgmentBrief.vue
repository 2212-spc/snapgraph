<template>
  <section class="recall-judgment-brief" :data-confidence="judgment.confidence_label">
    <div class="recall-judgment-copy">
      <span class="section-kicker">旧判断</span>
      <h3>{{ judgment.title }}</h3>
      <p>{{ judgment.summary }}</p>
    </div>
    <div class="recall-judgment-metrics">
      <span class="confidence-pill" :class="`is-${judgment.confidence_label}`">
        {{ confidenceLabel }}
      </span>
      <span v-if="judgment.space_name">{{ judgment.space_name }}</span>
      <span>{{ judgment.source }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RecallProjection } from '../types'

const props = defineProps<{
  judgment: RecallProjection['judgment']
}>()

const confidenceLabel = computed(() => {
  if (props.judgment.confidence_label === 'strong') return '证据强'
  if (props.judgment.confidence_label === 'mixed') return '需要复核'
  return '证据弱'
})
</script>

