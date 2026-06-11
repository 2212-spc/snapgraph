<template>
  <div class="study-shell">
    <aside class="study-sidebar" :data-collapsed="sidebarCollapsed ? 'true' : 'false'">
      <div class="sidebar-top">
        <button class="brand sidebar-brand" @click="activeView = 'recall'">
          <span class="brand-mark">S</span>
          <span class="brand-copy">
            <strong>SnapGraph</strong>
          </span>
        </button>
        <button
          class="sidebar-collapse"
          type="button"
          :aria-label="sidebarCollapsed ? '展开侧栏' : '收起侧栏'"
          @click="sidebarCollapsed = !sidebarCollapsed"
        >
          <component :is="sidebarCollapsed ? PanelLeftOpen : PanelLeftClose" :size="15" />
        </button>
      </div>

      <nav class="sidebar-nav" aria-label="SnapGraph layers">
        <button class="sidebar-new-chat" type="button" :disabled="busy" @click="startNewRecall">
          <Plus :size="16" />
          <span>新对话</span>
        </button>
        <button
          v-for="item in navItems"
          :key="item.id"
          :class="{ active: activeView === item.id }"
          @click="setView(item.id)"
        >
          <component :is="item.icon" :size="17" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-spacer"></div>

      <div class="sidebar-footer">
        <button class="sidebar-settings" type="button" @click="settingsOpen = true">
          <Settings :size="18" />
          <span>设置</span>
        </button>
        <span class="provider-pill">{{ runtimeStatusLabel }}</span>
      </div>
    </aside>

    <section class="study-chat-shell" :data-activity-open="showActivityPanel ? 'true' : 'false'">
      <header class="session-bar">
        <button class="session-title-button" type="button" :disabled="activeView !== 'recall'" @click="setView('recall')">
          <span>{{ sessionTitle }}</span>
        </button>
        <div class="session-actions">
          <button class="header-icon-button" aria-label="新对话" :disabled="busy" @click="startNewRecall">
            <SquarePen :size="16" />
          </button>
          <button
            class="header-icon-button activity-toggle"
            :aria-pressed="activityOpen"
            aria-label="活动面板"
            @click="activityOpen = !activityOpen"
          >
            <PanelRight :size="16" />
          </button>
        </div>
      </header>

      <main class="main-surface">
        <RecallHome
          v-if="activeView === 'recall'"
          :busy="busy"
          :busy-stage="busyStage"
          :mode="selectedRecallMode"
          :result-mode="currentRecallMode"
          :result="askResult"
          :focus-graph="focusGraph"
          :stages="recallStages"
          :current-question="currentRecallQuestion"
          :recent-questions="recentRecallQuestions"
          @recall="runRecall"
          @mode-changed="selectedRecallMode = $event"
          @open-local-file="openLocalFile"
        />

        <SpacesView
          v-else-if="activeView === 'spaces'"
          :busy="busy"
          :spaces="spaces"
          :selected-space-id="selectedSpaceId"
          :sources="spaceSources"
          :all-sources="allSources"
          :questions="savedQuestions"
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
          @start-collect="startCollect"
        />

        <TrustCenterView
          v-else-if="activeView === 'trust'"
          :review="trustReview"
          :detail="trustReviewDetail"
          :open-loops="trustOpenLoops"
          :diagnostics="trustDiagnostics"
          :selected-source-ids="selectedTrustSourceIds"
          :filters="trustFilters"
          :busy="busy"
          @refresh="loadTrustCenter"
          @select-review="selectTrustReview"
          @toggle-review-selection="toggleTrustSelection"
          @filter-changed="updateTrustFilters"
          @batch-action="applyTrustBatch"
          @update-open-loop="updateTrustOpenLoop"
        />

        <CollectView
          v-else
          :busy="busy"
          :spaces="spaces"
          :results="collectResults"
          @collect="collectMaterials"
          @open-space="openCollectedSpace"
          @ask-batch="askRecentBatch"
        />
      </main>
    </section>

    <aside v-if="showActivityPanel" class="activity-panel" aria-label="SnapGraph activity">
      <section class="activity-card">
        <span>当前层</span>
        <strong>{{ activeViewLabel }}</strong>
        <p>{{ busy ? busyStage || '正在处理当前请求。' : '本地材料、记忆连接和保存理由会在这里汇总。' }}</p>
      </section>
      <section class="activity-card">
        <span>证据</span>
        <strong>{{ evidenceSummary }}</strong>
        <p>{{ activityEvidenceDetail }}</p>
      </section>
      <section class="activity-card">
        <span>连接</span>
        <strong>{{ graphSummary }}</strong>
        <p>{{ pendingSummary }}</p>
      </section>
      <section class="activity-card">
        <span>运行</span>
        <strong>{{ runtimeStatusLabel }}</strong>
        <p>{{ runtimeStatusDetail }}</p>
      </section>
    </aside>

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
            <dt>提供方</dt>
            <dd>{{ config?.provider || 'mock' }}</dd>
          </div>
          <div>
            <dt>模型</dt>
            <dd>{{ config?.runtime?.model_used || config?.model || 'MockLLM' }}</dd>
          </div>
          <div>
            <dt>API Key</dt>
            <dd>{{ config?.has_api_key ? '已从环境变量读取' : '未配置或使用 mock' }}</dd>
          </div>
          <div>
            <dt>工作区</dt>
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
import {
  BookOpen,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  PenLine,
  PanelRight,
  Plus,
  Settings,
  ShieldCheck,
  SquarePen,
  X,
} from 'lucide-vue-next'
import CollectView from './components/CollectView.vue'
import RecallHome from './components/RecallHome.vue'
import SpacesView from './components/SpacesView.vue'
import TrustCenterView from './components/TrustCenterView.vue'
import type {
  AskResponse,
  CollectPayload,
  ContextUpdatePayload,
  FocusGraph,
  GraphPayload,
  GraphSpace,
  IngestResponse,
  LocalFileResult,
  ProviderConfig,
  RecallMode,
  RecallStage,
  SavedQuestion,
  Source,
  Suggestion,
  WorkspaceState,
} from './types'
import type {
  TrustBatchPayload,
  TrustDiagnostics,
  TrustOpenLoopPayload,
  TrustOpenLoopUpdatePayload,
  TrustReviewDetailPayload,
  TrustReviewFilters,
  TrustReviewPayload,
} from './components/trustCenterTypes'

type ActiveView = 'recall' | 'spaces' | 'trust' | 'collect'
type ToastKind = 'info' | 'error'

const navItems = [
  { id: 'recall' as const, label: '聊天', icon: markRaw(MessageSquare) },
  { id: 'spaces' as const, label: '知识库', icon: markRaw(BookOpen) },
  { id: 'trust' as const, label: '信任', icon: markRaw(ShieldCheck) },
  { id: 'collect' as const, label: '收集', icon: markRaw(PenLine) },
]

const activeView = ref<ActiveView>('recall')
const sidebarCollapsed = ref(false)
const selectedSpaceId = ref('all')
const busy = ref(false)
const busyStage = ref('')
const workspace = ref<WorkspaceState | null>(null)
const config = ref<ProviderConfig | null>(null)
const spaces = ref<GraphSpace[]>([])
const allSources = ref<Source[]>([])
const spaceSources = ref<Source[]>([])
const savedQuestions = ref<SavedQuestion[]>([])
const spaceGraph = ref<GraphPayload>({ nodes: [], edges: [] })
const spaceSuggestions = ref<Suggestion[]>([])
const focusGraph = ref<FocusGraph | null>(null)
const askResult = ref<AskResponse | null>(null)
const currentRecallQuestion = ref('')
const currentRecallSpaceId = ref('all')
const selectedRecallMode = ref<RecallMode>('auto')
const currentRecallMode = ref<RecallMode>('auto')
const recallStages = ref<RecallStage[]>([])
const collectResults = ref<IngestResponse[]>([])
const recentBatchSourceIds = ref<string[]>([])
const trustReview = ref<TrustReviewPayload>(emptyTrustReview())
const trustReviewDetail = ref<TrustReviewDetailPayload | null>(null)
const trustOpenLoops = ref<TrustOpenLoopPayload>(emptyTrustOpenLoops())
const trustDiagnostics = ref<TrustDiagnostics | null>(null)
const selectedTrustSourceIds = ref<string[]>([])
const trustFilters = ref<TrustReviewFilters>({})
const settingsOpen = ref(false)
const activityOpen = ref(false)
const toast = ref('')
const toastKind = ref<ToastKind>('info')

const providerLabel = computed(() => {
  const provider = config.value?.runtime?.provider_used || config.value?.provider || 'mock'
  const model = config.value?.runtime?.model_used || config.value?.model || ''
  return model ? `${provider} · ${model}` : provider
})

const providerTruthLabel = computed(() => {
  const provider = config.value?.runtime?.provider_used || config.value?.provider || 'mock'
  const model = config.value?.runtime?.model_used || config.value?.model || ''
  const fallback = config.value?.runtime?.fallback_used ? ' · fallback' : ''
  if (provider === 'mock') return 'MockLLM · 本地确定性'
  return model ? `${provider} · ${model}${fallback}` : `${provider}${fallback}`
})

const providerActionLabel = computed(() => {
  const provider = config.value?.runtime?.provider_used || config.value?.provider || 'mock'
  if (provider === 'mock') return 'MockLLM 正在按本地证据组织回答。'
  return `${providerTruthLabel.value} 正在组织回答。`
})

const providerFallbackLabel = computed(() => {
  const runtime = config.value?.runtime
  if (runtime?.fallback_used) return '模型调用失败时会回退到本地证据回答。'
  if (runtime?.provider_ready === false) return '当前模型未就绪，SnapGraph 会先保留本地证据。'
  return '真实模型只在需要生成回答时参与，证据仍来自本地 SnapGraph。'
})

const runtimeStatusLabel = computed(() => {
  return config.value?.has_api_key ? '本地记忆已连接' : '本地演示模式'
})

const runtimeStatusDetail = computed(() => {
  return config.value?.has_api_key
    ? providerFallbackLabel.value
    : '当前适合本地演示和确定性测试，回答会优先保留证据链。'
})

const activeViewLabel = computed(() => navItems.find((item) => item.id === activeView.value)?.label || '聊天')

const selectedSpaceName = computed(() => {
  if (selectedSpaceId.value === 'all') return '全部记忆'
  const space = spaces.value.find((item) => item.id === selectedSpaceId.value)
  return space ? graphSpaceDisplayName(space) : '记忆空间'
})

const sessionTitle = computed(() => {
  if (activeView.value === 'recall') {
    return currentRecallQuestion.value || askResult.value?.question || '新对话'
  }
  if (activeView.value === 'spaces') return selectedSpaceName.value
  if (activeView.value === 'trust') return '信任检查'
  return '收集'
})

const sessionSubtitle = computed(() => {
  if (activeView.value === 'recall') return busy.value ? busyStage.value || '正在找回' : '找回入口'
  if (activeView.value === 'spaces') return `${spaces.value.length} 个空间`
  if (activeView.value === 'trust') return `${trustReview.value.summary.ai_inferred} 条 AI 猜测`
  return collectResults.value.length ? `${collectResults.value.length} 份材料已进入知识库` : '收集入口'
})

const recentRecallQuestions = computed(() => savedQuestions.value.slice(0, 6).map((item) => ({
  id: item.id,
  question: item.question,
  path: item.path,
})))

const openFilesForCurrentRecall = computed(() => {
  const question = currentRecallQuestion.value || askResult.value?.question || ''
  const match = savedQuestions.value.find((item) => item.question === question)
  return match ? [{ path: match.path, title: match.question, source_id: match.id }] : []
})

function graphSpaceDisplayName(space: GraphSpace) {
  if (space.id === 'inbox') return '待整理'
  if (space.id === 'default') return '主记忆'
  return space.name
}

const workspaceSummary = computed(() => {
  if (!workspace.value) return '未加载'
  return `${workspace.value.sources} 份材料 · ${workspace.value.nodes} 个节点`
})

const showActivityPanel = computed(() => activityOpen.value)

const evidenceSummary = computed(() => {
  const summary = focusGraph.value?.confidence_summary
  if (!summary) return `${allSources.value.length} 份材料`
  return `${summary.source_count} 份材料 · ${summary.confidence_label}`
})

const activityEvidenceDetail = computed(() => {
  if (recentBatchSourceIds.value.length) {
    return `本轮会优先读取刚上传的 ${recentBatchSourceIds.value.length} 份材料，再扩展到旧记忆。`
  }
  const summary = focusGraph.value?.confidence_summary
  if (!summary) return '等待一次找回后，会显示用户原话、AI 猜测和证据数量。'
  return `${summary.user_stated} 条用户原话，${summary.ai_inferred} 条 AI 猜测线索。`
})

const graphSummary = computed(() => {
  const nodes = workspace.value?.nodes ?? spaceGraph.value.nodes.length
  const edges = workspace.value?.edges ?? spaceGraph.value.edges.length
  return `${nodes} 个节点 · ${edges} 条连接`
})

const pendingSummary = computed(() => {
  const pending = spaces.value.reduce((total, space) => total + (space.pending_suggestions || 0), 0)
  if (pending) return `${pending} 条知识库整理建议等待确认。`
  return '当前没有待确认建议，可以继续收集或找回。'
})

function emptyTrustReview(): TrustReviewPayload {
  return {
    items: [],
    filters: {},
    summary: {
      total: 0,
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      unreviewed: 0,
      confirmed: 0,
      rewritten: 0,
      rejected: 0,
      deferred: 0,
      ai_inferred: 0,
      user_stated: 0,
      open_loop_items: 0,
    },
  }
}

function emptyTrustOpenLoops(): TrustOpenLoopPayload {
  return {
    items: [],
    summary: {
      total: 0,
      by_state: {
        active: 0,
        next: 0,
        resolved: 0,
        dismissed: 0,
      },
      by_risk: {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0,
      },
    },
  }
}

function trustQueryString(filters: TrustReviewFilters) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value === '' || value === null || value === undefined) return
    params.set(key, String(value))
  })
  const query = params.toString()
  return query ? `?${query}` : ''
}

onMounted(() => {
  refreshShell()
})

function setView(view: ActiveView) {
  activeView.value = view
  if (view === 'spaces' && selectedSpaceId.value !== 'all') {
    loadSpaceDetail(selectedSpaceId.value)
  }
  if (view === 'trust') {
    loadTrustCenter()
  }
}

function startNewRecall() {
  activeView.value = 'recall'
  currentRecallQuestion.value = ''
  currentRecallSpaceId.value = 'all'
  askResult.value = null
  focusGraph.value = null
  recallStages.value = []
  recentBatchSourceIds.value = []
  activityOpen.value = false
}

function startCollect() {
  activeView.value = 'collect'
  activityOpen.value = false
}

async function refreshShell() {
  try {
    await Promise.all([loadWorkspace(), loadConfig(), loadSpaces(), loadAllSources(), loadQuestions(), loadTrustCenter()])
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

async function loadQuestions() {
  savedQuestions.value = await api<SavedQuestion[]>('/api/questions')
}

async function loadTrustCenter() {
  const query = trustQueryString(trustFilters.value)
  const [review, loops, diagnostics] = await Promise.all([
    api<TrustReviewPayload>(`/api/trust/review${query}`),
    api<TrustOpenLoopPayload>('/api/trust/open-loops'),
    api<TrustDiagnostics>('/api/trust/diagnostics'),
  ])
  trustReview.value = review
  trustOpenLoops.value = loops
  trustDiagnostics.value = diagnostics
  const available = new Set(review.items.map((item) => item.source_id))
  selectedTrustSourceIds.value = selectedTrustSourceIds.value.filter((sourceId) => available.has(sourceId))
  if (trustReviewDetail.value && !available.has(trustReviewDetail.value.item.source_id)) {
    trustReviewDetail.value = null
  }
  if (!trustReviewDetail.value && review.items[0]) {
    await selectTrustReview(review.items[0].source_id)
  } else if (trustReviewDetail.value) {
    await selectTrustReview(trustReviewDetail.value.item.source_id)
  }
}

async function selectTrustReview(sourceId: string) {
  if (!sourceId) {
    trustReviewDetail.value = null
    return
  }
  trustReviewDetail.value = await api<TrustReviewDetailPayload>(`/api/trust/review/${encodeURIComponent(sourceId)}`)
}

function toggleTrustSelection(sourceId: string) {
  if (!sourceId) return
  selectedTrustSourceIds.value = selectedTrustSourceIds.value.includes(sourceId)
    ? selectedTrustSourceIds.value.filter((item) => item !== sourceId)
    : [...selectedTrustSourceIds.value, sourceId]
}

async function updateTrustFilters(filters: TrustReviewFilters) {
  trustFilters.value = {
    ...filters,
    has_open_loops: filters.has_open_loops ?? null,
  }
  await loadTrustCenter()
}

async function applyTrustBatch(payload: TrustBatchPayload) {
  if (!payload.source_ids.length) return
  busy.value = true
  try {
    await api('/api/trust/review/batch', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    selectedTrustSourceIds.value = []
    await Promise.all([loadTrustCenter(), loadAllSources(), loadWorkspace()])
    showToast('信任审查已更新。')
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function updateTrustOpenLoop(loopId: string, payload: TrustOpenLoopUpdatePayload) {
  busy.value = true
  try {
    await api(`/api/trust/open-loops/${encodeURIComponent(loopId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
    await loadTrustCenter()
    showToast('Open loop 状态已更新。')
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
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
  currentRecallSpaceId.value = selectedSpaceId.value === 'all' ? 'all' : selectedSpaceId.value
  activeView.value = 'recall'
  await runRecall(question, 'auto')
}

async function askRecentBatch(question = '结合刚才上传的这批材料，我们下一步最应该优先完善什么？') {
  const fallbackIds = collectResults.value.map((result) => result.source_id).filter(Boolean)
  if (!recentBatchSourceIds.value.length && fallbackIds.length) {
    recentBatchSourceIds.value = fallbackIds
  }
  currentRecallSpaceId.value = selectedSpaceId.value === 'all' ? 'all' : selectedSpaceId.value
  activeView.value = 'recall'
  await runRecall(question, 'auto', { preserveContext: true })
}

async function runRecall(
  question: string,
  mode: RecallMode = selectedRecallMode.value,
  options: { preserveContext?: boolean } = {},
) {
  if (!options.preserveContext) {
    recentBatchSourceIds.value = []
  }
  currentRecallSpaceId.value = recallSpaceScope()
  selectedRecallMode.value = mode
  currentRecallMode.value = mode
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
  if (mode !== 'answer') {
    busyStage.value = '先找本地证据。'
    try {
      focusGraph.value = await api<FocusGraph>('/api/focus', {
        method: 'POST',
        body: JSON.stringify(recallRequestPayload(question)),
      })
      updateRecallStage({ id: 'evidence', label: '找本地证据', status: 'done', detail: `找到 ${focusGraph.value.evidence_cards.length} 条线索` })
    } catch (error) {
      updateRecallStage({ id: 'evidence', label: '找本地证据', status: 'error', detail: '本地证据检索失败' })
      showToast(`本地证据检索失败：${messageFromError(error)}`, 'error')
    }
  }

  if (mode === 'files') {
    busy.value = false
    busyStage.value = ''
    return
  }

  busyStage.value = providerActionLabel.value
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
    body: JSON.stringify(recallRequestPayload(question, false)),
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
    text: `# 回答\n## 结论\n${text}`,
    contexts: focusGraph.value?.evidence_cards || [],
    graph_paths: [],
    focus_graph: focusGraph.value || emptyFocusGraph(),
    local_files: focusGraph.value?.local_files || [],
  }
}

function emptyFocusGraph(): FocusGraph {
  return {
    nodes: [],
    edges: [],
    evidence_cards: [],
    local_files: [],
    open_loops: [],
    confidence_summary: {
      source_count: 0,
      user_stated: 0,
      ai_inferred: 0,
      confidence_label: 'none',
    },
  }
}

function recallRequestPayload(question: string, save?: boolean) {
  const contextSourceIds = currentContextSourceIds()
  return {
    question,
    space_id: recallSpaceScope(),
    ...(save === undefined ? {} : { save }),
    ...(contextSourceIds.length ? { context_source_ids: contextSourceIds } : {}),
  }
}

function recallSpaceScope() {
  if (currentRecallSpaceId.value && currentRecallSpaceId.value !== 'all') {
    return currentRecallSpaceId.value
  }
  if (selectedSpaceId.value && selectedSpaceId.value !== 'all' && activeView.value === 'spaces') {
    return selectedSpaceId.value
  }
  return 'all'
}

function currentContextSourceIds() {
  return recentBatchSourceIds.value
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
  recentBatchSourceIds.value = []
  const uploadedSourceIds: string[] = []
  try {
    for (const [index, file] of files.entries()) {
      busyStage.value = `正在放入知识库 ${index + 1}/${files.length}。`
      const form = new FormData()
      form.append('file', file)
      form.append('why', payload.why)
      form.append('route_mode', payload.routeMode)
      if (payload.routeMode === 'manual') form.append('space_id', payload.spaceId)
      const result = await api<IngestResponse>('/api/ingest', { method: 'POST', body: form })
      uploadedSourceIds.push(result.source_id)
      collectResults.value.unshift(result)
    }
    recentBatchSourceIds.value = uploadedSourceIds
    showToast('材料已进入知识库。')
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

async function updateSourceTitle(sourceId: string, title: string) {
  const nextTitle = title.trim()
  if (!sourceId || !nextTitle) return

  busy.value = true
  try {
    const response = await api<{ detail: Source }>(`/api/sources/${encodeURIComponent(sourceId)}/title`, {
      method: 'PATCH',
      body: JSON.stringify({ title: nextTitle }),
    })
    const savedTitle = response.detail?.title || nextTitle
    collectResults.value = collectResults.value.map((result) => (
      result.source_id === sourceId ? renameIngestResult(result, savedTitle) : result
    ))
    await refreshShell()
    showToast('保存名称已更新。')
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function openLocalFile(file: LocalFileResult) {
  try {
    await api('/api/open-local', {
      method: 'POST',
      body: JSON.stringify({
        source_id: file.source_id,
        target: file.open_target || 'raw',
      }),
    })
    showToast('已打开本地文件。')
  } catch (error) {
    showToast(`打开本地文件失败：${messageFromError(error)}`, 'error')
  }
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
    showToast('记忆空间已创建。')
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
    showToast('记忆空间已更新。')
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

function renameIngestResult(result: IngestResponse, title: string): IngestResponse {
  return {
    ...result,
    title,
    focus_graph: {
      ...result.focus_graph,
      nodes: result.focus_graph.nodes.map((node) => (
        node.id === `source_${result.source_id}` ? { ...node, label: title } : node
      )),
      evidence_cards: result.focus_graph.evidence_cards.map((card) => (
        card.source_id === result.source_id ? { ...card, title } : card
      )),
    },
  }
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
