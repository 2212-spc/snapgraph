<template>
  <section class="space-detail" v-if="space">
    <header>
      <div>
        <p class="eyebrow">图谱空间</p>
        <h2>{{ space.name }}</h2>
        <p>{{ space.purpose || space.description || '这个空间还没有写明用途。' }}</p>
      </div>
      <div class="space-stats">
        <span>{{ space.source_count }} 材料</span>
        <span>{{ space.node_count }} 节点</span>
        <span>{{ space.edge_count }} 边</span>
      </div>
    </header>

    <details class="space-editor">
      <summary>编辑空间</summary>
      <div>
        <input v-model="editSpaceName" placeholder="空间名称" />
        <input v-model="editSpacePurpose" placeholder="这个空间追什么问题？" />
        <textarea v-model="editSpaceDescription" placeholder="补充描述，可选。" />
        <label>
          <small>颜色</small>
          <input v-model="editSpaceColor" type="color" />
        </label>
        <button class="paper-button" :disabled="busy || !editSpaceName.trim()" @click="saveSpace">
          保存空间
        </button>
      </div>
    </details>

    <div class="space-columns">
      <article class="space-panel">
        <span>材料</span>
        <button
          v-for="source in sources"
          :key="source.id"
          class="source-row"
          :class="{ selected: selectedSource?.id === source.id }"
          @click="selectedSource = source"
        >
          <strong>{{ source.title }}</strong>
          <small>{{ source.why_saved_status === 'user-stated' ? '用户原话' : 'AI 推断' }}</small>
        </button>
        <p v-if="!sources.length">这个图谱还没有材料。</p>
      </article>

      <article class="space-panel">
        <span>连接</span>
        <div v-if="graph.nodes.length" class="graph-mini">
          <button
            v-for="node in graph.nodes.slice(0, 18)"
            :key="node.id"
            class="graph-node"
            :class="node.type"
            :style="nodeStyle(node.id)"
            :title="node.label"
          >
            {{ node.label }}
          </button>
        </div>
        <div v-if="graph.edges.length" class="edge-list">
          <p v-for="edge in graph.edges.slice(0, 16)" :key="edge.id">
            {{ labelFor(edge.source) }} -> {{ edge.relation }} -> {{ labelFor(edge.target) }}
          </p>
        </div>
        <p v-else>还没有连接边。</p>
      </article>

      <article class="space-panel">
        <span>节点信息</span>
        <template v-if="selectedSource">
          <strong>{{ selectedSource.title }}</strong>
          <p>{{ selectedSource.summary || selectedSource.why_saved }}</p>
          <label>
            <small>保存理由</small>
            <textarea v-model="editWhy" placeholder="这份材料当时为什么值得留下？" />
          </label>
          <label>
            <small>相关项目 / 问题</small>
            <input v-model="editProject" placeholder="例如：Thesis proposal" />
          </label>
          <label>
            <small>未闭环事项</small>
            <textarea v-model="editLoops" placeholder="每行一条" />
          </label>
          <button class="paper-button" :disabled="busy || !selectedSource" @click="saveContext">
            更新上下文
          </button>
          <label>
            <small>移动到图谱</small>
            <select v-model="moveTarget">
              <option v-for="item in routableSpaces" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
          </label>
          <button class="paper-button" :disabled="busy || !moveTarget || moveTarget === selectedSource.graph_space_id" @click="routeSelected">
            移动材料
          </button>
        </template>
        <p v-else>选择一份材料查看详情。</p>
      </article>
    </div>

    <section v-if="suggestions.length" class="suggestion-strip">
      <article v-for="suggestion in suggestions" :key="suggestion.id">
        <span>AI 建议 · {{ Math.round(suggestion.confidence * 100) }}%</span>
        <p>{{ suggestion.reason }}</p>
        <button class="paper-button" :disabled="busy" @click="$emit('acceptSuggestion', suggestion.id)">接受</button>
        <button class="ghost-button" :disabled="busy" @click="$emit('rejectSuggestion', suggestion.id)">忽略</button>
      </article>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ContextUpdatePayload, GraphPayload, GraphSpace, Source, Suggestion } from '../types'

const props = defineProps<{
  busy: boolean
  space: GraphSpace | null
  spaces: GraphSpace[]
  sources: Source[]
  graph: GraphPayload
  suggestions: Suggestion[]
}>()

const emit = defineEmits<{
  updateSpace: [spaceId: string, payload: { name: string; purpose: string; description: string; color: string }]
  moveSource: [sourceId: string, spaceId: string]
  updateContext: [sourceId: string, payload: ContextUpdatePayload]
  acceptSuggestion: [suggestionId: string]
  rejectSuggestion: [suggestionId: string]
}>()

const selectedSource = ref<Source | null>(null)
const moveTarget = ref('')
const editWhy = ref('')
const editProject = ref('')
const editLoops = ref('')
const editSpaceName = ref('')
const editSpacePurpose = ref('')
const editSpaceDescription = ref('')
const editSpaceColor = ref('#315f9f')
const routableSpaces = computed(() => props.spaces.filter((space) => space.status === 'active' && space.id !== 'inbox'))

watch(() => props.space, (space) => {
  editSpaceName.value = space?.name || ''
  editSpacePurpose.value = space?.purpose || ''
  editSpaceDescription.value = space?.description || ''
  editSpaceColor.value = space?.color || '#315f9f'
}, { immediate: true })

watch(selectedSource, (source) => {
  moveTarget.value = source?.graph_space_id || props.space?.id || 'default'
  editWhy.value = source?.why_saved || ''
  editProject.value = source?.related_project || ''
  editLoops.value = source?.open_loops?.join('\n') || ''
})

watch(() => props.sources, (sources) => {
  if (!selectedSource.value) return
  selectedSource.value = sources.find((source) => source.id === selectedSource.value?.id) || null
})

function routeSelected() {
  if (selectedSource.value && moveTarget.value) {
    emit('moveSource', selectedSource.value.id, moveTarget.value)
  }
}

function saveContext() {
  if (!selectedSource.value) return
  emit('updateContext', selectedSource.value.id, {
    why_saved: editWhy.value.trim(),
    related_project: editProject.value.trim(),
    open_loops: editLoops.value
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean),
    confirm: true,
  })
}

function saveSpace() {
  if (!props.space) return
  emit('updateSpace', props.space.id, {
    name: editSpaceName.value.trim(),
    purpose: editSpacePurpose.value.trim(),
    description: editSpaceDescription.value.trim(),
    color: editSpaceColor.value,
  })
}

function labelFor(nodeId: string) {
  return props.graph.nodes.find((node) => node.id === nodeId)?.label || nodeId
}

function nodeStyle(nodeId: string) {
  const index = props.graph.nodes.findIndex((node) => node.id === nodeId)
  const total = Math.min(props.graph.nodes.length, 18)
  const angle = (Math.PI * 2 * index) / Math.max(total, 1)
  const radius = index === 0 ? 0 : 38
  const x = 50 + Math.cos(angle) * radius
  const y = 50 + Math.sin(angle) * radius
  return { left: `${x}%`, top: `${y}%` }
}
</script>
