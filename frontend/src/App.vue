<template>
  <div class="snapgraph-shell">
    <header class="topbar">
      <button class="brand" @click="activeView = 'recall'">
        <span class="brand-mark">Sg</span>
        <span>
          <strong>SnapGraph</strong>
          <small>找回遗失的想法</small>
        </span>
      </button>

      <nav class="layer-nav" aria-label="SnapGraph layers">
        <button
          v-for="item in navItems"
          :key="item.id"
          :class="{ active: activeView === item.id }"
          @click="setView(item.id)"
        >
          <component :is="item.icon" :size="17" />
          {{ item.label }}
        </button>
      </nav>

      <div class="top-actions">
        <span class="provider-pill">{{ providerLabel }}</span>
        <button class="icon-button" aria-label="设置" @click="settingsOpen = true">
          <Settings :size="18" />
        </button>
      </div>
    </header>

    <main class="main-surface">
      <RecallHome
        v-if="activeView === 'recall'"
        :busy="busy"
        :busy-stage="busyStage"
        :result="askResult"
        :focus-graph="focusGraph"
        :stages="recallStages"
        :current-question="currentRecallQuestion"
        @recall="runRecall"
      />

      <SpacesView
        v-else-if="activeView === 'spaces'"
        :busy="busy"
        :spaces="spaces"
        :selected-space-id="selectedSpaceId"
        :sources="spaceSources"
        :graph="spaceGraph"
        :suggestions="spaceSuggestions"
        @select-space="selectSpace"
        @create-space="createSpace"
        @update-space="updateSpace"
        @move-source="moveSource"
        @update-context="updateContext"
        @accept-suggestion="acceptSuggestion"
        @reject-suggestion="rejectSuggestion"
        @graph-changed="refreshSelectedGraph"
        @ask-from-graph="askFromGraph"
      />

      <CollectView
        v-else
        :busy="busy"
        :spaces="spaces"
        :results="collectResults"
        @collect="collectMaterials"
        @open-space="openCollectedSpace"
      />
    </main>

    <nav class="mobile-nav" aria-label="SnapGraph mobile layers">
      <button
        v-for="item in navItems"
        :key="item.id"
        :class="{ active: activeView === item.id }"
        @click="setView(item.id)"
      >
        <component :is="item.icon" :size="18" />
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <section v-if="settingsOpen" class="settings-sheet" @click.self="settingsOpen = false">
      <div class="settings-panel">
        <button class="icon-button close" aria-label="关闭设置" @click="settingsOpen = false">
          <X :size="18" />
        </button>
        <p class="eyebrow">设置</p>
        <h2>运行状态</h2>
        <dl>
          <div>
            <dt>Provider</dt>
            <dd>{{ config?.provider || 'mock' }}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>{{ config?.runtime?.model_used || config?.model || 'MockLLM' }}</dd>
          </div>
          <div>
            <dt>API Key</dt>
            <dd>{{ config?.has_api_key ? '已从环境变量读取' : '未配置或使用 mock' }}</dd>
          </div>
          <div>
            <dt>Workspace</dt>
            <dd>{{ workspace?.workspace_path || '未加载' }}</dd>
          </div>
        </dl>
        <button class="paper-button" :disabled="busy" @click="loadDemo">加载演示数据</button>
      </div>
    </section>

    <p v-if="toast" class="toast" :class="{ error: toastKind === 'error' }">{{ toast }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, onMounted, ref } from 'vue'
import { Archive, FolderOpen, Search, Settings, X } from 'lucide-vue-next'
import CollectView from './components/CollectView.vue'
import RecallHome from './components/RecallHome.vue'
import SpacesView from './components/SpacesView.vue'
import type {
  AskResponse,
  CollectPayload,
  ContextUpdatePayload,
  FocusGraph,
  GraphPayload,
  GraphSpace,
  IngestResponse,
  ProviderConfig,
  RecallStage,
  Source,
  Suggestion,
  WorkspaceState,
} from './types'

type ActiveView = 'recall' | 'spaces' | 'collect'
type ToastKind = 'info' | 'error'

const navItems = [
  { id: 'recall' as const, label: '找回', icon: markRaw(Search) },
  { id: 'spaces' as const, label: '图谱', icon: markRaw(FolderOpen) },
  { id: 'collect' as const, label: '收集', icon: markRaw(Archive) },
]

const activeView = ref<ActiveView>('recall')
const selectedSpaceId = ref('all')
const busy = ref(false)
const busyStage = ref('')
const workspace = ref<WorkspaceState | null>(null)
const config = ref<ProviderConfig | null>(null)
const spaces = ref<GraphSpace[]>([])
const allSources = ref<Source[]>([])
const spaceSources = ref<Source[]>([])
const spaceGraph = ref<GraphPayload>({ nodes: [], edges: [] })
const spaceSuggestions = ref<Suggestion[]>([])
const focusGraph = ref<FocusGraph | null>(null)
const askResult = ref<AskResponse | null>(null)
const currentRecallQuestion = ref('')
const recallStages = ref<RecallStage[]>([])
const collectResults = ref<IngestResponse[]>([])
const settingsOpen = ref(false)
const toast = ref('')
const toastKind = ref<ToastKind>('info')

const providerLabel = computed(() => {
  const provider = config.value?.provider || 'mock'
  const model = config.value?.runtime?.model_used || config.value?.model || ''
  return model ? `${provider} · ${model}` : provider
})

onMounted(() => {
  refreshShell()
})

function setView(view: ActiveView) {
  activeView.value = view
  if (view === 'spaces' && selectedSpaceId.value !== 'all') {
    loadSpaceDetail(selectedSpaceId.value)
  }
}

async function refreshShell() {
  try {
    await Promise.all([loadWorkspace(), loadConfig(), loadSpaces(), loadAllSources()])
    if (selectedSpaceId.value !== 'all') await loadSpaceDetail(selectedSpaceId.value)
  } catch (error) {
    showToast(messageFromError(error), 'error')
  }
}

async function loadWorkspace() {
  workspace.value = await api<WorkspaceState>('/api/workspace')
}

async function loadConfig() {
  config.value = await api<ProviderConfig>('/api/config')
}

async function loadSpaces() {
  const payload = await api<{ spaces: GraphSpace[] }>('/api/spaces')
  spaces.value = payload.spaces
}

async function loadAllSources() {
  allSources.value = await api<Source[]>('/api/sources?space_id=all')
}

async function selectSpace(spaceId: string) {
  selectedSpaceId.value = spaceId
  if (spaceId === 'all') return
  await loadSpaceDetail(spaceId)
}

async function loadSpaceDetail(spaceId: string) {
  try {
    const [sources, graph, suggestions] = await Promise.all([
      api<Source[]>(`/api/spaces/${encodeURIComponent(spaceId)}/sources`),
      api<GraphPayload>(`/api/spaces/${encodeURIComponent(spaceId)}/graph`),
      api<{ suggestions: Suggestion[] }>(`/api/suggestions?status=pending&space_id=${encodeURIComponent(spaceId)}`),
    ])
    spaceSources.value = sources
    spaceGraph.value = graph
    spaceSuggestions.value = suggestions.suggestions
  } catch (error) {
    showToast(messageFromError(error), 'error')
  }
}

async function refreshSelectedGraph() {
  if (selectedSpaceId.value !== 'all') {
    await loadSpaceDetail(selectedSpaceId.value)
  }
  await loadWorkspace()
  await loadSpaces()
}

async function askFromGraph(question: string) {
  activeView.value = 'recall'
  await runRecall(question)
}

async function runRecall(question: string) {
  busy.value = true
  currentRecallQuestion.value = question
  askResult.value = null
  focusGraph.value = null
  recallStages.value = [
    { id: 'evidence', label: '找本地证据', status: 'active', detail: '先从本地图谱里找回线索' },
    { id: 'read', label: '读用户原话', status: 'pending' },
    { id: 'connect', label: '检查图谱连接', status: 'pending' },
    { id: 'write', label: '生成 AI 回复', status: 'pending' },
  ]
  busyStage.value = '先找本地证据。'
  try {
    focusGraph.value = await api<FocusGraph>('/api/focus', {
      method: 'POST',
      body: JSON.stringify({ question, space_id: 'all' }),
    })
    updateRecallStage({ id: 'evidence', label: '找本地证据', status: 'done', detail: `找到 ${focusGraph.value.evidence_cards.length} 条线索` })
  } catch (error) {
    updateRecallStage({ id: 'evidence', label: '找本地证据', status: 'error', detail: '本地证据检索失败' })
    showToast(`本地证据检索失败：${messageFromError(error)}`, 'error')
  }

  busyStage.value = 'Qwen 正在组织回答。'
  try {
    await streamRecall(question)
  } catch (error) {
    showToast(`解释生成暂时不可用，已保留本地证据。${friendlyProviderHint(error)}`, 'error')
  } finally {
    busy.value = false
    busyStage.value = ''
  }
}

async function streamRecall(question: string) {
  const response = await fetch('/api/ask/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, space_id: 'all', save: false }),
  })
  if (!response.ok || !response.body) {
    throw new Error(await response.text() || `HTTP ${response.status}`)
  }
  const decoder = new TextDecoder()
  const reader = response.body.getReader()
  let buffer = ''
  let streamedText = ''
  while (true) {
    const { done, value } = await reader.read()
    if (value) {
      buffer += decoder.decode(value, { stream: !done })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) handleStreamEvent(part, (chunk) => {
        streamedText += chunk
        askResult.value = partialAskResponse(question, streamedText)
      })
    }
    if (done) break
  }
}

function handleStreamEvent(raw: string, onChunk: (chunk: string) => void) {
  const eventLine = raw.split('\n').find((line) => line.startsWith('event:'))
  const dataLines = raw.split('\n').filter((line) => line.startsWith('data:'))
  if (!eventLine || !dataLines.length) return
  const event = eventLine.replace(/^event:\s*/, '').trim()
  const data = JSON.parse(dataLines.map((line) => line.replace(/^data:\s?/, '')).join('\n'))
  if (event === 'stage') {
    updateRecallStage(data as RecallStage)
  } else if (event === 'focus') {
    if (data.focus_graph) focusGraph.value = data.focus_graph as FocusGraph
  } else if (event === 'chunk') {
    onChunk(String(data.text || ''))
  } else if (event === 'final') {
    askResult.value = data as AskResponse
    if (askResult.value.focus_graph) focusGraph.value = askResult.value.focus_graph
    updateRecallStage({ id: 'write', label: '生成 AI 回复', status: 'done', detail: '回答已完成' })
  } else if (event === 'error') {
    throw new Error(String(data.message || 'Stream failed'))
  }
}

function partialAskResponse(question: string, text: string): AskResponse {
  return {
    question,
    text: `# 回答\n## AI 探索回应\n${text}`,
    contexts: focusGraph.value?.evidence_cards || [],
    graph_paths: [],
    focus_graph: focusGraph.value || emptyFocusGraph(),
  }
}

function emptyFocusGraph(): FocusGraph {
  return {
    nodes: [],
    edges: [],
    evidence_cards: [],
    open_loops: [],
    confidence_summary: {
      source_count: 0,
      user_stated: 0,
      ai_inferred: 0,
      confidence_label: 'none',
    },
  }
}

function updateRecallStage(stage: RecallStage) {
  const current = recallStages.value
  const index = current.findIndex((item) => item.id === stage.id)
  if (index >= 0) {
    recallStages.value = [
      ...current.slice(0, index),
      { ...current[index], ...stage },
      ...current.slice(index + 1),
    ]
  } else {
    recallStages.value = [...current, stage]
  }
}

async function collectMaterials(payload: CollectPayload) {
  const files = [...payload.files]
  if (payload.text.trim()) {
    files.unshift(textAsMarkdownFile(payload.text))
  }
  if (!files.length) return

  busy.value = true
  collectResults.value = []
  try {
    for (const [index, file] of files.entries()) {
      busyStage.value = `正在放入图谱 ${index + 1}/${files.length}。`
      const form = new FormData()
      form.append('file', file)
      form.append('why', payload.why)
      form.append('route_mode', payload.routeMode)
      if (payload.routeMode === 'manual') form.append('space_id', payload.spaceId)
      const result = await api<IngestResponse>('/api/ingest', { method: 'POST', body: form })
      collectResults.value.unshift(result)
    }
    showToast('材料已进入图谱。')
    await refreshShell()
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
    busyStage.value = ''
  }
}

async function openCollectedSpace(spaceId: string) {
  if (!spaceId) return
  activeView.value = 'spaces'
  await selectSpace(spaceId)
}

async function createSpace(payload: { name: string; purpose: string; description: string; color: string }) {
  busy.value = true
  try {
    const space = await api<GraphSpace>('/api/spaces', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    await loadSpaces()
    selectedSpaceId.value = space.id
    await loadSpaceDetail(space.id)
    showToast('图谱空间已创建。')
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function updateSpace(spaceId: string, payload: { name: string; purpose: string; description: string; color: string }) {
  busy.value = true
  try {
    await api<GraphSpace>(`/api/spaces/${encodeURIComponent(spaceId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
    await refreshShell()
    showToast('图谱空间已更新。')
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function moveSource(sourceId: string, spaceId: string) {
  busy.value = true
  try {
    await api(`/api/sources/${encodeURIComponent(sourceId)}/route`, {
      method: 'POST',
      body: JSON.stringify({ space_id: spaceId, reason: 'User moved from graph workspace.' }),
    })
    await refreshShell()
    showToast('材料已移动。')
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function updateContext(sourceId: string, payload: ContextUpdatePayload) {
  busy.value = true
  try {
    await api(`/api/sources/${encodeURIComponent(sourceId)}/context`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
    await refreshShell()
    showToast('认知上下文已更新。')
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function acceptSuggestion(suggestionId: string) {
  await decideSuggestion(suggestionId, 'accept')
}

async function rejectSuggestion(suggestionId: string) {
  await decideSuggestion(suggestionId, 'reject')
}

async function decideSuggestion(suggestionId: string, action: 'accept' | 'reject') {
  busy.value = true
  try {
    await api(`/api/suggestions/${encodeURIComponent(suggestionId)}/${action}`, { method: 'POST' })
    await refreshShell()
    showToast(action === 'accept' ? '已接受建议。' : '已忽略建议。')
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function loadDemo() {
  busy.value = true
  try {
    await api('/api/demo/load', {
      method: 'POST',
      body: JSON.stringify({ use_provider: false }),
    })
    await refreshShell()
    settingsOpen.value = false
    showToast('演示数据已加载。')
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(path, { ...options, headers })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = await response.json()
      detail = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail || payload)
    } catch {
      detail = await response.text()
    }
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return response.json()
}

function textAsMarkdownFile(text: string) {
  const cleaned = text.trim()
  const firstLine = cleaned.split('\n').find(Boolean) || '捕获材料'
  const title = firstLine.replace(/^#+\s*/, '').slice(0, 48) || '捕获材料'
  const markdown = cleaned.startsWith('#') ? `${cleaned}\n` : `# ${title}\n\n${cleaned}\n`
  return new File([markdown], `capture-${Date.now()}.md`, { type: 'text/markdown' })
}

function showToast(message: string, kind: ToastKind = 'info') {
  toast.value = message
  toastKind.value = kind
  window.setTimeout(() => {
    if (toast.value === message) toast.value = ''
  }, 4200)
}

function messageFromError(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

function friendlyProviderHint(error: unknown) {
  const message = messageFromError(error)
  if (message.includes('SNAPGRAPH_LLM_API_KEY') || message.includes('provider requires API key')) {
    return '模型 API key 没有被当前服务进程读到。'
  }
  return ''
}
</script>
