<template>
  <section class="trust-open-loop-panel">
    <div class="trust-panel-head">
      <div>
        <span class="section-kicker">Open loops</span>
        <h3>待闭环问题</h3>
      </div>
      <strong>{{ payload.summary.total }} 条</strong>
    </div>

    <div class="trust-loop-state-grid">
      <span>active {{ payload.summary.by_state.active || 0 }}</span>
      <span>next {{ payload.summary.by_state.next || 0 }}</span>
      <span>resolved {{ payload.summary.by_state.resolved || 0 }}</span>
      <span>dismissed {{ payload.summary.by_state.dismissed || 0 }}</span>
    </div>

    <div class="trust-open-loop-list">
      <article v-for="loop in payload.items" :key="loop.loop_id" class="trust-open-loop-card">
        <div>
          <span>{{ loop.state }}</span>
          <strong>{{ loop.text }}</strong>
          <p>{{ loop.source_titles.join(' · ') || loop.topic_title || '未连接到具体材料' }}</p>
        </div>
        <div class="trust-loop-actions">
          <input v-model="notes[loop.loop_id]" placeholder="状态备注" />
          <button class="ghost-button" type="button" :disabled="busy" @click="setState(loop.loop_id, 'next')">next</button>
          <button class="ghost-button" type="button" :disabled="busy" @click="setState(loop.loop_id, 'resolved')">resolved</button>
          <button class="ghost-button" type="button" :disabled="busy" @click="setState(loop.loop_id, 'dismissed')">dismissed</button>
        </div>
      </article>
      <p v-if="!payload.items.length" class="trust-empty">当前没有 open-loop。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import type { TrustOpenLoopPayload, TrustOpenLoopState, TrustOpenLoopUpdatePayload } from './trustCenterTypes'

defineProps<{
  payload: TrustOpenLoopPayload
  busy: boolean
}>()

const emit = defineEmits<{
  updateLoop: [loopId: string, payload: TrustOpenLoopUpdatePayload]
}>()

const notes = reactive<Record<string, string>>({})

function setState(loopId: string, state: TrustOpenLoopState) {
  emit('updateLoop', loopId, {
    state,
    note: notes[loopId] || '',
  })
}
</script>
