<template>
  <section class="trust-open-loop-panel">
    <div class="trust-panel-head">
      <div>
        <span class="section-kicker">未闭环</span>
        <h3>待闭环问题</h3>
      </div>
      <strong>{{ payload.summary.total }} 条</strong>
    </div>

    <div class="trust-loop-state-grid">
      <span>还要判断 {{ payload.summary.by_state.active || 0 }}</span>
      <span>下一步 {{ payload.summary.by_state.next || 0 }}</span>
      <span>已解决 {{ payload.summary.by_state.resolved || 0 }}</span>
      <span>不处理 {{ payload.summary.by_state.dismissed || 0 }}</span>
    </div>

    <p class="trust-loop-priority-note">{{ priorityNote }}</p>

    <div class="trust-open-loop-list">
      <article v-for="loop in visibleLoops" :key="loop.loop_id" class="trust-open-loop-card">
        <div>
          <span>{{ stateLabel(loop.state) }}</span>
          <strong>{{ loop.text }}</strong>
          <p>{{ loop.source_titles.join(' · ') || loop.topic_title || '未连接到具体材料' }}</p>
        </div>
        <div class="trust-loop-actions">
          <input v-model="notes[loop.loop_id]" placeholder="状态备注" />
          <button class="ghost-button" type="button" :disabled="busy" @click="setState(loop.loop_id, 'next')">下一步</button>
          <button class="ghost-button" type="button" :disabled="busy" @click="setState(loop.loop_id, 'resolved')">已解决</button>
          <button class="ghost-button" type="button" :disabled="busy" @click="setState(loop.loop_id, 'dismissed')">不处理</button>
        </div>
      </article>
      <p v-if="overflowCount" class="trust-loop-overflow-note">
        还有 {{ overflowCount }} 个未闭环问题已收起，先处理上面这些更高价值的问题。
      </p>
      <p v-if="!payload.items.length" class="trust-empty">当前没有未闭环问题。</p>
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
  if (nextCount) return `${nextCount} 个问题已经变成下一步，适合进入下一轮行动。`
  if (activeCount) return `${activeCount} 个问题还需要判断，先看它们是否还值得继续。`
  if (props.payload.summary.total) return '剩余问题大多已经处理，可以展开确认是否需要恢复。'
  return '当前没有悬而未决的问题。'
})

function stateLabel(state: TrustOpenLoopState) {
  if (state === 'active') return '还要判断'
  if (state === 'next') return '下一步'
  if (state === 'resolved') return '已解决'
  if (state === 'dismissed') return '不处理'
  return state
}

function setState(loopId: string, state: TrustOpenLoopState) {
  emit('updateLoop', loopId, {
    state,
    note: notes[loopId] || '',
  })
}
</script>
