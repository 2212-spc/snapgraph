<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">SG</div>
        <div>
          <strong>SnapGraph</strong>
          <span>Local cognitive spaces</span>
        </div>
      </div>

      <nav class="nav">
        <button
          v-for="page in pages"
          :key="page.id"
          :class="{ active: current === page.id }"
          @click="navigate(page.id)"
        >
          <component :is="page.icon" :size="18" />
          <span>{{ page.label }}</span>
        </button>
      </nav>

      <div class="space-switcher">
        <label>Current space</label>
        <select v-model="selectedSpaceId" @change="refreshSpaceData">
          <option value="all">All spaces</option>
          <option v-for="space in spaces" :key="space.id" :value="space.id">
            {{ space.name }}
          </option>
        </select>
      </div>

      <div class="runtime">
        <span :class="['dot', providerReady ? 'ready' : 'warn']"></span>
        <div>
          <strong>{{ config.provider || 'mock' }}</strong>
          <span>{{ providerReady ? 'ready' : 'needs key' }}</span>
        </div>
      </div>
    </aside>

    <main class="main">
      <div v-if="toast" class="toast">{{ toast }}</div>
      <div v-if="error" class="alert danger">{{ error }}</div>

      <section v-show="current === 'spaces'" class="screen">
        <header class="screen-head">
          <div>
            <p class="eyebrow">Spaces</p>
            <h1>把资料放进可审计的认知空间</h1>
          </div>
          <button class="btn primary" :disabled="loading" @click="startDemo">
            <Play :size="17" /> Demo data
          </button>
        </header>

        <div class="spaces-layout">
          <section class="space-grid">
            <article
              v-for="space in spaces"
              :key="space.id"
              :class="['space-card', { active: selectedSpaceId === space.id }]"
              @click="selectSpace(space.id)"
            >
              <div class="space-top">
                <span class="space-color" :style="{ background: space.color || '#315ea8' }"></span>
                <strong>{{ space.name }}</strong>
                <span v-if="space.pending_suggestions" class="badge ai">
                  {{ space.pending_suggestions }} suggestions
                </span>
              </div>
              <p>{{ space.purpose || space.description || 'A graph space for focused recall.' }}</p>
              <div class="metric-row">
                <div><span>User stated</span><strong>{{ spaceUserStatedRatio(space.id) }}</strong></div>
                <div><span>Open loops</span><strong>{{ spaceOpenLoopCount(space.id) }}</strong></div>
                <div><span>Suggestions</span><strong>{{ space.pending_suggestions }}</strong></div>
              </div>
            </article>
          </section>

          <section class="surface create-space">
            <div class="section-head">
              <h2>New space</h2>
              <Layers :size="18" />
            </div>
            <input v-model="newSpace.name" placeholder="产品洞察 / 论文 / 端侧 app" />
            <textarea v-model="newSpace.purpose" placeholder="这个空间希望帮我判断什么、推进什么？"></textarea>
            <input v-model="newSpace.description" placeholder="补充描述" />
            <div class="color-row">
              <button
                v-for="color in swatches"
                :key="color"
                :class="{ active: newSpace.color === color }"
                :style="{ background: color }"
                :title="color"
                @click="newSpace.color = color"
              ></button>
            </div>
            <button class="btn primary" :disabled="!newSpace.name || loading" @click="createSpace">
              <Plus :size="17" /> Create
            </button>
          </section>
        </div>
      </section>

      <section v-show="current === 'inbox'" class="screen">
        <header class="screen-head">
          <div>
            <p class="eyebrow">Capture</p>
            <h1>保存资料时，顺手保存它为什么重要</h1>
          </div>
          <button class="btn" @click="fileInput?.click()">
            <Upload :size="17" /> Capture
          </button>
        </header>

        <div class="inbox-layout">
          <section class="surface capture-panel">
            <input
              ref="fileInput"
              class="file-input"
              type="file"
              accept=".md,.markdown,.txt,.png,.jpg,.jpeg,.webp"
              @change="onFileSelected"
            />
            <div class="capture-drop" @click="fileInput?.click()">
              <Upload :size="24" />
              <strong>{{ ingestFile?.name || 'Choose markdown, text, or image' }}</strong>
              <span>PDF is still explicitly unsupported in Phase 8.</span>
            </div>
            <textarea v-model="ingestWhy" class="why-input" placeholder="为什么保存这个？用户明确理由会优先于 AI 推断。"></textarea>
            <div class="inline-controls">
              <select v-model="captureSpaceId">
                <option value="">Inbox</option>
                <option v-for="space in routableSpaces" :key="space.id" :value="space.id">
                  {{ space.name }}
                </option>
              </select>
              <button class="btn primary" :disabled="!ingestFile || loading" @click="doIngest">
                <Upload :size="17" /> Ingest
              </button>
            </div>
          </section>

          <section v-if="ingestReview" class="surface capture-review">
            <div class="section-head">
              <h2>Capture review</h2>
              <span :class="['badge', statusClass(ingestReview.status)]">{{ ingestReview.status }}</span>
            </div>
            <p class="review-title">{{ ingestReview.title }}</p>
            <div v-if="ingestReview.routing_suggestion" class="suggestion-band review">
              <Route :size="17" />
              <div>
                <strong>{{ ingestReview.routing_suggestion.payload.target_space_name }}</strong>
                <span>{{ ingestReview.routing_suggestion.reason }}</span>
              </div>
              <button class="icon-btn" title="Accept" @click="acceptSuggestion(ingestReview.routing_suggestion.id)">
                <Check :size="17" />
              </button>
              <button class="icon-btn" title="Reject" @click="rejectSuggestion(ingestReview.routing_suggestion.id)">
                <X :size="17" />
              </button>
            </div>
            <div class="mini-evidence">
              <article v-for="card in ingestReview.focus_graph?.evidence_cards || []" :key="card.source_id">
                <span>{{ card.why_saved_status }}</span>
                <strong>{{ card.why_saved }}</strong>
              </article>
            </div>
          </section>

          <section class="inbox-list">
            <article v-for="source in inboxSources" :key="source.id" class="source-card">
              <div class="source-head">
                <div>
                  <strong>{{ source.title }}</strong>
                  <span>{{ source.original_filename }} · {{ source.type }}</span>
                </div>
                <span :class="['badge', statusClass(source.why_saved_status)]">{{ source.why_saved_status }}</span>
              </div>
              <p>{{ source.why_saved || source.summary }}</p>
              <div v-if="suggestionForSource(source.id)" class="suggestion-band">
                <Route :size="17" />
                <div>
                  <strong>{{ suggestionForSource(source.id)?.payload.target_space_name }}</strong>
                  <span>{{ suggestionForSource(source.id)?.reason }}</span>
                </div>
                <button class="icon-btn" title="Accept" @click="acceptSuggestion(suggestionForSource(source.id)?.id)">
                  <Check :size="17" />
                </button>
                <button class="icon-btn" title="Reject" @click="rejectSuggestion(suggestionForSource(source.id)?.id)">
                  <X :size="17" />
                </button>
              </div>
            </article>
            <p v-if="!inboxSources.length" class="empty">Inbox is clear.</p>
          </section>
        </div>
      </section>

      <section v-show="current === 'graph'" class="screen graph-screen">
        <header class="screen-head">
          <div>
            <p class="eyebrow">Graph</p>
            <h1>拖动、缩放、确认关系</h1>
          </div>
          <div class="actions">
            <div class="segmented">
              <button :class="{ active: graphMode === 'focus' }" @click="setGraphMode('focus')">Focus Path</button>
              <button :class="{ active: graphMode === 'space' }" @click="setGraphMode('space')">Space Map</button>
              <button :class="{ active: graphMode === 'full' }" @click="setGraphMode('full')">Full Graph</button>
            </div>
            <button class="btn" @click="runGraphLayout">
              <RefreshCw :size="17" /> Layout
            </button>
            <button class="btn" @click="fitGraph">
              <Maximize2 :size="17" /> Fit
            </button>
          </div>
        </header>

        <div class="graph-workbench">
          <section class="graph-canvas-shell">
            <div class="graph-toolbar">
              <div class="graph-stats">
                <strong>{{ activeGraphNodes.length }}</strong><span>nodes</span>
                <strong>{{ activeGraphEdges.length }}</strong><span>edges</span>
              </div>
              <div class="graph-legend">
                <span class="legend source">source</span>
                <span class="legend thought">thought</span>
                <span class="legend project">project</span>
                <span class="legend proposed">proposed</span>
              </div>
            </div>
            <div ref="cyEl" class="cy-canvas"></div>
            <div v-if="!activeGraphNodes.length" class="graph-empty">
              <Network :size="28" />
              <strong>No graph nodes in this space yet.</strong>
            </div>
          </section>

          <aside class="surface inspector">
            <div class="section-head">
              <h2>Inspector</h2>
              <span v-if="selectedGraphItem" class="badge unknown">{{ selectedGraphItem.kind }}</span>
            </div>
            <template v-if="selectedGraphItem?.kind === 'node'">
              <h3>{{ selectedGraphItem.label }}</h3>
              <div class="detail-grid compact">
                <div><span>Type</span><strong>{{ selectedGraphItem.type }}</strong></div>
                <div><span>Status</span><strong>{{ selectedGraphItem.status }}</strong></div>
                <div><span>Space</span><strong>{{ selectedGraphItem.graph_space_id }}</strong></div>
                <div><span>Source</span><strong>{{ selectedGraphItem.properties?.source_id || 'none' }}</strong></div>
              </div>
              <div v-if="selectedGraphSource" class="source-preview">
                <span>Evidence summary</span>
                <strong>{{ selectedGraphSource.title }}</strong>
                <p>{{ selectedGraphSource.why_saved || selectedGraphSource.summary }}</p>
                <blockquote v-if="selectedGraphSource.open_loops?.length">
                  {{ selectedGraphSource.open_loops[0] }}
                </blockquote>
              </div>
              <button
                v-if="selectedGraphItem.properties?.source_id"
                class="btn"
                @click="loadSource(selectedGraphItem.properties.source_id)"
              >
                <FileText :size="17" /> Open source
              </button>
            </template>
            <template v-else-if="selectedGraphItem?.kind === 'edge'">
              <h3>{{ selectedGraphItem.relation }}</h3>
              <div class="detail-grid compact">
                <div><span>Status</span><strong>{{ selectedGraphItem.status }}</strong></div>
                <div><span>Confidence</span><strong>{{ Number(selectedGraphItem.confidence || 0).toFixed(2) }}</strong></div>
                <div><span>Source</span><strong>{{ selectedGraphItem.evidence_source_id || 'none' }}</strong></div>
                <div><span>Space</span><strong>{{ selectedGraphItem.graph_space_id }}</strong></div>
              </div>
              <p class="muted">AI-created relations stay proposed until a future confirm/reject workflow changes the fact layer.</p>
            </template>
            <template v-else>
              <p class="empty">Click a node or edge to inspect evidence and status.</p>
            </template>
          </aside>
        </div>
      </section>

      <section v-show="current === 'recall'" class="screen">
        <header class="screen-head">
          <div>
            <p class="eyebrow">Recall</p>
            <h1>找回一条想法背后的证据路径</h1>
          </div>
          <button class="btn" @click="loadFocusPreview">
            <Network :size="17" /> Preview path
          </button>
        </header>

        <section class="recall-hero">
          <div v-if="!providerReady" class="provider-warning">
            <Settings :size="18" />
            <div>
              <strong>LLM provider is configured but the key env is missing in this server process.</strong>
              <span>Graph, Spaces, Inbox, and Reports still work; real Recall needs SNAPGRAPH_LLM_API_KEY or mock mode.</span>
            </div>
          </div>
          <div class="ask-row">
            <select v-model="askSpaceId">
              <option value="all">All spaces</option>
              <option v-for="space in spaces" :key="space.id" :value="space.id">{{ space.name }}</option>
            </select>
            <input
              v-model="question"
              class="question-input"
              placeholder="这个项目为什么需要 AI 加 graph？"
              @keyup.enter="doAsk()"
            />
            <button class="btn primary" :disabled="!question || loading" @click="doAsk()">
              <Search :size="17" /> Ask
            </button>
          </div>
          <div class="prompt-grid">
            <button v-for="item in guidedQuestions" :key="item.question" @click="askPreset(item.question)">
              <span>{{ item.label }}</span>
              <strong>{{ item.question }}</strong>
            </button>
          </div>
        </section>

        <div class="focus-layout" ref="answerEl">
          <article class="surface answer-card focus-story">
            <div class="section-head">
              <h2>{{ answer ? 'Recovered answer' : 'Evidence preview' }}</h2>
              <span :class="['badge', focusConfidenceClass]">
                {{ activeFocusGraph?.confidence_summary.confidence_label || 'waiting' }}
              </span>
            </div>
            <div v-if="answer" class="md lead-answer" v-html="md2html(section(answer.text, '## Direct Answer'))"></div>
            <p v-else class="focus-empty-copy">
              Ask a question or preview the path. SnapGraph will show why the evidence mattered, where it came from, and what it asks you to do next.
            </p>
            <div class="diagnostic-strip">
              <div><span>Sources</span><strong>{{ activeFocusGraph?.confidence_summary.source_count || 0 }}</strong></div>
              <div><span>User stated</span><strong>{{ activeFocusGraph?.confidence_summary.user_stated || 0 }}</strong></div>
              <div><span>AI inferred</span><strong>{{ activeFocusGraph?.confidence_summary.ai_inferred || 0 }}</strong></div>
              <div><span>Next action</span><strong>{{ activeFocusGraph?.open_loops?.length || 0 }}</strong></div>
            </div>
            <div v-if="primaryOpenLoop" class="next-action">
              <span>Most useful next action</span>
              <strong>{{ primaryOpenLoop }}</strong>
            </div>
          </article>

          <article class="surface focus-map-panel">
            <div class="section-head">
              <h2>Focused path</h2>
              <button class="icon-btn" title="Open graph" @click="openAnswerGraph">
                <Network :size="18" />
              </button>
            </div>
            <div ref="focusCyEl" class="focus-cy"></div>
            <p v-if="!activeFocusGraph?.nodes.length" class="empty">No evidence path yet.</p>
            <div v-if="selectedGraphItem" class="focus-inspector-card">
              <span>{{ selectedGraphItem.kind === 'edge' ? 'relation' : selectedGraphItem.type }}</span>
              <strong>{{ selectedGraphItem.kind === 'edge' ? selectedGraphItem.relation : selectedGraphItem.label }}</strong>
              <p v-if="selectedGraphItem.kind === 'node' && selectedGraphSource">
                {{ selectedGraphSource.why_saved || selectedGraphSource.summary }}
              </p>
              <p v-else-if="selectedGraphItem.kind === 'edge'">
                {{ selectedGraphItem.status }} · confidence {{ Number(selectedGraphItem.confidence || 0).toFixed(2) }}
              </p>
            </div>
          </article>
        </div>

        <section v-if="focusEvidenceCards.length" class="evidence-story">
          <article v-for="chain in focusEvidenceCards" :key="chain.source_id" class="chain-card">
                <div class="chain-source">
                  <FileText :size="18" />
                  <strong>{{ chain.title }}</strong>
              <span :class="['badge', statusClass(chain.why_saved_status)]">{{ chain.space_name }}</span>
                </div>
            <p>{{ chain.why_saved }}</p>
            <blockquote v-if="chain.source_excerpt">{{ chain.source_excerpt }}</blockquote>
            <div v-if="chain.open_loops?.[0]" class="chain-line">{{ chain.open_loops[0] }}</div>
          </article>
        </section>

        <details v-if="answer" class="surface full-answer">
          <summary>Full markdown answer</summary>
          <div class="md" v-html="md2html(answer.text)"></div>
        </details>
      </section>

      <section v-show="current === 'reports'" class="screen">
        <header class="screen-head">
          <div>
            <p class="eyebrow">Reports</p>
            <h1>认知图谱健康报告</h1>
          </div>
          <button class="btn primary" :disabled="loading" @click="generateReport">
            <RefreshCw :size="17" /> Generate
          </button>
        </header>
        <div class="report-grid">
          <section class="surface status-surface">
            <div><span>Sources</span><strong>{{ ws.sources }}</strong></div>
            <div><span>Questions</span><strong>{{ ws.saved_questions }}</strong></div>
            <div><span>Nodes</span><strong>{{ ws.nodes }}</strong></div>
            <div><span>Lint</span><strong>{{ lint.status }}</strong></div>
          </section>
          <section class="surface md report-md" v-html="reportHtml || '<p>No report yet.</p>'"></section>
        </div>
      </section>

      <section v-show="current === 'settings'" class="screen narrow">
        <header class="screen-head">
          <div>
            <p class="eyebrow">Settings</p>
            <h1>运行时与边界</h1>
          </div>
        </header>
        <section class="surface settings-grid">
          <div><span>Provider</span><strong>{{ config.provider }}</strong></div>
          <div><span>Model</span><strong>{{ config.model || config.runtime?.model_used || 'mock' }}</strong></div>
          <div><span>API key env</span><strong>{{ config.api_key_env }}</strong></div>
          <div><span>Key state</span><strong>{{ config.has_api_key ? 'present' : 'missing' }}</strong></div>
          <div><span>Workspace</span><strong>{{ ws.workspace_path }}</strong></div>
          <div><span>Spaces</span><strong>{{ spaces.length }}</strong></div>
          <div><span>PDF</span><strong>unsupported</strong></div>
          <div><span>Images</span><strong>capture only</strong></div>
        </section>
        <section class="surface">
          <div class="config-row">
            <select v-model="draftConfig.provider">
              <option value="mock">mock</option>
              <option value="deepseek">deepseek</option>
              <option value="anthropic">anthropic</option>
            </select>
            <input v-model="draftConfig.model" placeholder="model" />
            <input v-model="draftConfig.api_key_env" placeholder="SNAPGRAPH_LLM_API_KEY" />
            <button class="btn" @click="saveConfig"><Save :size="17" /> Save</button>
          </div>
          <p v-if="!providerReady" class="warning-text">{{ config.provider_error || 'Provider key is missing.' }}</p>
        </section>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import cytoscape, { Core, ElementDefinition, EventObject } from 'cytoscape'
import {
  Check,
  FileText,
  Layers,
  Maximize2,
  Network,
  Play,
  Plus,
  RefreshCw,
  Route,
  Save,
  Search,
  Settings,
  Upload,
  X,
} from 'lucide-vue-next'

type PageId = 'recall' | 'inbox' | 'spaces' | 'graph' | 'reports' | 'settings'
type GraphMode = 'focus' | 'space' | 'full'

type ProviderMetadata = {
  configured_provider: string
  provider_used: string
  model_used: string
  api_key_env: string
  has_api_key: boolean
  provider_ready: boolean
  fallback_used: boolean
  provider_error: string
}

type Space = {
  id: string
  name: string
  description: string
  purpose: string
  color: string
  status: string
  source_count: number
  node_count: number
  edge_count: number
  pending_suggestions: number
}

type WorkspaceState = {
  sources: number
  saved_questions: number
  nodes: number
  edges: number
  lint_status: string
  workspace_path: string
  insights: Record<string, any>
  provider?: ProviderMetadata
}

type Source = {
  id: string
  title: string
  type: string
  summary: string
  why_saved: string
  why_saved_status: string
  related_project: string
  open_loops: string[]
  future_recall_questions: string[]
  confidence: number
  original_filename: string
  path: string
  graph_space_id: string
  space_name: string
  routing_status: string
  routing_reason: string
  source_excerpt?: string
}

type GraphNode = {
  id: string
  type: string
  label: string
  graph_space_id: string
  status: string
  properties?: Record<string, any>
}

type GraphEdge = {
  id: string
  source: string
  target: string
  relation: string
  evidence_source_id?: string
  confidence?: number
  graph_space_id: string
  status: string
}

type EvidenceCard = {
  source_id: string
  title: string
  space_id: string
  space_name: string
  why_saved: string
  why_saved_status: string
  related_project: string
  open_loops: string[]
  future_recall_questions: string[]
  source_excerpt: string
}

type FocusGraph = {
  center: { kind: string; label: string }
  space_id: string
  nodes: GraphNode[]
  edges: GraphEdge[]
  evidence_cards: EvidenceCard[]
  open_loops: string[]
  confidence_summary: {
    source_count: number
    user_stated: number
    ai_inferred: number
    confidence_label: string
  }
}

type Suggestion = {
  id: string
  graph_space_id: string
  kind: string
  payload: Record<string, any>
  reason: string
  confidence: number
  status: string
  created_at: string
}

type AskResponse = {
  question: string
  text: string
  provider: ProviderMetadata
  contexts: Source[]
  graph_paths: string[]
  diagnostics: Record<string, any>
  focus_graph: FocusGraph
  saved_page?: string
}

const pages = [
  { id: 'recall' as const, label: 'Recall', icon: Search },
  { id: 'inbox' as const, label: 'Capture', icon: Upload },
  { id: 'spaces' as const, label: 'Spaces', icon: Layers },
  { id: 'graph' as const, label: 'Graph', icon: Network },
  { id: 'reports' as const, label: 'Reports', icon: FileText },
  { id: 'settings' as const, label: 'Settings', icon: Settings },
]

const swatches = ['#315ea8', '#237162', '#98620b', '#8f4f76', '#4f5f6f']
const guidedQuestions = [
  { label: '价值判断', question: '这个项目为什么需要 AI 加 graph？' },
  { label: 'Open loop', question: '我现在最应该处理的 open loop 是什么？' },
  { label: 'LLM Wiki', question: '我为什么要从 LLM Wiki 开始？' },
]

const current = ref<PageId>('recall')
const selectedSpaceId = ref('default')
const askSpaceId = ref('all')
const captureSpaceId = ref('')
const graphMode = ref<GraphMode>('focus')
const loading = ref(false)
const toast = ref('')
const error = ref('')
const question = ref('这个项目为什么需要 AI 加 graph？')
const answer = ref<AskResponse | null>(null)
const answerEl = ref<HTMLElement | null>(null)
const cyEl = ref<HTMLElement | null>(null)
const cy = ref<Core | null>(null)
const focusCyEl = ref<HTMLElement | null>(null)
const focusCy = ref<Core | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const ingestFile = ref<File | null>(null)
const ingestWhy = ref('')
const ingestReview = ref<any>(null)
const reportHtml = ref('')
const selectedGraphItem = ref<any>(null)

const ws = reactive<WorkspaceState>({
  sources: 0,
  saved_questions: 0,
  nodes: 0,
  edges: 0,
  lint_status: '-',
  workspace_path: '',
  insights: {},
})
const config = reactive<any>({ provider: 'mock', runtime: {} })
const draftConfig = reactive({ provider: 'mock', model: '', api_key_env: 'SNAPGRAPH_LLM_API_KEY' })
const lint = reactive({ status: '-', errors: [] as string[], warnings: [] as string[] })
const graph = reactive<any>({ nodes: [] as GraphNode[], edges: [] as GraphEdge[], node_count: 0, edge_count: 0 })
const focusGraph = ref<FocusGraph | null>(null)
const spaces = ref<Space[]>([])
const sources = ref<Source[]>([])
const inboxSources = ref<Source[]>([])
const suggestions = ref<Suggestion[]>([])
const newSpace = reactive({ name: '', description: '', purpose: '', color: swatches[0] })

const providerReady = computed(() => Boolean(config.provider === 'mock' || config.has_api_key))
const routableSpaces = computed(() => spaces.value.filter((space) => space.id !== 'inbox'))
const selectedGraphSource = computed(() => {
  const sourceId = selectedGraphItem.value?.properties?.source_id || selectedGraphItem.value?.evidence_source_id
  if (!sourceId) return null
  return sources.value.find((source) => source.id === sourceId) || null
})
const activeFocusGraph = computed(() => answer.value?.focus_graph || focusGraph.value)
const focusEvidenceCards = computed(() => activeFocusGraph.value?.evidence_cards || [])
const primaryOpenLoop = computed(() => activeFocusGraph.value?.open_loops?.[0] || '')
const focusConfidenceClass = computed(() => {
  const label = activeFocusGraph.value?.confidence_summary.confidence_label
  if (label === 'strong') return 'user'
  if (label === 'mixed') return 'ai'
  return 'unknown'
})
const activeGraphNodes = computed(() => {
  if (graphMode.value === 'focus') return activeFocusGraph.value ? focusBubbleGraph(activeFocusGraph.value).nodes : []
  if (graphMode.value === 'space') return graph.nodes.filter((node: GraphNode) => ['project', 'source', 'task'].includes(node.type))
  return graph.nodes
})
const activeGraphEdges = computed(() => {
  if (graphMode.value === 'focus') return activeFocusGraph.value ? focusBubbleGraph(activeFocusGraph.value).edges : []
  const nodeIds = new Set(activeGraphNodes.value.map((node: GraphNode) => node.id))
  return graph.edges.filter((edge: GraphEdge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
})

function statusClass(status: string) {
  if (status === 'user-stated') return 'user'
  if (status === 'AI-inferred') return 'ai'
  if (status === 'proposed') return 'ai'
  return 'unknown'
}

async function api<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {}
  if (opts.body && !(opts.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const res = await fetch(url, { ...opts, headers: { ...headers, ...(opts.headers as any) } })
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}))
    const detail = payload.detail
    if (detail && typeof detail === 'object') {
      throw new Error(detail.provider_error || JSON.stringify(detail))
    }
    throw new Error(detail || res.statusText)
  }
  return res.json()
}

const get = <T,>(url: string) => api<T>(url)
const post = <T,>(url: string, body: any = {}) => api<T>(url, { method: 'POST', body: JSON.stringify(body) })

function notify(message: string) {
  toast.value = message
  setTimeout(() => (toast.value = ''), 2400)
}

function navigate(page: PageId) {
  current.value = page
  error.value = ''
  if (page === 'graph') nextTick(renderGraph)
  if (page === 'reports') loadReport()
}

function selectSpace(spaceId: string) {
  selectedSpaceId.value = spaceId
  askSpaceId.value = spaceId
  navigate('recall')
  refreshSpaceData()
  loadFocusPreview()
}

async function loadAll() {
  try {
    const [workspace, cfg, lintResult, spacePayload, sourceList, inboxList, suggestionPayload] = await Promise.all([
      get<WorkspaceState>('/api/workspace'),
      get<any>('/api/config'),
      get<any>('/api/lint'),
      get<{ spaces: Space[] }>('/api/spaces'),
      get<Source[]>('/api/sources?space_id=all'),
      get<Source[]>('/api/spaces/inbox/sources'),
      get<{ suggestions: Suggestion[] }>('/api/suggestions?status=pending'),
    ])
    Object.assign(ws, workspace)
    Object.assign(config, cfg)
    Object.assign(draftConfig, {
      provider: cfg.provider || 'mock',
      model: cfg.model || '',
      api_key_env: cfg.api_key_env || 'SNAPGRAPH_LLM_API_KEY',
    })
    Object.assign(lint, lintResult)
    spaces.value = spacePayload.spaces
    sources.value = sourceList
    inboxSources.value = inboxList
    suggestions.value = suggestionPayload.suggestions
    await refreshSpaceData()
    await loadFocusPreview()
  } catch (exc: any) {
    error.value = `加载失败：${exc.message}`
  }
}

async function refreshSpaceData() {
  try {
    const graphData = await get<any>(
      selectedSpaceId.value === 'all' ? '/api/graph?space_id=all' : `/api/spaces/${selectedSpaceId.value}/graph`,
    )
    Object.assign(graph, graphData)
    await nextTick()
    renderGraph()
  } catch (exc: any) {
    error.value = `图谱加载失败：${exc.message}`
  }
}

async function startDemo() {
  loading.value = true
  error.value = ''
  try {
    await post('/api/demo/load', {})
    selectedSpaceId.value = 'default'
    askSpaceId.value = 'default'
    await loadAll()
    notify('Demo data loaded')
  } catch (exc: any) {
    error.value = `演示失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

async function createSpace() {
  loading.value = true
  try {
    const created = await post<Space>('/api/spaces', newSpace)
    Object.assign(newSpace, { name: '', description: '', purpose: '', color: swatches[0] })
    selectedSpaceId.value = created.id
    askSpaceId.value = created.id
    await loadAll()
    notify('Space created')
  } catch (exc: any) {
    error.value = `创建失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  ingestFile.value = input.files?.[0] || null
}

async function doIngest() {
  if (!ingestFile.value) return
  loading.value = true
  error.value = ''
  try {
    const fd = new FormData()
    fd.append('file', ingestFile.value)
    fd.append('why', ingestWhy.value)
    fd.append('space_id', captureSpaceId.value)
    ingestReview.value = await api('/api/ingest', { method: 'POST', body: fd })
    focusGraph.value = ingestReview.value.focus_graph
    ingestFile.value = null
    ingestWhy.value = ''
    captureSpaceId.value = ''
    if (fileInput.value) fileInput.value.value = ''
    await loadAll()
    await nextTick()
    renderFocusGraph()
    notify('Captured')
  } catch (exc: any) {
    error.value = `摄入失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

function suggestionForSource(sourceId: string) {
  return suggestions.value.find((suggestion) => suggestion.payload?.source_id === sourceId && suggestion.status === 'pending')
}

async function acceptSuggestion(id?: string) {
  if (!id) return
  await post(`/api/suggestions/${id}/accept`)
  await loadAll()
  notify('Suggestion accepted')
}

async function rejectSuggestion(id?: string) {
  if (!id) return
  await post(`/api/suggestions/${id}/reject`)
  await loadAll()
  notify('Suggestion rejected')
}

async function askPreset(value: string) {
  question.value = value
  await doAsk()
}

async function doAsk() {
  if (!question.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    answer.value = await post<AskResponse>('/api/ask', {
      question: question.value.trim(),
      save: false,
      space_id: askSpaceId.value,
    })
    focusGraph.value = answer.value.focus_graph
    await nextTick()
    renderFocusGraph()
    answerEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (exc: any) {
    error.value = `恢复失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

async function loadFocusPreview() {
  if (!question.value.trim()) return
  try {
    focusGraph.value = await post<FocusGraph>('/api/focus', {
      question: question.value.trim(),
      space_id: askSpaceId.value,
    })
    await nextTick()
    renderFocusGraph()
  } catch (exc: any) {
    error.value = `路径预览失败：${exc.message}`
  }
}

function setGraphMode(mode: GraphMode) {
  graphMode.value = mode
  nextTick(renderGraph)
}

function spaceSources(spaceId: string) {
  return sources.value.filter((source) => source.graph_space_id === spaceId)
}

function spaceUserStatedRatio(spaceId: string) {
  const list = spaceSources(spaceId)
  if (!list.length) return '0%'
  const count = list.filter((source) => source.why_saved_status === 'user-stated').length
  return `${Math.round((count / list.length) * 100)}%`
}

function spaceOpenLoopCount(spaceId: string) {
  return spaceSources(spaceId).reduce(
    (count, source) => count + source.open_loops.filter((loop) => loop && loop !== 'None').length,
    0,
  )
}

function openAnswerGraph() {
  const first = answer.value?.contexts?.[0]
  if (first?.graph_space_id) selectedSpaceId.value = first.graph_space_id
  navigate('graph')
  refreshSpaceData()
}

async function loadSource(id: string) {
  const source = sources.value.find((item) => item.id === id)
  if (source?.graph_space_id) {
    selectedSpaceId.value = source.graph_space_id
    await refreshSpaceData()
  }
}

async function generateReport() {
  loading.value = true
  try {
    const result = await post<any>('/api/report/generate')
    reportHtml.value = md2html(result.markdown)
    await loadAll()
    notify('Report generated')
  } catch (exc: any) {
    error.value = `报告失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

async function loadReport() {
  try {
    const result = await get<any>('/api/report')
    reportHtml.value = md2html(result.markdown)
  } catch {
    reportHtml.value = ''
  }
}

async function saveConfig() {
  try {
    const result = await api<any>('/api/config', {
      method: 'PUT',
      body: JSON.stringify(draftConfig),
    })
    Object.assign(config, result.runtime, draftConfig)
    await loadAll()
    notify('Config saved')
  } catch (exc: any) {
    error.value = `配置失败：${exc.message}`
  }
}

function renderGraph() {
  if (!cyEl.value || current.value !== 'graph') return
  const elements = graphMode.value === 'focus'
    ? focusElements(activeFocusGraph.value, cyEl.value)
    : graphElements(activeGraphNodes.value, activeGraphEdges.value)
  const layout = graphMode.value === 'focus' ? focusLayoutOptions() : graphLayoutOptions()

  if (!cy.value) {
    cy.value = cytoscape({
      container: cyEl.value,
      elements,
      minZoom: 0.25,
      maxZoom: 2.4,
      wheelSensitivity: 0.22,
      style: graphStyle(),
      layout,
    })
    cy.value.on('tap', 'node', (event: EventObject) => selectGraphNode(event.target))
    cy.value.on('tap', 'edge', (event: EventObject) => selectGraphEdge(event.target))
    cy.value.on('mouseover', 'node, edge', (event: EventObject) => previewGraphPath(cy.value, event.target))
    cy.value.on('mouseout', 'node, edge', () => clearGraphPreview(cy.value))
    cy.value.on('tap', (event: EventObject) => {
      if (event.target === cy.value) {
        selectedGraphItem.value = null
        cy.value?.elements().removeClass('dim highlight')
      }
    })
  } else {
    cy.value.elements().remove()
    cy.value.add(elements)
    runGraphLayout()
  }
}

function renderFocusGraph() {
  if (!focusCyEl.value || current.value !== 'recall') return
  const focus = activeFocusGraph.value
  const elements = focusElements(focus, focusCyEl.value)
  const layout = focusLayoutOptions()

  if (!focusCy.value) {
    focusCy.value = cytoscape({
      container: focusCyEl.value,
      elements,
      minZoom: 0.35,
      maxZoom: 2.2,
      wheelSensitivity: 0.18,
      style: graphStyle(),
      layout,
    })
    focusCy.value.on('tap', 'node', (event: EventObject) => selectFocusNode(event.target))
    focusCy.value.on('tap', 'edge', (event: EventObject) => selectFocusEdge(event.target))
    focusCy.value.on('mouseover', 'node, edge', (event: EventObject) => previewGraphPath(focusCy.value, event.target))
    focusCy.value.on('mouseout', 'node, edge', () => clearGraphPreview(focusCy.value))
    focusCy.value.on('tap', (event: EventObject) => {
      if (event.target === focusCy.value) {
        selectedGraphItem.value = null
        focusCy.value?.elements().removeClass('dim highlight')
      }
    })
  } else {
    focusCy.value.elements().remove()
    focusCy.value.add(elements)
    focusCy.value.layout(layout).run()
  }
}

function selectFocusNode(node: any) {
  selectedGraphItem.value = {
    kind: 'node',
    id: node.id(),
    label: node.data('fullLabel') || node.data('label'),
    type: node.data('type'),
    status: node.data('status'),
    graph_space_id: node.data('graph_space_id'),
    properties: node.data('properties'),
  }
  highlightGraphPath(focusCy.value, node)
}

function selectFocusEdge(edge: any) {
  selectedGraphItem.value = {
    kind: 'edge',
    id: edge.id(),
    relation: edge.data('relation'),
    status: edge.data('status'),
    confidence: edge.data('confidence'),
    evidence_source_id: edge.data('evidence_source_id'),
    graph_space_id: edge.data('graph_space_id'),
  }
  highlightGraphPath(focusCy.value, edge)
}

function selectGraphNode(node: any) {
  selectedGraphItem.value = {
    kind: 'node',
    id: node.id(),
    label: node.data('fullLabel') || node.data('label'),
    type: node.data('type'),
    status: node.data('status'),
    graph_space_id: node.data('graph_space_id'),
    properties: node.data('properties'),
  }
  highlightGraphPath(cy.value, node)
}

function selectGraphEdge(edge: any) {
  selectedGraphItem.value = {
    kind: 'edge',
    id: edge.id(),
    relation: edge.data('relation'),
    status: edge.data('status'),
    confidence: edge.data('confidence'),
    evidence_source_id: edge.data('evidence_source_id'),
    graph_space_id: edge.data('graph_space_id'),
  }
  highlightGraphPath(cy.value, edge)
}

function runGraphLayout() {
  cy.value?.layout(graphMode.value === 'focus' ? focusLayoutOptions() : graphLayoutOptions()).run()
}

function fitGraph() {
  cy.value?.fit(undefined, 56)
}

function graphElements(nodes: GraphNode[], edges: GraphEdge[], positions?: Map<string, { x: number; y: number }>): ElementDefinition[] {
  return [
    ...nodes.map((node: GraphNode) => ({
      data: {
        id: node.id,
        label: graphNodeLabel(node),
        glyph: graphNodeGlyph(node),
        fullLabel: node.label,
        type: node.type,
        status: node.status || 'confirmed',
        graph_space_id: node.graph_space_id,
        properties: node.properties || {},
      },
      position: positions?.get(node.id),
      classes: `${node.type} ${node.status || 'confirmed'}`,
    })),
    ...edges.map((edge: GraphEdge) => ({
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.relation,
        relation: edge.relation,
        confidence: edge.confidence,
        evidence_source_id: edge.evidence_source_id,
        graph_space_id: edge.graph_space_id,
        status: edge.status || 'confirmed',
      },
      classes: `${edge.relation} ${edge.status || 'confirmed'}`,
    })),
  ]
}

function focusElements(focus: FocusGraph | null | undefined, _container?: HTMLElement | null): ElementDefinition[] {
  if (!focus?.nodes.length) return []
  const { nodes, edges } = focusBubbleGraph(focus)
  return graphElements(nodes, edges)
}

function focusBubbleGraph(focus: FocusGraph) {
  const sourceNodes = focus.nodes.filter((node) => node.type === 'source').slice(0, 6)
  const sourceIds = sourceNodes.map((node) => String(node.properties?.source_id || '').trim()).filter(Boolean)
  const sourceIdSet = new Set(sourceIds)
  const thoughtNodes = focus.nodes
    .filter((node) => node.type === 'thought' && sourceIdSet.has(String(node.properties?.source_id || '')))
    .slice(0, 6)
  const projectNodes = uniqueValues(
    focus.evidence_cards
      .filter((card) => sourceIdSet.has(card.source_id))
      .map((card) => card.related_project)
      .filter(Boolean),
  )
    .slice(0, 2)
    .map((label, index) => syntheticFocusNode(`focus-project-${index}`, 'project', label, focus.space_id))
  const loopNodes = uniqueValues(focus.open_loops.filter(Boolean))
    .slice(0, 2)
    .map((label, index) => syntheticFocusNode(`focus-loop-${index}`, 'task', label.replace(/^Open loop:\s*/i, ''), focus.space_id))
  const nodes = [...sourceNodes, ...thoughtNodes, ...projectNodes, ...loopNodes]
  const nodeIds = new Set(nodes.map((node) => node.id))
  const edges = focus.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))

  const linkedProjects = new Set<string>()
  const linkedLoops = new Set<string>()
  sourceNodes.forEach((sourceNode, index) => {
    const sourceId = String(sourceNode.properties?.source_id || '')
    const thoughtNode = thoughtNodes.find((node) => node.properties?.source_id === sourceId)
    const anchorId = thoughtNode?.id || sourceNode.id
    const projectNode = projectNodes.find((node) => !linkedProjects.has(node.id))
    const loopNode = loopNodes.find((node) => !linkedLoops.has(node.id))
    if (projectNode && linkedProjects.size < 3) {
      linkedProjects.add(projectNode.id)
      edges.push(syntheticFocusEdge(`focus-project-edge-${index}`, anchorId, projectNode.id, 'evidence_for', focus.space_id, sourceId))
    }
    if (loopNode && linkedLoops.size < 2) {
      linkedLoops.add(loopNode.id)
      edges.push(syntheticFocusEdge(`focus-loop-edge-${index}`, anchorId, loopNode.id, 'follow_up', focus.space_id, sourceId))
    }
  })

  return { nodes, edges }
}

function syntheticFocusNode(id: string, type: string, label: string, graphSpaceId: string): GraphNode {
  return {
    id,
    type,
    label,
    graph_space_id: graphSpaceId,
    status: 'confirmed',
    properties: { synthetic: true },
  }
}

function syntheticFocusEdge(
  id: string,
  source: string,
  target: string,
  relation: string,
  graphSpaceId: string,
  evidenceSourceId?: string,
): GraphEdge {
  return {
    id,
    source,
    target,
    relation,
    evidence_source_id: evidenceSourceId,
    confidence: 0.82,
    graph_space_id: graphSpaceId,
    status: 'confirmed',
  }
}

function uniqueValues(values: string[]) {
  return [...new Set(values.map((value) => value.trim()).filter((value) => value && value !== 'None'))]
}

function focusLayoutOptions() {
  return {
    name: 'cose',
    animate: true,
    animationDuration: 700,
    animationEasing: 'ease-out-cubic',
    fit: true,
    padding: 44,
    nodeRepulsion: 4200,
    nodeOverlap: 18,
    idealEdgeLength: 70,
    edgeElasticity: 120,
    nestingFactor: 1.2,
    gravity: 0.22,
    numIter: 700,
  }
}

function graphLayoutOptions() {
  if (graphMode.value === 'space') {
    return { name: 'concentric', animate: true, animationDuration: 560, fit: true, padding: 60, minNodeSpacing: 48 }
  }
  return {
    name: 'cose',
    animate: true,
    animationDuration: 560,
    animationEasing: 'ease-out-cubic',
    fit: true,
    padding: 58,
    nodeRepulsion: 6200,
    idealEdgeLength: 122,
    gravity: 0.18,
  }
}

function highlightGraphPath(instance: Core | null, target: any) {
  if (!instance) return
  instance.elements().removeClass('dim highlight')
  const path = target.isNode?.() ? target.closedNeighborhood() : target.connectedNodes().union(target)
  instance.elements().not(path).addClass('dim')
  path.addClass('highlight')
}

function previewGraphPath(instance: Core | null, target: any) {
  if (!instance || selectedGraphItem.value) return
  highlightGraphPath(instance, target)
}

function clearGraphPreview(instance: Core | null) {
  if (!instance || selectedGraphItem.value) return
  instance.elements().removeClass('dim highlight')
}

function graphStyle() {
  return [
    {
      selector: 'node',
      style: {
        label: 'data(glyph)',
        'font-family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
        'font-size': 12,
        'font-weight': 850,
        color: '#ffffff',
        'text-valign': 'center',
        'text-halign': 'center',
        'text-margin-y': 0,
        'text-outline-width': 0,
        shape: 'ellipse',
        width: 44,
        height: 44,
        'background-color': '#64748b',
        'border-color': '#ffffff',
        'border-width': 2,
        'shadow-blur': 12,
        'shadow-color': '#475569',
        'shadow-opacity': 0.2,
        'shadow-offset-x': 0,
        'shadow-offset-y': 3,
        'transition-property': 'opacity, width, height, border-width, background-color, line-color',
        'transition-duration': '140ms',
      },
    },
    { selector: 'node.source', style: { width: 50, height: 50, 'background-color': '#2563eb', 'shadow-color': '#2563eb' } },
    { selector: 'node.thought', style: { width: 44, height: 44, 'background-color': '#0f766e', 'shadow-color': '#0f766e' } },
    { selector: 'node.project', style: { width: 56, height: 56, 'background-color': '#b7791f', 'shadow-color': '#b7791f' } },
    { selector: 'node.task', style: { width: 46, height: 46, 'background-color': '#be3455', 'shadow-color': '#be3455' } },
    { selector: 'node.question', style: { width: 34, height: 34, 'background-color': '#7c3aed', 'shadow-color': '#7c3aed' } },
    { selector: 'node.proposed', style: { 'border-style': 'dashed', opacity: 0.72 } },
    {
      selector: 'node.highlight',
      style: {
        label: 'data(label)',
        color: '#111827',
        'font-size': 10,
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 8,
        'text-wrap': 'wrap',
        'text-max-width': 92,
        'text-background-color': '#ffffff',
        'text-background-opacity': 0.94,
        'text-background-padding': 3,
        'text-background-shape': 'roundrectangle',
      },
    },
    { selector: 'node:grabbed', style: { 'border-width': 4, 'shadow-blur': 28, 'shadow-opacity': 0.42 } },
    {
      selector: 'edge',
      style: {
        width: 1.15,
        'curve-style': 'haystack',
        'target-arrow-shape': 'none',
        'line-color': '#94a3b8',
        'target-arrow-color': '#94a3b8',
        opacity: 0.58,
        label: '',
        'font-size': 9,
        color: '#475569',
        'text-background-color': '#ffffff',
        'text-background-opacity': 0.85,
        'text-background-padding': 2,
        'transition-property': 'opacity, width, line-color',
        'transition-duration': '140ms',
      },
    },
    { selector: 'edge.triggered_thought', style: { 'line-color': '#0f766e' } },
    { selector: 'edge.evidence_for', style: { 'line-color': '#2563eb' } },
    { selector: 'edge.follow_up', style: { 'line-color': '#be3455' } },
    { selector: 'edge.proposed', style: { 'line-style': 'dashed', opacity: 0.76 } },
    { selector: '.dim', style: { opacity: 0.22 } },
    { selector: 'node.highlight', style: { opacity: 1, 'border-width': 4, 'shadow-opacity': 0.45, 'shadow-blur': 26 } },
    { selector: 'edge.highlight', style: { opacity: 1, width: 2.8, 'line-color': '#111827' } },
  ]
}

function shortLabel(label: string, max = 28) {
  if (!label) return ''
  return label.length > max ? `${label.slice(0, max - 1)}...` : label
}

function graphNodeLabel(node: GraphNode) {
  if (node.type === 'thought') return 'reason'
  if (node.type === 'task') return 'loop'
  if (node.type === 'question') return ''
  return shortLabel(node.label, node.type === 'project' ? 14 : 12)
}

function graphNodeGlyph(node: GraphNode) {
  if (node.type === 'source') return 'S'
  if (node.type === 'thought') return 'R'
  if (node.type === 'project') return 'P'
  if (node.type === 'task') return 'L'
  if (node.type === 'question') return '?'
  return '•'
}

function section(text: string, heading: string) {
  if (!text || !text.includes(heading)) return text || ''
  const tail = text.slice(text.indexOf(heading) + heading.length).trim()
  const next = tail.search(/\n## /)
  return (next >= 0 ? tail.slice(0, next) : tail).trim()
}

function md2html(text: string) {
  if (!text) return ''
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, _lang, code) => `<pre><code>${code.trim()}</code></pre>`)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
  html = html.replace(/^[ \t]*- (.+)$/gm, '<li>$1</li>').replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
  return html
    .split(/\n\n+/)
    .map((part) => {
      const p = part.trim()
      if (!p) return ''
      if (/^<(h[1-3]|ul|pre)/.test(p)) return p
      return `<p>${p.replace(/\n/g, '<br>')}</p>`
    })
    .join('\n')
}

watch(selectedSpaceId, refreshSpaceData)
watch(graphMode, () => nextTick(renderGraph))
watch(current, (page) => {
  if (page === 'graph') nextTick(renderGraph)
  if (page === 'recall') nextTick(renderFocusGraph)
})

onMounted(loadAll)
onBeforeUnmount(() => {
  cy.value?.destroy()
  focusCy.value?.destroy()
})
</script>
