<template>
  <section class="layer-view spaces-view">
    <div v-if="!selectedSpace" class="spaces-overview">
      <div class="layer-head">
        <p class="eyebrow">图谱</p>
        <h1>你的信息在哪些问题里生长？</h1>
        <p>空间不是写之前的分类负担，而是材料进入后逐渐显出的结构。</p>
      </div>

      <section class="space-grid">
        <button
          v-for="space in visibleSpaces"
          :key="space.id"
          class="space-card"
          :style="{ '--space-color': space.color }"
          @click="$emit('selectSpace', space.id)"
        >
          <span>{{ space.id === 'inbox' ? '待整理' : '图谱空间' }}</span>
          <strong>{{ space.name }}</strong>
          <p>{{ space.purpose || space.description || '还没有写明这个空间追什么问题。' }}</p>
          <small>{{ space.source_count }} 材料 · {{ space.node_count }} 节点 · {{ space.pending_suggestions }} 建议</small>
        </button>
      </section>

      <form class="create-space" @submit.prevent="submitSpace">
        <span>新建图谱空间</span>
        <input v-model="name" placeholder="空间名称" />
        <input v-model="purpose" placeholder="它要帮你追什么问题？" />
        <textarea v-model="description" placeholder="补充描述，可选。" />
        <div>
          <input v-model="color" type="color" aria-label="空间颜色" />
          <button class="primary-button" :disabled="busy || !name.trim()">创建空间</button>
        </div>
      </form>
    </div>

    <div v-else>
      <button class="text-button back-button" @click="$emit('selectSpace', 'all')">返回图谱列表</button>
      <GraphSpaceView
        :busy="busy"
        :space="selectedSpace"
        :spaces="spaces"
        :sources="sources"
        :graph="graph"
        :suggestions="suggestions"
        @update-space="(spaceId, payload) => $emit('updateSpace', spaceId, payload)"
        @move-source="(sourceId, spaceId) => $emit('moveSource', sourceId, spaceId)"
        @update-context="(sourceId, payload) => $emit('updateContext', sourceId, payload)"
        @accept-suggestion="(suggestionId) => $emit('acceptSuggestion', suggestionId)"
        @reject-suggestion="(suggestionId) => $emit('rejectSuggestion', suggestionId)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import GraphSpaceView from './GraphSpaceView.vue'
import type { ContextUpdatePayload, GraphPayload, GraphSpace, Source, Suggestion } from '../types'

const props = defineProps<{
  busy: boolean
  spaces: GraphSpace[]
  selectedSpaceId: string
  sources: Source[]
  graph: GraphPayload
  suggestions: Suggestion[]
}>()

const emit = defineEmits<{
  selectSpace: [spaceId: string]
  createSpace: [payload: { name: string; purpose: string; description: string; color: string }]
  updateSpace: [spaceId: string, payload: { name: string; purpose: string; description: string; color: string }]
  moveSource: [sourceId: string, spaceId: string]
  updateContext: [sourceId: string, payload: ContextUpdatePayload]
  acceptSuggestion: [suggestionId: string]
  rejectSuggestion: [suggestionId: string]
}>()

const name = ref('')
const purpose = ref('')
const description = ref('')
const color = ref('#315f9f')

const selectedSpace = computed(() => props.spaces.find((space) => space.id === props.selectedSpaceId) || null)
const visibleSpaces = computed(() => props.spaces.filter((space) => space.status === 'active'))

function submitSpace() {
  if (!name.value.trim()) return
  emit('createSpace', {
    name: name.value.trim(),
    purpose: purpose.value.trim(),
    description: description.value.trim(),
    color: color.value,
  })
  name.value = ''
  purpose.value = ''
  description.value = ''
}
</script>
