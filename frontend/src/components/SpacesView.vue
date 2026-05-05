<template>
  <section class="layer-view spaces-view">
    <div v-if="!selectedSpace" class="spaces-overview">
      <div class="layer-head">
        <p class="eyebrow">图谱</p>
        <h1>你的信息在哪些问题里生长？</h1>
        <p>空间不是写之前的分类负担，而是材料进入后逐渐显出的结构。</p>
      </div>

      <section class="space-grid memory-space-grid">
        <article
          v-for="spaceCard in graphSpaceCards"
          :key="spaceCard.id"
          class="graph-space-card"
          :style="{ '--space-color': spaceCard.color }"
        >
          <div class="graph-space-card-head">
            <div>
              <span>{{ spaceCard.kicker }}</span>
              <strong>{{ spaceCard.name }}</strong>
            </div>
            <div class="graph-space-stats">
              <span class="graph-stat-chip">{{ spaceCard.sourceCount }} 材料</span>
              <span class="graph-stat-chip">{{ spaceCard.nodeCount }} 节点</span>
              <span v-if="spaceCard.openItemCount" class="graph-stat-chip">
                {{ spaceCard.openItemCount }} {{ spaceCard.openItemLabel }}
              </span>
            </div>
          </div>

          <p>{{ spaceCard.description }}</p>

          <div class="graph-space-meta">
            <strong>最近材料</strong>
            <p v-if="spaceCard.recentSourceTitles.length">
              {{ spaceCard.recentSourceTitles.join(' · ') }}
            </p>
            <p v-else class="subtle-empty-state">还没有最近材料，等新内容进入后再回来看看。</p>
          </div>

          <footer class="graph-space-footer">
            <small v-if="spaceCard.lastActiveLabel">{{ spaceCard.lastActiveLabel }}</small>
            <button class="primary-button" :disabled="busy" @click="$emit('selectSpace', spaceCard.id)">
              进入空间
            </button>
          </footer>
        </article>
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
        @graph-changed="$emit('graphChanged')"
        @ask-from-graph="(question) => $emit('askFromGraph', question)"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import GraphSpaceView from './GraphSpaceView.vue'
import type { ContextUpdatePayload, GraphPayload, GraphSpace, Source, Suggestion } from '../types'

type GraphSpaceCard = {
  id: string
  name: string
  kicker: string
  description: string
  color: string
  sourceCount: number
  nodeCount: number
  openItemCount: number
  openItemLabel: string
  recentSourceTitles: string[]
  lastActiveLabel: string
}

const props = defineProps<{
  busy: boolean
  spaces: GraphSpace[]
  selectedSpaceId: string
  sources: Source[]
  allSources: Source[]
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
  graphChanged: []
  askFromGraph: [question: string]
}>()

const name = ref('')
const purpose = ref('')
const description = ref('')
const color = ref('#315f9f')

const selectedSpace = computed(() => props.spaces.find((space) => space.id === props.selectedSpaceId) || null)
const visibleSpaces = computed(() => props.spaces.filter((space) => space.status === 'active'))
const sourcesBySpaceId = computed(() => {
  const buckets = new Map<string, Source[]>()
  for (const source of props.allSources) {
    const existing = buckets.get(source.graph_space_id) || []
    existing.push(source)
    buckets.set(source.graph_space_id, existing)
  }
  return buckets
})

const graphSpaceCards = computed<GraphSpaceCard[]>(() => {
  return visibleSpaces.value.map((space) => {
    const recentSources = [...(sourcesBySpaceId.value.get(space.id) || [])]
      .sort((left, right) => Date.parse(right.imported_at || '') - Date.parse(left.imported_at || ''))
    const openLoopCount = recentSources.reduce((total, source) => total + (source.open_loops?.length || 0), 0)
    const recentSourceTitles = recentSources.slice(0, 3).map((source) => source.title)
    const lastActive = recentSources[0]?.imported_at || space.updated_at || ''
    const pendingCount = space.pending_suggestions || openLoopCount

    return {
      id: space.id,
      name: space.name,
      kicker: space.id === 'inbox' ? '记忆入口' : '记忆空间',
      description: spaceDescription(space),
      color: space.color,
      sourceCount: space.source_count,
      nodeCount: space.node_count,
      openItemCount: pendingCount,
      openItemLabel: space.pending_suggestions ? '建议' : '开放问题',
      recentSourceTitles,
      lastActiveLabel: lastActive ? `最近活跃：${formatDate(lastActive)}` : '',
    }
  })
})

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

function spaceDescription(space: GraphSpace) {
  if (space.id === 'inbox') {
    return '新材料会先放在这里，等待确认和整理。'
  }
  if (space.id === 'default') {
    return '默认记忆空间，保存当前 SnapGraph 工作流的主要材料、判断和开放问题。'
  }
  return space.purpose || space.description || '这个空间正在等待更多材料，逐步长出自己的问题结构。'
}

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
</script>
