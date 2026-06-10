<template>
  <section class="recall-trust-debt-panel" :data-level="trustDebt.level">
    <div class="recall-panel-head">
      <div>
        <span class="section-kicker">不确定性</span>
        <h3>哪些地方还不能完全相信</h3>
      </div>
      <span class="trust-debt-level" :class="`is-${trustDebt.level}`">{{ levelLabel }}</span>
    </div>

    <p>{{ trustDebt.summary }}</p>

    <div v-if="trustDebt.items.length" class="trust-debt-list">
      <article v-for="item in trustDebt.items" :key="item.id" class="trust-debt-item" :class="`is-${item.severity}`">
        <strong>{{ item.label }}</strong>
        <p>{{ item.detail }}</p>
      </article>
    </div>
    <p v-else class="subtle-empty-state">这次回答没有明显的信任债务。</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RecallProjection } from '../types'

const props = defineProps<{
  trustDebt: RecallProjection['trust_debt']
}>()

const levelLabel = computed(() => {
  if (props.trustDebt.level === 'high') return '高风险'
  if (props.trustDebt.level === 'medium') return '需复核'
  return '低风险'
})
</script>

