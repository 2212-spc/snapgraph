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

    <p class="trust-loop-priority-note">{{ priorityNote }}</p>

    <div class="trust-open-loop-list">
      <article v-for="loop in visibleLoops" :key="loop.loop_id" class="trust-open-loop-card">
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
      <p v-if="overflowCount" class="trust-loop-overflow-note">
        还有 {{ overflowCount }} 个 open loop 已收起，先处理上面这些更高价值的问题。
      </p>
      <p v-if="!payload.items.length" class="trust-empty">当前没有 open-loop。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { TrustOpenLoopPayload, TrustOpenLoopState, TrustOpenLoopUpdatePayload } from './trustCenterTypes'

const props = defineProps<{
  payload: TrustOpenLoopPayload
  busy: boolean
}>()

const emit = defineEmits<{
  updateLoop: [loopId: string, payload: TrustOpenLoopUpdatePayload]
}>()

const notes = reactive<Record<string, string>>({})
const visibleLoops = computed(() => props.payload.items.slice(0, 4))
const overflowCount = computed(() => Math.max(props.payload.items.length - visibleLoops.value.length, 0))
const priorityNote = computed(() => {
  const nextCount = props.payload.summary.by_state.next || 0
  const activeCount = props.payload.summary.by_state.active || 0
  if (nextCount) return `${nextCount} 个问题已经标成 next，适合进入下一轮行动。`
  if (activeCount) return `${activeCount} 个问题仍然 active，先判断它们是否还值得继续。`
  if (props.payload.summary.total) return '剩余问题大多已经处理，可以展开确认是否需要恢复。'
  return '当前没有悬而未决的问题。'
})

function setState(loopId: string, state: TrustOpenLoopState) {
  emit('updateLoop', loopId, {
    state,
    note: notes[loopId] || '',
  })
}
</script>
