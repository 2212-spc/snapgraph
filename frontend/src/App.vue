<template>
  <div class="app study-shell snapgraph-reference-shell">
    <aside class="side study-sidebar">
      <div class="brand">
        <button class="brand-main" type="button" @click="setView('recall')">
          <span class="wordmark">SnapGraph</span>
          <span class="sub">AI 认知记忆图谱</span>
        </button>
      </div>

      <nav class="nav" aria-label="SnapGraph layers">
        <button
          v-for="item in navItems"
          :key="item.id"
          :class="{ active: activeView === item.id }"
          type="button"
          @click="setView(item.id)"
        >
          <span class="seal">{{ item.seal }}</span>
          <span class="label">{{ item.label }}</span>
          <span v-if="item.badge" class="badge">{{ item.badge }}</span>
        </button>
      </nav>

      <section class="side-history" aria-label="最近对话">
        <div class="side-history-title">最近对话</div>
        <button
          v-for="thread in sideHistoryThreads"
          :key="thread.id"
          class="side-history-item"
          type="button"
          @click="reopenRecallThread(thread)"
        >
          <span class="side-history-question">{{ compactRailText(thread.question, 30) }}</span>
          <span class="side-history-meta">{{ thread.depth === 'deep' ? '深度 Thought' : '快速' }} · {{ thread.mode === 'files' ? '文件找回' : thread.mode === 'answer' ? '只要回答' : '自动模式' }}</span>
        </button>
        <p v-if="!sideHistoryThreads.length" class="side-history-empty">还没有聊天历史</p>
      </section>

      <div class="side-foot sidebar-footer">
        <button class="link sidebar-settings" type="button" @click="settingsOpen = true">设置</button>
        <div class="status">
          <span class="dot-live"></span>
          <span>{{ runtimeStatusLabel }}<br>{{ workspaceSummary }}</span>
        </div>
      </div>
    </aside>

    <main class="main study-chat-shell" :class="{ chat: hasRecallConversation, 'is-recall-chat': hasRecallConversation }">
      <RecallHome
        v-if="activeView === 'recall'"
        :busy="busy"
        :busy-stage="busyStage"
        :mode="selectedRecallMode"
        :depth="selectedRecallDepth"
        :result-mode="currentRecallMode"
        :result="askResult"
        :focus-graph="focusGraph"
        :stages="recallStages"
        :current-thought="currentThought"
        :thought-history="thoughtHistory"
        :current-question="currentRecallQuestion"
        :recent-questions="recentRecallQuestions"
        :turns="recallTurns"
        @recall="runRecall"
        @mode-changed="selectedRecallMode = $event"
        @depth-changed="selectedRecallDepth = $event"
        @open-local-file="openLocalFile"
        @reset="startNewRecall"
      />

      <OrganizeView
        v-else-if="activeView === 'emerge'"
        :busy="busy"
        :review="trustReview"
        :detail="trustReviewDetail"
        :open-loops="trustOpenLoops"
        :all-sources="allSources"
        @batch-action="applyTrustBatch"
        @update-open-loop="updateTrustOpenLoop"
        @ask-from-graph="askFromGraph"
        @open-source="openSourceById"
        @go-shelf="setView('shelf')"
      />

      <CollectView
        v-else-if="activeView === 'collect'"
        :busy="busy"
        :spaces="spaces"
        :results="collectResults"
        @collect="collectMaterials"
        @open-space="openCollectedSpace"
        @ask-batch="askRecentBatch"
        @update-title="updateSourceTitle"
      />

      <ShelfView
        v-else
        :busy="busy"
        :spaces="spaces"
        :all-sources="allSources"
        :questions="savedQuestions"
        :review="trustReview"
        :open-loops="trustOpenLoops"
        :diagnostics="trustDiagnostics"
        @ask-from-graph="askFromGraph"
        @open-source="openSourceById"
        @go-emerge="setView('emerge')"
        @start-collect="startCollect"
        @create-space="createSpace"
      />
    </main>

    <aside v-if="showRecallRail" class="rail recall-rail" aria-label="SnapGraph recall activity">
      <div>
        <div class="r-lbl">本场对话碰到的记忆</div>
        <div class="rail-graph">
          <svg class="rg" viewBox="0 0 250 168" xmlns="http://www.w3.org/2000/svg" aria-label="本场记忆图谱">
            <path class="e" d="M52,52 C95,40 130,52 150,78" />
            <path class="e" d="M52,52 C60,95 78,118 110,128" />
            <path class="e con" d="M150,78 C190,95 200,118 168,132" />
            <path class="e new" d="M52,52 C110,18 150,22 150,46" />
            <path class="e new" d="M168,132 C160,90 150,60 150,48" />
            <circle class="pulse" cx="150" cy="44" r="9" />
            <circle class="ny" cx="52" cy="52" r="8" />
            <circle class="na" cx="150" cy="78" r="7" />
            <circle class="na" cx="110" cy="128" r="7" />
            <circle class="na" cx="168" cy="132" r="7" />
            <circle class="nn" cx="150" cy="44" r="8" />
            <text x="52" y="38" text-anchor="middle">{{ railGraphLabels[0] }}</text>
            <text class="ai" x="150" y="98" text-anchor="middle">{{ railGraphLabels[1] }}</text>
            <text class="ai" x="110" y="148" text-anchor="middle">{{ railGraphLabels[2] }}</text>
            <text class="ai" x="178" y="150" text-anchor="middle">未闭环</text>
            <text x="150" y="30" text-anchor="middle" class="new-label">Thought ★</text>
          </svg>
        </div>
        <div v-if="currentThought" class="r-claimed">
          ★ 深度 Thought 已接入 <b>{{ currentThought.evidence_titles.length || railLocalFiles.length }}</b> 条线索
        </div>
      </div>

      <div>
        <div class="r-lbl">引用到的你的原话</div>
        <div class="r-list">
          <button
            v-for="file in railLocalFiles"
            :key="file.source_id"
            class="r-item"
            type="button"
            @click="openLocalFile(file)"
          >
            <span class="it-q">「{{ compactRailText(file.source_excerpt || file.match_reason || file.title, 54) }}」</span>
            <span class="it-m">{{ file.title }} · {{ file.space_name || '本地材料' }}</span>
          </button>
          <p v-if="!railLocalFiles.length" class="r-empty">
            还没引用到原话。被召回的每一句都会停在这里，一字不改，可点开原文。
          </p>
        </div>
      </div>

      <div>
        <div class="r-lbl">最近的对话</div>
        <div class="r-list">
          <button
            v-for="thread in railHistoryThreads"
            :key="thread.id"
            class="r-item recall-history-item"
            type="button"
            @click="reopenRecallThread(thread)"
          >
            <span class="it-q">「{{ compactRailText(thread.question, 42) }}」</span>
            <span class="it-m">{{ thread.depth === 'deep' ? '深度 Thought' : '快速' }} · {{ thread.mode === 'files' ? '只找文件' : thread.mode === 'answer' ? '只要回答' : '全部材料' }}</span>
          </button>
        </div>
      </div>

      <div class="r-foot">
        一切都在本地 · Thought 显示公开摘要<br>
        AI 从不冒充你，原话永远用宋体苔绿标出。
      </div>
    </aside>

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
import { computed, markRaw, nextTick, onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'
import { normalizeRestoredAnswerMarkdown } from './answerDisplay'
import CollectView from './components/CollectView.vue'
import OrganizeView from './components/OrganizeView.vue'
import RecallHome from './components/RecallHome.vue'
import ShelfView from './components/ShelfView.vue'
import type {
  AskResponse,
  CollectPayload,
  ContextUpdatePayload,
  EvidenceCard,
  FocusGraph,
  GraphPayload,
  GraphSpace,
  IngestResponse,
  LocalFileResult,
  ProviderConfig,
  RecallConversationTurn,
  RecallDepth,
  RecallHistoryItem,
  RecallHistoryPayload,
  RecallMode,
  RecallStage,
  RecallThought,
  RecallThoughtTraceEvent,
  SavedQuestion,
  Source,
  Suggestion,
  ThoughtHistoryPayload,
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

type ActiveView = 'recall' | 'emerge' | 'collect' | 'shelf'
type ToastKind = 'info' | 'error'
type RecallThread = {
  id: string
  question: string
  mode: RecallMode
  depth: RecallDepth
  spaceId: string
  contextCount?: number
  localFileCount?: number
  answerPreview?: string
  thoughtSummary?: string
  updatedAt: string
}

const navItems: Array<{ id: ActiveView; label: string; seal: string; badge?: string }> = [
  { id: 'recall', label: '问过去', seal: '问' },
  { id: 'emerge', label: '涌现', seal: '涌', badge: '3 条新连接' },
  { id: 'collect', label: '收下', seal: '收' },
  { id: 'shelf', label: '书架', seal: '架' },
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
const savedQuestions = ref<SavedQuestion[]>([])
const spaceGraph = ref<GraphPayload>({ nodes: [], edges: [] })
const spaceSuggestions = ref<Suggestion[]>([])
const focusGraph = ref<FocusGraph | null>(null)
const askResult = ref<AskResponse | null>(null)
const currentThought = ref<RecallThought | null>(null)
const thoughtHistory = ref<ThoughtHistoryPayload | null>(null)
const currentRecallQuestion = ref('')
const currentRecallThreadId = ref('')
const currentRecallTurnId = ref('')
const currentRecallSpaceId = ref('all')
const selectedRecallMode = ref<RecallMode>('auto')
const currentRecallMode = ref<RecallMode>('auto')
const selectedRecallDepth = ref<RecallDepth>('quick')
const recallStages = ref<RecallStage[]>([])
const recallThreads = ref<RecallThread[]>([])
const recallHistoryItems = ref<RecallHistoryItem[]>([])
const recallTurns = ref<RecallConversationTurn[]>([])
const collectResults = ref<IngestResponse[]>([])
const recentBatchSourceIds = ref<string[]>([])
const trustReview = ref<TrustReviewPayload>(emptyTrustReview())
const trustReviewDetail = ref<TrustReviewDetailPayload | null>(null)
const trustOpenLoops = ref<TrustOpenLoopPayload>(emptyTrustOpenLoops())
const trustDiagnostics = ref<TrustDiagnostics | null>(null)
const selectedTrustSourceIds = ref<string[]>([])
const trustFilters = ref<TrustReviewFilters>({})
const settingsOpen = ref(false)
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

const activeViewLabel = computed(() => navItems.find((item) => item.id === activeView.value)?.label || '问过去')

const selectedSpaceName = computed(() => {
  if (selectedSpaceId.value === 'all') return '全部记忆'
  const space = spaces.value.find((item) => item.id === selectedSpaceId.value)
  return space ? graphSpaceDisplayName(space) : '记忆空间'
})

const sessionTitle = computed(() => {
  if (activeView.value === 'recall') {
    return currentRecallQuestion.value || askResult.value?.question || '新对话'
  }
  if (activeView.value === 'emerge') return '涌现'
  if (activeView.value === 'collect') return '收下'
  return selectedSpaceName.value === '全部记忆' ? '书架' : selectedSpaceName.value
})

const recentRecallQuestions = computed(() => recallThreads.value)
const hasRecallConversation = computed(() => (
  activeView.value === 'recall'
  && Boolean(askResult.value || focusGraph.value || busy.value || currentRecallQuestion.value)
))
const showRecallRail = computed(() => hasRecallConversation.value)
const railLocalFiles = computed<LocalFileResult[]>(() => (
  askResult.value?.local_files || focusGraph.value?.local_files || []
))
const railHistoryThreads = computed(() => recallThreads.value.slice(0, 4))
const sideHistoryThreads = computed(() => recallThreads.value.slice(0, 8))
const railGraphLabels = computed(() => {
  const labels = railLocalFiles.value.slice(0, 3).map((file) => compactRailText(file.title, 9))
  return [
    labels[0] || '召回判断',
    labels[1] || 'AI 猜测',
    labels[2] || '本地证据',
  ]
})

function navDetail(view: ActiveView) {
  if (view === 'recall') return '找回或一起想'
  if (view === 'emerge') return '看新连接'
  if (view === 'collect') return '给未来留一句'
  return '材料和空间'
}

function graphSpaceDisplayName(space: GraphSpace) {
  if (space.id === 'inbox') return '待整理'
  if (space.id === 'default') return '主记忆'
  return space.name
}

const workspaceSummary = computed(() => {
  if (!workspace.value) return '未加载'
  return `${workspace.value.sources} 份材料 · ${workspace.value.nodes} 个节点`
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
  recallThreads.value = loadRecallThreads()
  refreshShell()
})

function setView(view: ActiveView) {
  activeView.value = view
  if (view === 'shelf' && selectedSpaceId.value !== 'all') {
    loadSpaceDetail(selectedSpaceId.value)
  }
  if (view === 'emerge' || view === 'shelf') {
    loadTrustCenter()
  }
}

function startNewRecall() {
  activeView.value = 'recall'
  currentRecallQuestion.value = ''
  currentRecallThreadId.value = ''
  currentRecallTurnId.value = ''
  currentRecallSpaceId.value = 'all'
  askResult.value = null
  currentThought.value = null
  focusGraph.value = null
  recallStages.value = []
  recallTurns.value = []
  recentBatchSourceIds.value = []
}

function startCollect() {
  activeView.value = 'collect'
}

async function refreshShell() {
  try {
    await Promise.all([
      loadWorkspace(),
      loadConfig(),
      loadSpaces(),
      loadAllSources(),
      loadQuestions(),
      loadTrustCenter(),
      loadThoughtHistory(),
      loadRecallHistory(),
    ])
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

async function loadThoughtHistory() {
  thoughtHistory.value = await api<ThoughtHistoryPayload>('/api/thought-history?limit=4')
}

async function loadRecallHistory() {
  const payload = await api<RecallHistoryPayload>('/api/recall-history?limit=12')
  recallHistoryItems.value = payload.items
  recallThreads.value = mergeRecallThreads(
    payload.items.map(recallHistoryToThread),
    recallThreads.value,
  )
  persistRecallThreads(recallThreads.value)
}

async function loadRecallThreadHistory(threadId: string) {
  const payload = await api<RecallHistoryPayload>(`/api/recall-history?thread_id=${encodeURIComponent(threadId)}&limit=50`)
  recallHistoryItems.value = mergeRecallHistoryItems(payload.items, recallHistoryItems.value)
  return payload.items
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
    showToast('整理结果已更新。')
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
    showToast('问题状态已更新。')
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
  depthOrOptions: RecallDepth | { preserveContext?: boolean } = selectedRecallDepth.value,
  optionsArg: { preserveContext?: boolean } = {},
) {
  const depth = typeof depthOrOptions === 'string' ? depthOrOptions : selectedRecallDepth.value
  const options = typeof depthOrOptions === 'string' ? optionsArg : depthOrOptions
  if (!options.preserveContext) {
    recentBatchSourceIds.value = []
  }
  currentRecallSpaceId.value = recallSpaceScope()
  currentRecallThreadId.value = rememberRecallThread(question, mode, depth, currentRecallSpaceId.value)
  currentRecallTurnId.value = createRecallTurn(question, mode, depth, currentRecallSpaceId.value)
  selectedRecallMode.value = mode
  currentRecallMode.value = mode
  selectedRecallDepth.value = depth
  busy.value = true
  currentRecallQuestion.value = question
  askResult.value = null
  currentThought.value = null
  focusGraph.value = null
  recallStages.value = initialRecallStages(depth)
  updateRecallTurn(currentRecallTurnId.value, { stages: recallStages.value })
  if (mode !== 'answer') {
    busyStage.value = '先找本地证据。'
    try {
      focusGraph.value = await api<FocusGraph>('/api/focus', {
        method: 'POST',
        body: JSON.stringify(recallRequestPayload(question)),
      })
      updateRecallTurn(currentRecallTurnId.value, {
        focusGraph: focusGraph.value,
        localFiles: focusGraph.value.local_files || [],
      })
      updateRecallStage({ id: 'evidence', label: '找本地证据', status: 'done', detail: `找到 ${focusGraph.value.evidence_cards.length} 条线索` })
      if (focusGraph.value.thought) {
        currentThought.value = focusGraph.value.thought
        updateRecallTurn(currentRecallTurnId.value, { currentThought: currentThought.value })
        updateRecallStage({ id: 'thought', label: '形成 Thought', status: 'done', detail: '已先完成本轮思考' })
      }
      void scrollRecallThreadToBottom({ force: true })
    } catch (error) {
      updateRecallStage({ id: 'evidence', label: '找本地证据', status: 'error', detail: '本地证据检索失败' })
      showToast(`本地证据检索失败：${messageFromError(error)}`, 'error')
    }
  }

  if (mode === 'files') {
    updateRecallStage({ id: 'read', label: '读用户原话', status: 'done', detail: '停在本地文件结果' })
    updateRecallStage({ id: 'connect', label: '检查图谱连接', status: 'done', detail: `${focusGraph.value?.edges.length || 0} 条可见连接` })
    updateRecallStage({ id: 'write', label: '生成 AI 回复', status: 'done', detail: '只找文件模式不生成回答' })
    void scrollRecallThreadToBottom({ force: true })
    void loadRecallHistory()
    busy.value = false
    updateRecallTurn(currentRecallTurnId.value, { busy: false })
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
    updateRecallTurn(currentRecallTurnId.value, { busy: false })
    busyStage.value = ''
  }
}

function initialRecallStages(depth: RecallDepth): RecallStage[] {
  return [
    { id: 'evidence', label: '找本地证据', status: 'active', detail: '先从本地图谱里找回线索' },
    { id: 'thought', label: '形成 Thought', status: depth === 'deep' ? 'pending' : 'done', detail: depth === 'deep' ? '后端 solve 模式会先规划再回答' : '快速模式跳过展示' },
    { id: 'read', label: '读用户原话', status: 'pending' },
    { id: 'connect', label: '检查图谱连接', status: 'pending' },
    { id: 'write', label: '生成 AI 回复', status: 'pending' },
  ]
}

function createRecallTurn(question: string, mode: RecallMode, depth: RecallDepth, spaceId: string) {
  const threadId = currentRecallThreadId.value || rememberRecallThread(question, mode, depth, spaceId)
  const turnIndex = recallTurns.value.filter((turn) => turn.threadId === threadId).length + 1
  const turnId = `turn-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
  const turn: RecallConversationTurn = {
    threadId,
    turnId,
    turnIndex,
    question,
    mode,
    depth,
    spaceId,
    result: null,
    focusGraph: null,
    stages: initialRecallStages(depth),
    currentThought: null,
    localFiles: [],
    busy: true,
  }
  recallTurns.value = [...recallTurns.value, turn]
  return turnId
}

function updateRecallTurn(turnId: string, patch: Partial<RecallConversationTurn>) {
  if (!turnId) return
  recallTurns.value = recallTurns.value.map((turn) => (
    turn.turnId === turnId
      ? {
          ...turn,
          ...patch,
          stages: patch.stages ? [...patch.stages] : turn.stages,
        }
      : turn
  ))
}

async function reopenRecallThread(thread: RecallThread) {
  activeView.value = 'recall'
  currentRecallThreadId.value = thread.id
  currentRecallSpaceId.value = thread.spaceId || 'all'
  selectedRecallMode.value = thread.mode || selectedRecallMode.value
  selectedRecallDepth.value = thread.depth || selectedRecallDepth.value
  currentRecallMode.value = thread.mode || selectedRecallMode.value

  let items = await loadRecallThreadHistory(thread.id)
  if (!items.length) {
    await loadRecallHistory()
    items = recallHistoryItemsForThread(thread.id)
  }
  restoreRecallThread(thread, items)
}

function recallHistoryItemsForThread(threadId: string) {
  return recallHistoryItems.value
    .filter((item) => (item.thread_id || item.id) === threadId || item.id === threadId)
    .sort((a, b) => {
      const turnDiff = (a.turn_index || 0) - (b.turn_index || 0)
      if (turnDiff !== 0) return turnDiff
      return new Date(a.created_at || a.updated_at || 0).getTime() - new Date(b.created_at || b.updated_at || 0).getTime()
    })
}

function recallHistoryItemToTurn(item: RecallHistoryItem): RecallConversationTurn {
  const thought = recallThoughtFromHistory(item)
  const focus = recallHistoryFocusGraph(item, thought)
  const result: AskResponse = {
    question: item.question,
    text: recallHistoryAnswerMarkdown(item),
    contexts: focus.evidence_cards,
    graph_paths: [],
    focus_graph: focus,
    local_files: focus.local_files || [],
    thought: thought || undefined,
  }
  return {
    threadId: item.thread_id || item.id,
    turnId: item.turn_id || item.id,
    turnIndex: item.turn_index || 1,
    question: item.question,
    mode: item.mode || 'auto',
    depth: item.depth || 'quick',
    spaceId: item.space_id || 'all',
    result,
    focusGraph: focus,
    stages: recallHistoryStages(item, thought),
    currentThought: thought,
    localFiles: focus.local_files || [],
    answerPreview: item.answer_preview || compactRailText(item.answer_text || '', 180),
    busy: false,
  }
}

function restoreRecallThread(thread: RecallThread, items: RecallHistoryItem[]) {
  const restoredTurns = items.map(recallHistoryItemToTurn)
  const turns = restoredTurns.length ? restoredTurns : [recallThreadSummaryToTurn(thread)]
  const latest = turns[turns.length - 1]
  recallTurns.value = turns
  currentRecallThreadId.value = thread.id
  currentRecallTurnId.value = latest.turnId
  currentRecallSpaceId.value = latest.spaceId || thread.spaceId || 'all'
  currentRecallQuestion.value = latest.question || thread.question
  selectedRecallMode.value = latest.mode || thread.mode || selectedRecallMode.value
  currentRecallMode.value = latest.mode || thread.mode || selectedRecallMode.value
  selectedRecallDepth.value = latest.depth || thread.depth || selectedRecallDepth.value
  askResult.value = latest.result
  focusGraph.value = latest.focusGraph
  currentThought.value = latest.currentThought || latest.result?.thought || null
  recallStages.value = [...latest.stages]
  busy.value = false
  busyStage.value = ''
  void scrollRecallThreadToTop()
}

function recallThreadSummaryToTurn(thread: RecallThread): RecallConversationTurn {
  const focus = emptyFocusGraph()
  const result: AskResponse = {
    question: thread.question,
    text: `# 历史记录\n\n${thread.answerPreview || '这条历史只有本地摘要，未重新请求模型。'}`,
    contexts: [],
    graph_paths: [],
    focus_graph: focus,
    local_files: [],
  }
  return {
    threadId: thread.id,
    turnId: thread.id,
    turnIndex: 1,
    question: thread.question,
    mode: thread.mode || 'auto',
    depth: thread.depth || 'quick',
    spaceId: thread.spaceId || 'all',
    result,
    focusGraph: focus,
    stages: recallHistoryStages({
      ...thread,
      mode: thread.mode || 'auto',
      depth: thread.depth || 'quick',
      context_count: thread.contextCount || 0,
      local_file_count: thread.localFileCount || 0,
    } as RecallHistoryItem, null),
    currentThought: null,
    localFiles: [],
    answerPreview: thread.answerPreview || '',
    busy: false,
  }
}

function recallThoughtFromHistory(item: RecallHistoryItem): RecallThought | null {
  const thought = item.thought
  if (!thought || !('id' in thought) || !Array.isArray(thought.lines)) return null
  return {
    id: String(thought.id || item.turn_id || item.id),
    title: String(thought.title || 'Thought'),
    status: thought.status === 'thinking' ? 'thinking' : 'done',
    question: String(thought.question || item.question),
    summary: String(thought.summary || item.thought_summary || ''),
    lines: thought.lines.map((line) => String(line)),
    stage_flow: Array.isArray(thought.stage_flow) ? thought.stage_flow.map((stage) => String(stage)) : [],
    evidence_titles: Array.isArray(thought.evidence_titles) ? thought.evidence_titles.map((title) => String(title)) : [],
    notice: String(thought.notice || '这里显示的是公开求解轨迹摘要，不是隐藏推理草稿。'),
  }
}

function recallHistoryAnswerMarkdown(item: RecallHistoryItem) {
  const answer = (item.answer_text || item.answer_preview || '').trim()
  if (!answer) {
    if (item.mode === 'files') return '# 文件找回\n\n这条历史记录保留了本轮找到的本地线索。'
    return '# 历史回答\n\n这条历史没有重新请求模型，只恢复已保存的记录。'
  }
  const normalized = normalizeRestoredAnswerMarkdown(answer)
  return normalized.startsWith('#') ? normalized : `# 历史回答\n\n${normalized}`
}

function recallHistoryStages(item: Pick<RecallHistoryItem, 'mode' | 'depth' | 'context_count' | 'local_file_count'>, thought: RecallThought | null): RecallStage[] {
  const contextCount = item.context_count || 0
  const fileCount = item.local_file_count || 0
  return [
    { id: 'evidence', label: '找本地证据', status: 'done', detail: `历史记录保留了 ${contextCount} 条线索` },
    {
      id: 'thought',
      label: '形成 Thought',
      status: item.depth === 'deep' ? (thought ? 'done' : 'done') : 'done',
      detail: item.depth === 'deep' ? (thought ? '已恢复公开 Thought' : '历史记录未保存 Thought 细节') : '快速模式跳过展示',
    },
    { id: 'read', label: '读用户原话', status: 'done', detail: fileCount ? `恢复 ${fileCount} 份本地文件` : '已恢复历史摘要' },
    { id: 'connect', label: '检查图谱连接', status: 'done', detail: contextCount ? '按历史证据恢复' : '暂无历史证据节点' },
    { id: 'write', label: '生成 AI 回复', status: 'done', detail: item.mode === 'files' ? '文件找回记录已恢复' : '历史回答已恢复' },
  ]
}

function recallHistoryFocusGraph(item: RecallHistoryItem, thought: RecallThought | null): FocusGraph {
  const evidenceCards = recallHistoryEvidenceCards(item)
  const localFiles = recallHistoryLocalFiles(item)
  return {
    ...emptyFocusGraph(),
    nodes: evidenceCards.map((card) => ({
      id: card.source_id,
      type: 'source',
      label: card.title,
      graph_space_id: item.space_id || 'all',
    })),
    evidence_cards: evidenceCards,
    local_files: localFiles,
    thought: thought || undefined,
    confidence_summary: {
      source_count: evidenceCards.length,
      user_stated: evidenceCards.filter((card) => card.why_saved_status === 'user-stated').length,
      ai_inferred: evidenceCards.filter((card) => card.why_saved_status === 'ai-inferred').length,
      confidence_label: evidenceCards.length ? 'history' : 'none',
    },
  }
}

function recallHistoryEvidenceCards(item: RecallHistoryItem): EvidenceCard[] {
  return item.context_source_ids
    .map((sourceId) => allSources.value.find((source) => source.id === sourceId))
    .filter((source): source is Source => Boolean(source))
    .map((source) => ({
      source_id: source.id,
      title: source.title,
      space_name: source.space_name || graphSpaceDisplayName(spaces.value.find((space) => space.id === source.graph_space_id) || {
        id: source.graph_space_id || 'default',
        name: '主记忆',
        description: '',
        purpose: '',
        color: '',
        status: '',
        source_count: 0,
        node_count: 0,
        edge_count: 0,
        pending_suggestions: 0,
      }),
      why_saved: source.why_saved || source.summary || '历史记录引用了这份材料。',
      why_saved_status: source.why_saved_status || 'unknown',
      related_project: source.related_project || '',
      open_loops: source.open_loops || [],
      future_recall_questions: source.future_recall_questions || [],
      source_excerpt: source.summary || source.why_saved || source.title,
      review_status: source.review_status,
      review_note: source.review_note,
      reviewed_at: source.reviewed_at,
    }))
}

function recallHistoryLocalFiles(item: RecallHistoryItem): LocalFileResult[] {
  return item.context_source_ids
    .map((sourceId) => allSources.value.find((source) => source.id === sourceId))
    .filter((source): source is Source => Boolean(source))
    .map((source) => ({
      source_id: source.id,
      title: source.title,
      path: source.path || source.original_filename || source.title,
      raw_path: source.path || source.original_filename || source.title,
      open_target: 'source_page',
      why_saved: source.why_saved,
      why_saved_status: source.why_saved_status,
      space_name: source.space_name,
      source_excerpt: source.summary || source.why_saved || source.title,
      match_reason: source.summary || source.why_saved || '历史记录引用了这份材料。',
    }))
}

function rememberRecallThread(question: string, mode: RecallMode, depth: RecallDepth, spaceId: string) {
  const normalizedQuestion = question.trim()
  const updatedAt = new Date().toISOString()
  const existing = (
    currentRecallThreadId.value
      ? recallThreads.value.find((thread) => thread.id === currentRecallThreadId.value)
      : null
  ) || recallThreads.value.find((thread) => thread.question === normalizedQuestion)
  const nextThread: RecallThread = {
    id: existing?.id || currentRecallThreadId.value || `recall-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
    question: normalizedQuestion,
    mode,
    depth,
    spaceId: spaceId || 'all',
    updatedAt,
  }
  recallThreads.value = [
    nextThread,
    ...recallThreads.value.filter((thread) => thread.id !== nextThread.id && thread.question !== normalizedQuestion),
  ].slice(0, 12)
  persistRecallThreads(recallThreads.value)
  return nextThread.id
}

function loadRecallThreads(): RecallThread[] {
  try {
    const raw = window.localStorage.getItem('snapgraph.recallThreads')
    if (!raw) return []
    const parsed = JSON.parse(raw) as RecallThread[]
    return parsed
      .filter((item) => item && typeof item.question === 'string' && item.question.trim())
      .map((item) => ({
        id: item.id || `recall-${item.question}`,
        question: item.question.trim(),
        mode: item.mode || 'auto',
        depth: item.depth || 'quick',
        spaceId: item.spaceId || 'all',
        contextCount: item.contextCount || 0,
        localFileCount: item.localFileCount || 0,
        answerPreview: item.answerPreview || '',
        thoughtSummary: item.thoughtSummary || '',
        updatedAt: item.updatedAt || new Date(0).toISOString(),
      }))
      .slice(0, 12)
  } catch {
    return []
  }
}

function recallHistoryToThread(item: RecallHistoryItem): RecallThread {
  return {
    id: item.thread_id || item.id,
    question: item.question,
    mode: item.mode || 'auto',
    depth: item.depth || 'quick',
    spaceId: item.space_id || 'all',
    contextCount: item.context_count,
    localFileCount: item.local_file_count,
    answerPreview: item.answer_preview,
    thoughtSummary: item.thought_summary,
    updatedAt: item.updated_at || item.created_at || new Date(0).toISOString(),
  }
}

function mergeRecallThreads(primary: RecallThread[], secondary: RecallThread[]) {
  const byKey = new Map<string, RecallThread>()
  for (const thread of [...primary, ...secondary]) {
    const key = thread.id || `${thread.spaceId || 'all'}::${thread.question.trim()}`
    const existing = byKey.get(key)
    if (thread.question.trim() && (!existing || new Date(thread.updatedAt).getTime() >= new Date(existing.updatedAt).getTime())) {
      byKey.set(key, thread)
    }
  }
  return Array.from(byKey.values())
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
    .slice(0, 12)
}

function mergeRecallHistoryItems(primary: RecallHistoryItem[], secondary: RecallHistoryItem[]) {
  const byKey = new Map<string, RecallHistoryItem>()
  for (const item of [...secondary, ...primary]) {
    const key = item.turn_id || item.id
    if (key) byKey.set(key, item)
  }
  return Array.from(byKey.values())
    .sort((a, b) => new Date(b.updated_at || b.created_at || 0).getTime() - new Date(a.updated_at || a.created_at || 0).getTime())
}

function persistRecallThreads(threads: RecallThread[]) {
  try {
    window.localStorage.setItem('snapgraph.recallThreads', JSON.stringify(threads))
  } catch {
    // Local history is a convenience, so storage failures should not block recall.
  }
}

async function streamRecall(question: string, turnId = currentRecallTurnId.value) {
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
      for (const part of parts) handleStreamEvent(part, turnId, (chunk) => {
        streamedText += chunk
        askResult.value = partialAskResponse(question, streamedText)
        updateRecallTurn(turnId, {
          result: askResult.value,
          focusGraph: focusGraph.value,
          currentThought: currentThought.value,
          localFiles: askResult.value.local_files || [],
        })
        void scrollRecallThreadToBottom()
      })
    }
    if (done) break
  }
}

function handleStreamEvent(raw: string, turnId: string, onChunk: (chunk: string) => void) {
  const eventLine = raw.split('\n').find((line) => line.startsWith('event:'))
  const dataLines = raw.split('\n').filter((line) => line.startsWith('data:'))
  if (!eventLine || !dataLines.length) return
  const event = eventLine.replace(/^event:\s*/, '').trim()
  const data = JSON.parse(dataLines.map((line) => line.replace(/^data:\s?/, '')).join('\n'))
  if (event === 'stage') {
    updateRecallStage(data as RecallStage)
  } else if (event === 'focus') {
    if (data.focus_graph) focusGraph.value = data.focus_graph as FocusGraph
    updateRecallTurn(turnId, {
      focusGraph: focusGraph.value,
      localFiles: focusGraph.value?.local_files || [],
    })
    void scrollRecallThreadToBottom()
  } else if (event === 'thought') {
    currentThought.value = data as RecallThought
    updateRecallTurn(turnId, { currentThought: currentThought.value })
    updateRecallStage({
      id: 'thought',
      label: '形成 Thought',
      status: currentThought.value.status === 'thinking' ? 'active' : 'done',
      detail: currentThought.value.status === 'thinking' ? '正在公开 solve trace' : '已完成公开 Thought',
    })
    void scrollRecallThreadToBottom()
  } else if (event === 'thought_delta') {
    appendThoughtDelta(data as { text?: string })
    updateRecallTurn(turnId, { currentThought: currentThought.value })
    updateRecallStage({ id: 'thought', label: '形成 Thought', status: 'active', detail: '正在公开 solve trace' })
    void scrollRecallThreadToBottom()
  } else if (event === 'chunk') {
    onChunk(String(data.text || ''))
  } else if (event === 'final') {
    askResult.value = data as AskResponse
    currentThought.value = askResult.value.thought || currentThought.value
    if (askResult.value.focus_graph) focusGraph.value = askResult.value.focus_graph
    updateRecallTurn(turnId, {
      result: askResult.value,
      focusGraph: focusGraph.value,
      currentThought: currentThought.value,
      localFiles: askResult.value.local_files || focusGraph.value?.local_files || [],
      answerPreview: compactRailText(stripMarkdown(askResult.value.text || ''), 180),
      busy: false,
    })
    updateRecallStage({ id: 'write', label: '生成 AI 回复', status: 'done', detail: '回答已完成' })
    void loadRecallHistory()
    void loadThoughtHistory()
    void loadWorkspace()
    void scrollRecallThreadToBottom()
  } else if (event === 'error') {
    throw new Error(String(data.message || 'Stream failed'))
  }
}

function appendThoughtDelta(delta: Partial<RecallThoughtTraceEvent> & { text?: string }) {
  const text = String(delta.text || '')
  if (!text) return
  const base: RecallThought = currentThought.value || {
    id: 'current-recall-thought',
    title: 'Thought',
    status: 'thinking',
    question: currentRecallQuestion.value,
    summary: '正在形成公开 Thought',
    lines: [],
    trace_events: [],
    stage_flow: ['Plan', 'Retrieve', 'Think', 'Verify', 'Finish'],
    evidence_titles: [],
    notice: '这是后端 solve 模式的公开推理轨迹；不展示模型私有草稿。',
  }
  const traceId = String(delta.trace_id || delta.phase || delta.label || `thought-${base.lines.length + 1}`)
  const traceEvent: RecallThoughtTraceEvent = {
    trace_id: traceId,
    phase: String(delta.phase || 'reasoning'),
    label: String(delta.label || 'THINK'),
    trace_role: String(delta.trace_role || 'thought'),
    call_kind: String(delta.call_kind || 'llm_reasoning'),
    trace_kind: 'llm_chunk',
    call_state: 'running',
    index: Number(delta.index || base.lines.length + 1),
    text,
  }
  const existingTraceEvents = base.trace_events || []
  const existingIndex = existingTraceEvents.findIndex((event) => event.trace_id === traceId)
  const nextTraceEvents =
    existingIndex >= 0
      ? existingTraceEvents.map((event, index) => (
          index === existingIndex
            ? {
                ...event,
                ...traceEvent,
                text: `${event.text || ''}${text}`,
              }
            : event
        ))
      : [...existingTraceEvents, traceEvent]
  currentThought.value = {
    ...base,
    status: 'thinking',
    trace_events: nextTraceEvents,
    lines: nextTraceEvents.map((event) => `${event.label}：${event.text}`),
  }
}

async function scrollRecallThreadToBottom(options: { force?: boolean } = {}) {
  await nextTick()
  window.requestAnimationFrame(() => {
    const thread = document.querySelector<HTMLElement>('.recall-thread')
    if (!thread) return
    if (!options.force && !recallThreadIsNearBottom(thread)) return
    thread.scrollTop = thread.scrollHeight
  })
}

function recallThreadIsNearBottom(thread: HTMLElement) {
  const distanceFromBottom = thread.scrollHeight - thread.scrollTop - thread.clientHeight
  return distanceFromBottom <= 96
}

async function scrollRecallThreadToTop() {
  await nextTick()
  window.requestAnimationFrame(() => {
    const thread = document.querySelector<HTMLElement>('.recall-thread')
    if (!thread) return
    thread.scrollTop = 0
  })
}

function partialAskResponse(question: string, text: string): AskResponse {
  return {
    question,
    text: `# 回答\n## 结论\n${text}`,
    contexts: focusGraph.value?.evidence_cards || [],
    graph_paths: [],
    focus_graph: focusGraph.value || emptyFocusGraph(),
    local_files: focusGraph.value?.local_files || [],
    thought: currentThought.value || undefined,
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
    mode: currentRecallMode.value || selectedRecallMode.value,
    depth: selectedRecallDepth.value,
    thread_id: currentRecallThreadId.value,
    turn_id: currentRecallTurnId.value,
    turn_index: currentRecallTurnIndex(),
    previous_turns: recallPreviousTurnsPayload(),
    ...(save === undefined ? {} : { save }),
    ...(contextSourceIds.length ? { context_source_ids: contextSourceIds } : {}),
  }
}

function currentRecallTurnIndex() {
  const currentTurn = recallTurns.value.find((turn) => turn.turnId === currentRecallTurnId.value)
  return currentTurn?.turnIndex || 0
}

function recallPreviousTurnsPayload() {
  return recallTurns.value
    .filter((turn) => turn.threadId === currentRecallThreadId.value && turn.turnId !== currentRecallTurnId.value)
    .slice(-6)
    .map((turn) => ({
      question: turn.question,
      answer_preview: turn.answerPreview || compactRailText(stripMarkdown(turn.result?.text || ''), 220),
      mode: turn.mode,
      depth: turn.depth,
    }))
}

function recallSpaceScope() {
  if (currentRecallSpaceId.value && currentRecallSpaceId.value !== 'all') {
    return currentRecallSpaceId.value
  }
  if (selectedSpaceId.value && selectedSpaceId.value !== 'all' && activeView.value === 'shelf') {
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
  updateRecallTurn(currentRecallTurnId.value, { stages: recallStages.value })
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

async function createSpace(payload: { name: string; description?: string; purpose?: string; color?: string }) {
  const name = payload.name.trim()
  if (!name) return
  busy.value = true
  try {
    const space = await api<GraphSpace>('/api/spaces', {
      method: 'POST',
      body: JSON.stringify({
        name,
        description: payload.description || '',
        purpose: payload.purpose || '',
        color: payload.color || '#5f7050',
      }),
    })
    await loadSpaces()
    selectedSpaceId.value = space.id
    await loadSpaceDetail(space.id)
    showToast(`已新建图谱空间：${graphSpaceDisplayName(space)}`)
  } catch (error) {
    showToast(messageFromError(error), 'error')
  } finally {
    busy.value = false
  }
}

async function openCollectedSpace(spaceId: string) {
  if (!spaceId) return
  activeView.value = 'shelf'
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

async function openSourceById(sourceId: string, target: 'raw' | 'source_page' = 'raw') {
  try {
    await api('/api/open-local', {
      method: 'POST',
      body: JSON.stringify({
        source_id: sourceId,
        target,
      }),
    })
    showToast('已打开本地文件。')
  } catch (error) {
    showToast(`打开本地文件失败：${messageFromError(error)}`, 'error')
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

function compactRailText(text: string, limit: number) {
  const cleaned = String(text || '').replace(/\s+/g, ' ').trim()
  if (!cleaned) return '本地材料'
  return cleaned.length <= limit ? cleaned : `${cleaned.slice(0, limit).trim()}…`
}

function stripMarkdown(text: string) {
  return String(text || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/\s+/g, ' ')
    .trim()
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
