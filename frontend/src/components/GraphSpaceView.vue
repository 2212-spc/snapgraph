<template>
  <section class="space-detail graph-space-detail" v-if="space">
    <header class="space-detail-head">
      <div>
        <p class="eyebrow">{{ surfaceMode === 'overview' ? '图谱概览' : '图谱操作台' }}</p>
        <h2>{{ space.name }}</h2>
        <p>{{ spaceDescription }}</p>
      </div>
      <div class="space-detail-topbar">
        <div class="space-stats graph-space-stats">
          <span class="graph-stat-chip">{{ space.source_count }} 材料</span>
          <span class="graph-stat-chip">{{ space.node_count }} 节点</span>
          <span class="graph-stat-chip">{{ space.edge_count }} 边</span>
          <span v-if="overviewOpenCount" class="graph-stat-chip">
            {{ overviewOpenCount }} {{ overviewOpenLabel }}
          </span>
        </div>

        <div class="graph-mode-switch" role="tablist" aria-label="图谱模式切换">
          <button
            :class="{ active: surfaceMode === 'overview' }"
            role="tab"
            :aria-selected="surfaceMode === 'overview'"
            @click="surfaceMode = 'overview'"
          >
            概览
          </button>
          <button
            :class="{ active: surfaceMode === 'workbench' }"
            role="tab"
            :aria-selected="surfaceMode === 'workbench'"
            @click="surfaceMode = 'workbench'"
          >
            专业模式
          </button>
        </div>
      </div>
    </header>

    <section v-if="surfaceMode === 'overview'" class="graph-overview-mode">
      <div class="graph-overview-actions">
        <button class="primary-button" @click="askFromSpace">找回这个空间里的判断</button>
        <button class="paper-button" @click="openActionWorkbench">整理开放问题</button>
        <button class="ghost-button" @click="surfaceMode = 'workbench'">进入专业模式</button>
      </div>

      <div class="graph-overview-grid">
        <article class="space-panel graph-summary-card">
          <div class="section-head compact">
            <p class="section-kicker">空间摘要</p>
            <h3>这个空间正在追踪什么</h3>
          </div>
          <p>{{ overviewSummary }}</p>
          <div v-if="overviewProjects.length" class="graph-project-row">
            <span v-for="project in overviewProjects" :key="project.project" class="graph-stat-chip">
              {{ project.project }} · {{ project.source_count }} 条材料
            </span>
          </div>
        </article>

        <article class="space-panel graph-summary-card">
          <div class="section-head compact">
            <p class="section-kicker">最近材料</p>
            <h3>最近材料</h3>
          </div>
          <div v-if="overviewRecentSources.length" class="graph-overview-list">
            <article
              v-for="source in overviewRecentSources"
              :key="source.id"
              class="graph-recent-source-card"
            >
              <div class="graph-card-row">
                <strong>{{ source.title }}</strong>
                <span class="evidence-badge" :class="sourceToneClass(source)">
                  {{ sourceBadgeLabel(source) }}
                </span>
              </div>
              <p>{{ sourcePreview(source) }}</p>
            </article>
          </div>
          <p v-else class="subtle-empty-state">还没有最近材料。继续收集后，这里会先出现新的线索。</p>
        </article>

        <article class="space-panel graph-summary-card">
          <div class="section-head compact">
            <p class="section-kicker">关键节点</p>
            <h3>关键节点</h3>
          </div>
          <div v-if="overviewKeyNodes.length" class="graph-overview-list">
            <article
              v-for="node in overviewKeyNodes"
              :key="node.id"
              class="graph-key-node-card"
            >
              <div class="graph-card-row">
                <strong>{{ node.label }}</strong>
                <span class="evidence-badge" :class="nodeToneClass(node)">
                  {{ nodeTypeLabel(node.type) }}
                </span>
              </div>
              <p>{{ keyNodeSummary(node) }}</p>
            </article>
          </div>
          <p v-else class="subtle-empty-state">
            还没有足够节点。继续收集材料后，SnapGraph 会逐步形成结构。
          </p>
        </article>

        <article class="space-panel graph-summary-card">
          <div class="section-head compact">
            <p class="section-kicker">开放问题 / 下一步</p>
            <h3>开放问题 / 下一步</h3>
          </div>
          <div v-if="overviewOpenItems.length" class="graph-overview-list">
            <article
              v-for="item in overviewOpenItems"
              :key="item.key"
              class="open-loop-card"
            >
              <div class="graph-card-row">
                <strong>{{ item.title }}</strong>
                <span v-if="item.badge" class="evidence-badge" :class="item.tone">
                  {{ item.badge }}
                </span>
              </div>
              <p>{{ item.detail }}</p>
            </article>
          </div>
          <p v-else class="subtle-empty-state">
            暂时没有明确开放问题。你可以继续收集材料，或进入专业模式整理连接。
          </p>
        </article>
      </div>
    </section>

    <section v-else class="graph-workbench">
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

      <div class="graph-toolbar" aria-label="Graph workspace controls">
        <div class="graph-toolbar-group">
          <span>视图</span>
          <div class="graph-toolbar-buttons">
            <button
              v-for="mode in viewModes"
              :key="mode.id"
              :class="{ active: viewMode === mode.id }"
              @click="viewMode = mode.id"
            >
              <component :is="mode.icon" :size="15" />
              {{ mode.label }}
            </button>
          </div>
          <p class="graph-view-caption">{{ modeDescription }}</p>
        </div>
        <div class="graph-toolbar-group">
          <span>操作</span>
          <div class="graph-toolbar-buttons">
            <button
              v-for="mode in interactionModes"
              :key="mode.id"
              :class="{ active: interactionMode === mode.id }"
              @click="setInteractionMode(mode.id)"
            >
              <component :is="mode.icon" :size="15" />
              {{ mode.label }}
            </button>
          </div>
        </div>
      </div>

      <div class="workbench-grid">
        <aside class="space-panel graph-left-panel">
          <span>材料</span>
          <input v-model="sourceFilter" placeholder="筛选材料" />
          <div class="source-scroll">
            <button
              v-for="source in visibleSources"
              :key="source.id"
              class="source-row"
              :class="{ selected: selectedSource?.id === source.id }"
              @click="selectSource(source)"
            >
              <strong>{{ source.title }}</strong>
              <small>{{ source.why_saved_status === 'user-stated' ? '用户原话' : 'AI 推断' }}</small>
            </button>
            <p v-if="!visibleSources.length">这个图谱还没有可显示的材料。</p>
          </div>

          <section v-if="themes.length" class="theme-list">
            <span>主题分组</span>
            <button
              v-for="theme in themes"
              :key="theme.id"
              :class="{ selected: selectedThemeId === theme.id }"
              @click="selectTheme(theme.id)"
            >
              <strong>{{ theme.label }}</strong>
              <small>{{ theme.origin }} · {{ theme.status }}</small>
            </button>
          </section>

          <section v-if="suggestions.length" class="route-suggestions">
            <span>AI 路由建议</span>
            <article v-for="suggestion in suggestions" :key="suggestion.id">
              <small>{{ Math.round(suggestion.confidence * 100) }}%</small>
              <p>{{ suggestion.reason }}</p>
              <button class="paper-button" :disabled="busy" @click="$emit('acceptSuggestion', suggestion.id)">接受</button>
              <button class="ghost-button" :disabled="busy" @click="$emit('rejectSuggestion', suggestion.id)">忽略</button>
            </article>
          </section>
        </aside>

        <article class="space-panel graph-canvas-panel" :class="{ 'is-expanded': graphExpanded }">
          <div class="canvas-head">
            <div>
              <span>{{ currentViewLabel }}</span>
              <p>{{ modeDescription }}</p>
            </div>
            <div class="canvas-actions">
              <button class="paper-button" :disabled="!visibleGraphNodes.length" @click="toggleGraphExpanded">
                <component :is="graphExpanded ? Minimize2 : Maximize2" :size="15" />
                {{ graphExpanded ? '退出放大' : '放大图谱' }}
              </button>
              <button class="paper-button" :disabled="!visibleGraphNodes.length" @click="resetAutoLayout">
                重新排布
              </button>
              <button class="paper-button" :disabled="!graph.nodes.length || savingLayout" @click="saveCurrentLayout">
                保存布局
              </button>
            </div>
          </div>

          <div
            v-if="visibleGraphNodes.length"
            ref="stageContainer"
            class="graph-stage"
            @dblclick="toggleGraphExpanded"
            @pointerdown="startGraphPan"
            @wheel.prevent="zoomGraph"
          >
            <div class="graph-map-layer" :style="graphTransformStyle">
              <svg class="graph-stage-edges" viewBox="0 0 1000 680" preserveAspectRatio="none" aria-hidden="true">
                <defs>
                  <marker id="paper-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" />
                  </marker>
                </defs>
                <g>
                  <g
                    v-for="edge in visibleGraphEdges"
                    :key="edge.id"
                    class="graph-edge-hit"
                    :aria-label="`${labelFor(edge.source)} ${edge.relation} ${labelFor(edge.target)}`"
                    @click="selectGraphEdge(edge.id)"
                  >
                    <path :d="edgePath(edge)" class="paper-edge-touch" />
                    <path
                      :d="edgePath(edge)"
                      class="paper-edge"
                      :class="edgeClasses(edge)"
                      marker-end="url(#paper-arrow)"
                    />
                  </g>
                  <text
                    v-for="edge in labeledGraphEdges"
                    :key="`label-${edge.id}`"
                    class="paper-edge-label"
                    :x="edgeMidpoint(edge).x"
                    :y="edgeMidpoint(edge).y"
                  >
                    {{ edge.relation }}
                  </text>
                </g>
              </svg>
              <button
                v-for="node in visibleGraphNodes"
                :key="node.id"
                class="paper-graph-node"
                :class="[
                  `node-${node.type}`,
                  `status-${node.status || 'confirmed'}`,
                  { selected: selectedNodeIds.includes(node.id) },
                ]"
                :style="nodePositionStyle(node.id)"
                :title="node.label"
                :aria-label="`${nodeTypeLabel(node.type)}：${node.label}`"
                @click.stop="selectGraphNode(node.id, $event.shiftKey)"
                @dblclick.stop="toggleGraphExpanded"
              >
                <span class="node-dot" aria-hidden="true" @pointerdown.stop="startNodeDrag($event, node.id)"></span>
                <span class="node-label">{{ nodeMapLabel(node) }}</span>
              </button>
            </div>
            <div v-if="selectedNode" class="graph-stage-caption">
              <small>{{ nodeTypeLabel(selectedNode.type) }}</small>
              <strong>{{ shortLabel(selectedNode.label) }}</strong>
            </div>
          </div>
          <div v-else class="empty-canvas">
            <strong>这个空间还没有节点</strong>
            <p>先去“收集”放入材料，或者从 Inbox 接受一条路由建议。</p>
          </div>

          <section class="mode-guide">
            <span>怎么用这一层</span>
            <p>{{ interactionGuide }}</p>
          </section>

          <div class="selection-strip">
            <span>{{ selectionSummary }}</span>
            <button class="ghost-button" :disabled="!selectedNodeIds.length" @click="clearSelection">清空选择</button>
          </div>

          <section v-if="interactionMode === 'connect'" class="operation-card">
            <span>手动连边</span>
            <p>选择两个节点，写下为什么它们应该被连起来。这个原因会记录进审计日志。</p>
            <input v-model="edgeRelation" placeholder="关系，例如 supports / contradicts / clarifies" />
            <textarea v-model="edgeReason" placeholder="为什么这两个节点有关？" />
            <button class="primary-button" :disabled="busy || selectedNodeIds.length < 2 || !edgeReason.trim()" @click="createEdge">
              确认连边
            </button>
          </section>

          <section v-if="interactionMode === 'synthesize'" class="operation-card">
            <span>框选归纳</span>
            <p>选择多个节点，把它们沉淀成一条用户判断，或者保存成主题分组。</p>
            <input v-model="synthesisLabel" placeholder="判断或主题名称" />
            <textarea v-model="synthesisReason" placeholder="为什么这些节点放在一起？" />
            <textarea v-model="themeDescription" placeholder="主题描述，可选" />
            <div>
              <button class="primary-button" :disabled="busy || selectedNodeIds.length < 2 || !synthesisLabel.trim() || !synthesisReason.trim()" @click="createThought">
                生成用户判断
              </button>
              <button class="paper-button" :disabled="busy || !selectedNodeIds.length || !synthesisLabel.trim()" @click="createTheme">
                保存主题
              </button>
            </div>
          </section>

          <section v-if="interactionMode === 'prune'" class="operation-card">
            <span>削弱 / 拒绝边</span>
            <p>选择一条边，再给出原因。削弱、拒绝、隐藏都必须说明理由。</p>
            <select v-model="pruneStatus">
              <option value="confirmed">确认</option>
              <option value="proposed">改为待确认</option>
              <option value="weakened">削弱</option>
              <option value="rejected">拒绝</option>
              <option value="hidden">隐藏</option>
            </select>
            <textarea v-model="pruneReason" placeholder="为什么这样处理这条边？" />
            <button class="primary-button" :disabled="busy || !selectedEdge || pruneNeedsReason" @click="updateEdgeStatus">
              更新边状态
            </button>
          </section>
        </article>

        <aside class="space-panel graph-inspector">
          <span>Inspector</span>
          <template v-if="selectedTheme">
            <strong>{{ selectedTheme.label }}</strong>
            <p>{{ selectedTheme.description || selectedTheme.reason || '这个主题还没有说明。' }}</p>
            <dl>
              <div>
                <dt>Origin</dt>
                <dd>{{ selectedTheme.origin }}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{{ selectedTheme.status }}</dd>
              </div>
              <div>
                <dt>Members</dt>
                <dd>{{ selectedTheme.member_node_ids.length }}</dd>
              </div>
            </dl>
          </template>

          <template v-else-if="selectedEdge">
            <strong>{{ labelFor(selectedEdge.source) }} -> {{ selectedEdge.relation }} -> {{ labelFor(selectedEdge.target) }}</strong>
            <p>{{ selectedEdge.explanation || selectedEdge.weakened_reason || selectedEdge.rejected_reason || '这条边还没有解释。' }}</p>
            <dl>
              <div>
                <dt>Status</dt>
                <dd>{{ selectedEdge.status || 'confirmed' }}</dd>
              </div>
              <div>
                <dt>Origin</dt>
                <dd>{{ selectedEdge.origin || 'AI-inferred' }}</dd>
              </div>
              <div>
                <dt>Confidence</dt>
                <dd>{{ Math.round((selectedEdge.confidence ?? 0) * 100) }}%</dd>
              </div>
            </dl>
          </template>

          <template v-else-if="selectedNode">
            <strong>{{ selectedNode.label }}</strong>
            <p>{{ nodeSummary(selectedNode) }}</p>
            <dl>
              <div>
                <dt>Type</dt>
                <dd>{{ selectedNode.type }}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{{ selectedNode.status || 'confirmed' }}</dd>
              </div>
              <div v-if="sourceForSelectedNode">
                <dt>Why</dt>
                <dd>{{ sourceForSelectedNode.why_saved_status }}</dd>
              </div>
            </dl>
            <div class="inspector-actions">
              <button class="paper-button" :disabled="!sourceIdForSelectedNode" @click="openSource">
                <ExternalLink :size="15" />
                打开来源
              </button>
              <button class="paper-button" @click="askFromHere">
                <Search :size="15" />
                从这里追问
              </button>
            </div>

            <section v-if="sourceForSelectedNode" class="context-editor">
              <span>认知上下文</span>
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
              <button class="paper-button" :disabled="busy || !sourceForSelectedNode" @click="saveContext">
                更新上下文
              </button>
              <label>
                <small>移动到图谱</small>
                <select v-model="moveTarget">
                  <option v-for="item in routableSpaces" :key="item.id" :value="item.id">{{ item.name }}</option>
                </select>
              </label>
              <button class="paper-button" :disabled="busy || !moveTarget || moveTarget === sourceForSelectedNode.graph_space_id" @click="routeSelected">
                移动材料
              </button>
            </section>
          </template>

          <div v-else class="graph-empty-inspector">
            <p>选择一个材料或节点，查看它为什么被保存、和哪些问题相连。</p>
          </div>

          <section v-if="sourceDetailOpen" class="source-markdown">
            <div>
              <span>Source Markdown</span>
              <button class="text-button" @click="sourceDetailOpen = false">收起</button>
            </div>
            <pre>{{ sourceDetail?.markdown }}</pre>
          </section>

          <p v-if="localError" class="local-error">{{ localError }}</p>
        </aside>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, markRaw, onBeforeUnmount, ref, watch } from 'vue'
import {
  ExternalLink,
  GitBranch,
  Hand,
  Layers,
  Map as MapIcon,
  Maximize2,
  Minimize2,
  PencilLine,
  Route,
  Scissors,
  Search,
} from 'lucide-vue-next'
import type {
  ContextUpdatePayload,
  GraphEdge,
  GraphInteractionMode,
  GraphInsights,
  GraphLayoutPosition,
  GraphNode,
  GraphOpenLoopHotspot,
  GraphPayload,
  GraphProjectCluster,
  GraphReviewPath,
  GraphSpace,
  GraphTheme,
  GraphViewMode,
  Source,
  Suggestion,
} from '../types'

type GraphSurfaceMode = 'overview' | 'workbench'
type OverviewOpenItem = {
  key: string
  title: string
  detail: string
  badge?: string
  tone?: string
}

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
  graphChanged: []
  askFromGraph: [question: string]
}>()

const viewModes = [
  { id: 'memory' as const, label: 'Memory Map', icon: markRaw(MapIcon) },
  { id: 'evidence' as const, label: 'Evidence Path', icon: markRaw(Route) },
  { id: 'action' as const, label: 'Action Map', icon: markRaw(Layers) },
]

const interactionModes = [
  { id: 'arrange' as const, label: 'Arrange', icon: markRaw(Hand) },
  { id: 'connect' as const, label: 'Connect', icon: markRaw(GitBranch) },
  { id: 'synthesize' as const, label: 'Synthesize', icon: markRaw(PencilLine) },
  { id: 'prune' as const, label: 'Prune', icon: markRaw(Scissors) },
]

const stageContainer = ref<HTMLDivElement | null>(null)

const surfaceMode = ref<GraphSurfaceMode>('overview')
const viewMode = ref<GraphViewMode>('memory')
const interactionMode = ref<GraphInteractionMode>('arrange')
const layoutPositions = ref<GraphLayoutPosition[]>([])
const themes = ref<GraphTheme[]>([])
const selectedNodeIds = ref<string[]>([])
const selectedEdgeId = ref('')
const selectedThemeId = ref('')
const selectedSource = ref<Source | null>(null)
const sourceDetail = ref<{ markdown: string; detail?: Source } | null>(null)
const sourceDetailOpen = ref(false)
const sourceFilter = ref('')
const savingLayout = ref(false)
const graphExpanded = ref(false)
const localError = ref('')
const nodePositions = ref<Record<string, { x: number; y: number }>>({})
const draggingNodeId = ref('')
const pendingDragNodeId = ref('')
const pendingDragAddToSelection = ref(false)
const pendingDragStart = ref({ x: 0, y: 0 })
const graphFocusNodeId = ref('')
const nodeDragOffset = ref({ x: 0, y: 0 })
const graphZoom = ref(1)
const graphPan = ref({ x: 0, y: 0 })
const panningGraph = ref(false)
const lastPanPoint = ref({ x: 0, y: 0 })

const edgeRelation = ref('related_to')
const edgeReason = ref('')
const synthesisLabel = ref('')
const synthesisReason = ref('')
const themeDescription = ref('')
const pruneStatus = ref<'confirmed' | 'proposed' | 'rejected' | 'weakened' | 'hidden'>('weakened')
const pruneReason = ref('')

const moveTarget = ref('')
const editWhy = ref('')
const editProject = ref('')
const editLoops = ref('')
const editSpaceName = ref('')
const editSpacePurpose = ref('')
const editSpaceDescription = ref('')
const editSpaceColor = ref('#315f9f')

const graphSpaceId = computed(() => props.space?.id || 'all')
const routableSpaces = computed(() => props.spaces.filter((space) => space.status === 'active' && space.id !== 'inbox'))
const insights = computed<GraphInsights>(() => props.graph.insights || {})
const projectClusters = computed<GraphProjectCluster[]>(() => insights.value.project_clusters || [])
const openLoopHotspots = computed<GraphOpenLoopHotspot[]>(() => insights.value.open_loop_hotspots || [])
const reviewPaths = computed<GraphReviewPath[]>(() => insights.value.high_value_review_paths || [])
const adjacencyCount = computed(() => {
  const counts = new Map<string, number>()
  for (const edge of props.graph.edges) {
    counts.set(edge.source, (counts.get(edge.source) || 0) + 1)
    counts.set(edge.target, (counts.get(edge.target) || 0) + 1)
  }
  return counts
})
const visibleSources = computed(() => {
  const query = sourceFilter.value.trim().toLowerCase()
  if (!query) return props.sources
  return props.sources.filter((source) => {
    return [source.title, source.why_saved, source.summary, source.related_project]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(query))
  })
})
const graphTransformStyle = computed(() => ({
  transform: `matrix(${graphZoom.value}, 0, 0, ${graphZoom.value}, ${graphPan.value.x}, ${graphPan.value.y})`,
}))
const anchorNodeId = computed(() => {
  if (graphFocusNodeId.value) return graphFocusNodeId.value
  const firstSource = props.sources[0]
  if (firstSource) return `source_${firstSource.id}`
  return props.graph.nodes.find((node) => node.type === 'source')?.id || props.graph.nodes[0]?.id || ''
})
const neighborhoodDistances = computed(() => {
  const anchor = anchorNodeId.value
  const distances = new Map<string, number>()
  if (!anchor) return distances
  distances.set(anchor, 0)
  const maxDepth = viewMode.value === 'action' ? 2 : 2
  const traversableEdges = props.graph.edges.filter((edge) => edge.status !== 'hidden')
  for (let depth = 0; depth < maxDepth; depth += 1) {
    const frontier = [...distances.entries()]
      .filter(([, distance]) => distance === depth)
      .map(([nodeId]) => nodeId)
    for (const nodeId of frontier) {
      for (const edge of traversableEdges) {
        if (edge.source === nodeId && !distances.has(edge.target)) distances.set(edge.target, depth + 1)
        if (edge.target === nodeId && !distances.has(edge.source)) distances.set(edge.source, depth + 1)
      }
    }
  }
  return distances
})
const visibleGraphNodes = computed(() => {
  const distances = neighborhoodDistances.value
  const maxNodes = viewMode.value === 'action' ? 18 : 14
  return props.graph.nodes
    .filter((node) => distances.has(node.id))
    .sort((a, b) => {
      const distanceDelta = (distances.get(a.id) || 0) - (distances.get(b.id) || 0)
      if (distanceDelta) return distanceDelta
      return nodeRank(a) - nodeRank(b)
    })
    .slice(0, maxNodes)
})
const visibleGraphNodeIds = computed(() => new Set(visibleGraphNodes.value.map((node) => node.id)))
const visibleGraphEdges = computed(() => {
  return props.graph.edges.filter((edge) => {
    if (edge.status === 'hidden' && interactionMode.value !== 'prune') return false
    return visibleGraphNodeIds.value.has(edge.source) && visibleGraphNodeIds.value.has(edge.target)
  })
})
const labeledGraphEdges = computed(() => {
  if (selectedEdge.value) return [selectedEdge.value]
  if (!graphExpanded.value) return []
  return visibleGraphEdges.value
    .filter((edge) => edge.origin === 'user' || edge.evidence_kind === 'user-stated')
    .slice(0, 2)
})
const selectedNode = computed(() => {
  const lastNodeId = selectedNodeIds.value[selectedNodeIds.value.length - 1]
  return props.graph.nodes.find((node) => node.id === lastNodeId) || null
})
const selectedEdge = computed(() => props.graph.edges.find((edge) => edge.id === selectedEdgeId.value) || null)
const selectedTheme = computed(() => themes.value.find((theme) => theme.id === selectedThemeId.value) || null)
const sourceIdForSelectedNode = computed(() => selectedNode.value ? sourceIdForNode(selectedNode.value) : '')
const sourceForSelectedNode = computed(() => {
  if (!sourceIdForSelectedNode.value) return null
  return props.sources.find((source) => source.id === sourceIdForSelectedNode.value) || null
})
const overviewProjects = computed(() => projectClusters.value.slice(0, 3))
const overviewRecentSources = computed(() => {
  return [...props.sources]
    .sort((left, right) => Date.parse(right.imported_at || '') - Date.parse(left.imported_at || ''))
    .slice(0, 4)
})
const overviewKeyNodes = computed(() => {
  const preferredTypes = ['project', 'thought', 'task', 'question']
  const importantNodes = props.graph.nodes
    .filter((node) => preferredTypes.includes(node.type))
    .sort((left, right) => {
      const typeDelta = preferredTypes.indexOf(left.type) - preferredTypes.indexOf(right.type)
      if (typeDelta) return typeDelta
      return (adjacencyCount.value.get(right.id) || 0) - (adjacencyCount.value.get(left.id) || 0)
    })
  const fallbackNodes = props.graph.nodes
    .filter((node) => !importantNodes.find((item) => item.id === node.id))
    .sort((left, right) => (adjacencyCount.value.get(right.id) || 0) - (adjacencyCount.value.get(left.id) || 0))
  return [...importantNodes, ...fallbackNodes].slice(0, 5)
})
const overviewOpenItems = computed<OverviewOpenItem[]>(() => {
  const hotspotItems = openLoopHotspots.value.slice(0, 4).map((item) => ({
    key: `hotspot:${item.open_loop}`,
    title: item.open_loop,
    detail: item.count > 1 ? `来自 ${item.count} 条材料的开放问题。` : `来自 ${item.sources[0]?.title || '当前材料'} 的开放问题。`,
    badge: item.sources[0]?.status === 'user-stated' ? 'user-stated / 用户原话' : 'AI-inferred / AI 推断',
    tone: item.sources[0]?.status === 'user-stated' ? 'tone-user' : 'tone-ai',
  }))
  const suggestionItems = props.suggestions.slice(0, 3).map((suggestion) => ({
    key: `suggestion:${suggestion.id}`,
    title: suggestion.reason,
    detail: `${Math.round(suggestion.confidence * 100)}% 置信度，等待你确认是否采纳。`,
    badge: 'graph-path / 图谱建议',
    tone: 'tone-graph',
  }))
  const pathItems = reviewPaths.value.slice(0, 2).map((item) => ({
    key: `path:${item.source_id}:${item.path}`,
    title: item.title,
    detail: item.why || '这条路径提示了一个值得继续追问的判断连接。',
    badge: item.status === 'user-stated' ? 'user-stated / 用户原话' : 'AI-inferred / AI 推断',
    tone: item.status === 'user-stated' ? 'tone-user' : 'tone-ai',
  }))
  return [...hotspotItems, ...suggestionItems, ...pathItems].slice(0, 6)
})
const overviewOpenCount = computed(() => {
  if (openLoopHotspots.value.length) return openLoopHotspots.value.length
  if (props.suggestions.length) return props.suggestions.length
  if (reviewPaths.value.length) return reviewPaths.value.length
  return props.sources.reduce((total, source) => total + (source.open_loops?.length || 0), 0)
})
const overviewOpenLabel = computed(() => {
  return props.suggestions.length ? '建议' : '开放问题'
})
const spaceDescription = computed(() => {
  if (props.space?.id === 'inbox') {
    return '新材料会先放在这里，等待确认和整理。'
  }
  if (props.space?.id === 'default') {
    return '默认记忆空间，保存当前 SnapGraph 工作流的主要材料、判断和开放问题。'
  }
  return props.space?.purpose || props.space?.description || '这个空间保存了相关材料、想法和连接，用来帮助之后找回判断。'
})
const overviewSummary = computed(() => {
  const projectList = overviewProjects.value.map((item) => item.project).filter(Boolean)
  if (projectList.length) {
    const lead = projectList.slice(0, 2).join('、')
    const openCount = overviewOpenCount.value
    if (openCount) {
      return `这个空间现在主要围绕 ${lead} 这些主题组织材料，并把 ${openCount} 个待继续处理的问题保留下来，方便之后找回判断。`
    }
    return `这个空间现在主要围绕 ${lead} 这些主题组织材料，把来源、想法和连接整理成可回看的判断脉络。`
  }
  if (props.sources.length || props.graph.nodes.length) {
    return '这个空间保存了相关材料、想法和连接，用来帮助之后找回判断。'
  }
  return '这个空间保存了相关材料、想法和连接，用来帮助之后找回判断。'
})
const pruneNeedsReason = computed(() => {
  return ['rejected', 'weakened', 'hidden'].includes(pruneStatus.value) && !pruneReason.value.trim()
})
const currentViewLabel = computed(() => viewModes.find((mode) => mode.id === viewMode.value)?.label || 'Memory Map')
const modeDescription = computed(() => {
  if (viewMode.value === 'evidence') return '查看某个回答或判断背后的证据路径。'
  if (viewMode.value === 'action') return '查看开放问题、下一步和待处理连接。'
  return '查看这个空间里材料、想法和项目之间的整体结构。'
})
const selectionSummary = computed(() => {
  const nodeCount = selectedNodeIds.value.length
  if (selectedEdge.value) return `已选择 1 条边：${selectedEdge.value.relation}`
  if (nodeCount) return `已选择 ${nodeCount} 个节点`
  return '点击节点或边查看细节；按 Shift 可多选节点。'
})
const interactionGuide = computed(() => {
  if (interactionMode.value === 'connect') {
    return '连续点两个节点，再写关系和原因。再次点击已选节点会取消选择。'
  }
  if (interactionMode.value === 'synthesize') {
    return '连续点多个节点，把它们归纳成一条用户判断，或者保存成一个主题分组。'
  }
  if (interactionMode.value === 'prune') {
    return '点击一条边，确认、削弱或拒绝它。削弱/拒绝/隐藏都必须写原因，方便以后追溯。'
  }
  return '默认只展示当前材料附近的证据路径。点圆点看细节，双击画布放大；想继续追问，点右侧“从这里追问”。'
})

watch(() => props.space, (space) => {
  editSpaceName.value = space?.name || ''
  editSpacePurpose.value = space?.purpose || ''
  editSpaceDescription.value = space?.description || ''
  editSpaceColor.value = space?.color || '#315f9f'
  surfaceMode.value = 'overview'
  selectedSource.value = null
  selectedNodeIds.value = []
  selectedEdgeId.value = ''
  selectedThemeId.value = ''
  graphExpanded.value = false
  graphFocusNodeId.value = ''
  resetGraphView()
  if (space) {
    loadLayout()
    loadThemes()
  }
}, { immediate: true })

watch(selectedSource, (source) => {
  moveTarget.value = source?.graph_space_id || props.space?.id || 'default'
  editWhy.value = source?.why_saved || ''
  editProject.value = source?.related_project || ''
  editLoops.value = source?.open_loops?.join('\n') || ''
})

watch(sourceForSelectedNode, (source) => {
  if (!source) return
  selectedSource.value = source
}, { immediate: true })

watch(() => props.sources, (sources) => {
  if (!sources.length) {
    selectedSource.value = null
    selectedNodeIds.value = []
    graphFocusNodeId.value = ''
    return
  }
  if (!selectedSource.value) {
    graphFocusNodeId.value = `source_${sources[0].id}`
    selectedNodeIds.value = []
    return
  }
  selectedSource.value = sources.find((source) => source.id === selectedSource.value?.id) || null
  if (!graphFocusNodeId.value) {
    graphFocusNodeId.value = `source_${selectedSource.value?.id || sources[0].id}`
  }
}, { immediate: true })

watch([() => props.graph.nodes, layoutPositions, viewMode, graphFocusNodeId], () => {
  syncNodePositions()
}, { deep: true, immediate: true })

onBeforeUnmount(() => {
  stopNodeDrag()
  stopGraphPan()
})

async function loadLayout() {
  if (!props.space) return
  try {
    const payload = await api<{ positions: GraphLayoutPosition[] }>(`/api/graph/layout?view_id=${encodeURIComponent(viewId())}`)
    layoutPositions.value = payload.positions || []
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function loadThemes() {
  if (!props.space) return
  try {
    const payload = await api<{ themes: GraphTheme[] }>(`/api/graph/themes?space_id=${encodeURIComponent(props.space.id)}`)
    themes.value = payload.themes || []
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

function syncNodePositions() {
  const saved = new Map(layoutPositions.value.map((position) => [position.node_id, position]))
  const next: Record<string, { x: number; y: number }> = {}
  const nodes = visibleGraphNodes.value
  nodes.forEach((node, index) => {
    const existing = nodePositions.value[node.id]
    const persisted = saved.get(node.id)
    if (persisted?.locked) {
      next[node.id] = { x: clampGraphX(persisted.x), y: clampGraphY(persisted.y) }
    } else if (existing) {
      next[node.id] = existing
    } else {
      next[node.id] = fallbackPosition(index, Math.max(nodes.length, 1), node)
    }
  })
  nodePositions.value = next
}

async function saveCurrentLayout() {
  if (!props.space) return
  savingLayout.value = true
  localError.value = ''
  try {
    const positions = visibleGraphNodes.value.map((node) => ({
      node_id: node.id,
      x: nodePositions.value[node.id]?.x ?? 500,
      y: nodePositions.value[node.id]?.y ?? 340,
      locked: true,
    }))
    await api('/api/graph/layout', {
      method: 'PATCH',
      body: JSON.stringify({
        view_id: viewId(),
        graph_space_id: props.space.id,
        positions,
      }),
    })
    layoutPositions.value = positions
  } catch (error) {
    localError.value = messageFromError(error)
  } finally {
    savingLayout.value = false
  }
}

function selectSource(source: Source) {
  selectedSource.value = source
  selectedThemeId.value = ''
  selectedEdgeId.value = ''
  const nodeId = `source_${source.id}`
  graphFocusNodeId.value = nodeId
  selectedNodeIds.value = [nodeId]
}

function selectTheme(themeId: string) {
  selectedThemeId.value = themeId
  selectedEdgeId.value = ''
  selectedNodeIds.value = themes.value.find((item) => item.id === themeId)?.member_node_ids || []
  selectedSource.value = null
}

function clearSelection() {
  selectedNodeIds.value = []
  selectedEdgeId.value = ''
  selectedThemeId.value = ''
  selectedSource.value = null
}

function setInteractionMode(mode: GraphInteractionMode) {
  interactionMode.value = mode
  clearSelection()
}

async function createEdge() {
  const [source, target] = selectedNodeIds.value
  if (!props.space || !source || !target) return
  localError.value = ''
  try {
    await api('/api/graph/edges', {
      method: 'POST',
      body: JSON.stringify({
        source,
        target,
        relation: edgeRelation.value.trim() || 'related_to',
        reason: edgeReason.value.trim(),
        graph_space_id: props.space.id,
      }),
    })
    edgeReason.value = ''
    emit('graphChanged')
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function createThought() {
  if (!props.space) return
  localError.value = ''
  try {
    await api('/api/graph/thoughts', {
      method: 'POST',
      body: JSON.stringify({
        graph_space_id: props.space.id,
        node_ids: selectedNodeIds.value,
        label: synthesisLabel.value.trim(),
        reason: synthesisReason.value.trim(),
      }),
    })
    synthesisLabel.value = ''
    synthesisReason.value = ''
    emit('graphChanged')
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function createTheme() {
  if (!props.space) return
  localError.value = ''
  try {
    await api('/api/graph/themes', {
      method: 'POST',
      body: JSON.stringify({
        graph_space_id: props.space.id,
        label: synthesisLabel.value.trim(),
        member_node_ids: selectedNodeIds.value,
        reason: synthesisReason.value.trim(),
        description: themeDescription.value.trim(),
      }),
    })
    synthesisLabel.value = ''
    synthesisReason.value = ''
    themeDescription.value = ''
    await loadThemes()
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function updateEdgeStatus() {
  if (!selectedEdge.value) return
  localError.value = ''
  try {
    await api(`/api/graph/edges/${encodeURIComponent(selectedEdge.value.id)}`, {
      method: 'PATCH',
      body: JSON.stringify({
        status: pruneStatus.value,
        reason: pruneReason.value.trim(),
      }),
    })
    pruneReason.value = ''
    emit('graphChanged')
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function openSource() {
  const sourceId = sourceIdForSelectedNode.value
  if (!sourceId) return
  localError.value = ''
  try {
    sourceDetail.value = await api<{ markdown: string; detail?: Source }>(`/api/sources/${encodeURIComponent(sourceId)}`)
    sourceDetailOpen.value = true
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

function askFromHere() {
  const clue = selectedNode.value?.label || sourceForSelectedNode.value?.title
  if (!clue) return
  emit('askFromGraph', `我之前关于「${clue}」想过什么？`)
}

function routeSelected() {
  const source = sourceForSelectedNode.value
  if (source && moveTarget.value) {
    emit('moveSource', source.id, moveTarget.value)
  }
}

function saveContext() {
  const source = sourceForSelectedNode.value
  if (!source) return
  emit('updateContext', source.id, {
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

function askFromSpace() {
  emit('askFromGraph', '这个空间最近在追踪什么问题？')
}

function openActionWorkbench() {
  surfaceMode.value = 'workbench'
  viewMode.value = 'action'
  interactionMode.value = 'arrange'
  clearSelection()
}

function sourceToneClass(source: Source) {
  if (source.why_saved_status === 'user-stated') return 'tone-user'
  if (source.why_saved_status === 'AI-inferred') return 'tone-ai'
  return 'tone-source'
}

function sourceBadgeLabel(source: Source) {
  if (source.why_saved_status === 'user-stated') return 'user-stated / 用户原话'
  if (source.why_saved_status === 'AI-inferred') return 'AI-inferred / AI 推断'
  return 'source / 材料'
}

function nodeToneClass(node: GraphNode) {
  if (node.type === 'task') return 'tone-ai'
  if (node.type === 'project' || node.type === 'question') return 'tone-graph'
  return 'tone-source'
}

function sourcePreview(source: Source) {
  const why = cleanOverviewText(source.why_saved)
  if (why) return why
  const summary = cleanOverviewText(source.summary)
  if (summary) return summary
  return '这条材料已经进入图谱，等待之后继续连接。'
}

function keyNodeSummary(node: GraphNode) {
  const source = props.sources.find((item) => item.id === sourceIdForNode(node))
  if (source) return sourcePreview(source)
  const connections = adjacencyCount.value.get(node.id) || 0
  if (node.type === 'task') return connections ? `目前连着 ${connections} 条路径，适合作为下一步整理入口。` : '这是一个待继续处理的开放问题。'
  if (node.type === 'project') return connections ? `目前与 ${connections} 条连接相关，帮助你理解这个空间在围绕什么生长。` : '这个项目节点正在等待更多材料连接过来。'
  if (node.type === 'thought') return connections ? `目前连着 ${connections} 条连接，用来承接已经形成的判断。` : '这个判断节点已经形成，但还需要更多连接支撑。'
  return connections ? `目前连着 ${connections} 条路径。` : '这个节点还在等待更多材料补全。'
}

function cleanOverviewText(text: string) {
  if (!text) return ''
  return text
    .replace(/^AI-inferred:\s*/i, '')
    .replace(/^user-stated:\s*/i, '')
    .replace(/^ai_inferred:\s*/i, '')
    .trim()
}

function sourceIdForNode(node: GraphNode) {
  const sourceId = node.properties?.source_id
  if (typeof sourceId === 'string' && sourceId) return sourceId
  if (node.id.startsWith('source_')) return node.id.slice('source_'.length)
  return ''
}

function nodeSummary(node: GraphNode) {
  const source = props.sources.find((item) => item.id === sourceIdForNode(node))
  if (source) return source.summary || source.why_saved || '这份材料还没有摘要。'
  const reason = node.properties?.reason
  if (typeof reason === 'string' && reason) return reason
  return '这个节点来自图谱结构，可通过边和相邻材料理解它的位置。'
}

function labelFor(nodeId: string) {
  return props.graph.nodes.find((node) => node.id === nodeId)?.label || nodeId
}

function selectGraphNode(nodeId: string, addToSelection = false) {
  selectedThemeId.value = ''
  selectedEdgeId.value = ''
  if (interactionMode.value === 'connect') {
    if (selectedNodeIds.value.includes(nodeId)) {
      selectedNodeIds.value = selectedNodeIds.value.filter((id) => id !== nodeId)
    } else if (selectedNodeIds.value.length >= 2) {
      selectedNodeIds.value = [selectedNodeIds.value[0], nodeId]
    } else {
      selectedNodeIds.value = [...selectedNodeIds.value, nodeId]
    }
  } else if (interactionMode.value === 'synthesize' || addToSelection) {
    selectedNodeIds.value = selectedNodeIds.value.includes(nodeId)
      ? selectedNodeIds.value.filter((id) => id !== nodeId)
      : [...selectedNodeIds.value, nodeId]
  } else {
    selectedNodeIds.value = [nodeId]
  }
  const node = props.graph.nodes.find((item) => item.id === nodeId)
  const sourceId = node ? sourceIdForNode(node) : ''
  selectedSource.value = sourceId ? props.sources.find((source) => source.id === sourceId) || null : null
}

function selectGraphEdge(edgeId: string) {
  selectedThemeId.value = ''
  selectedNodeIds.value = []
  selectedEdgeId.value = edgeId
  selectedSource.value = null
}

function toggleGraphExpanded() {
  graphExpanded.value = !graphExpanded.value
}

function resetGraphView() {
  graphZoom.value = 1
  graphPan.value = { x: 0, y: 0 }
}

function resetAutoLayout() {
  const next: Record<string, { x: number; y: number }> = {}
  visibleGraphNodes.value.forEach((node, index) => {
    next[node.id] = fallbackPosition(index, Math.max(visibleGraphNodes.value.length, 1), node)
  })
  nodePositions.value = next
  layoutPositions.value = []
  resetGraphView()
}

function graphPointFromEvent(event: PointerEvent | WheelEvent) {
  if (!stageContainer.value) return { x: 500, y: 340 }
  const rect = stageContainer.value.getBoundingClientRect()
  return {
    x: (((event.clientX - rect.left - graphPan.value.x) / graphZoom.value) / Math.max(rect.width, 1)) * 1000,
    y: (((event.clientY - rect.top - graphPan.value.y) / graphZoom.value) / Math.max(rect.height, 1)) * 680,
  }
}

function nodePositionStyle(nodeId: string) {
  const position = nodePositions.value[nodeId] || { x: 500, y: 340 }
  return {
    left: `${(position.x / 1000) * 100}%`,
    top: `${(position.y / 680) * 100}%`,
  }
}

function edgePath(edge: GraphEdge) {
  const source = positionFor(edge.source)
  const target = positionFor(edge.target)
  const dx = target.x - source.x
  const dy = target.y - source.y
  const curve = Math.min(70, Math.max(24, Math.sqrt(dx * dx + dy * dy) * 0.16))
  const cx1 = source.x + dx * 0.34 - dy / curve
  const cy1 = source.y + dy * 0.34 + dx / curve
  const cx2 = source.x + dx * 0.66 - dy / curve
  const cy2 = source.y + dy * 0.66 + dx / curve
  return `M ${source.x} ${source.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${target.x} ${target.y}`
}

function edgeMidpoint(edge: GraphEdge) {
  const source = positionFor(edge.source)
  const target = positionFor(edge.target)
  return {
    x: source.x + (target.x - source.x) * 0.5,
    y: source.y + (target.y - source.y) * 0.5,
  }
}

function positionFor(nodeId: string) {
  return nodePositions.value[nodeId] || { x: 500, y: 340 }
}

function viewId() {
  return `space:${graphSpaceId.value}`
}

function fallbackPosition(index: number, total: number, node: GraphNode) {
  const distance = neighborhoodDistances.value.get(node.id) || 0
  if (distance === 0) {
    return { x: 500, y: 340 }
  }
  const sameDistance = visibleGraphNodes.value.filter((item) => (neighborhoodDistances.value.get(item.id) || 0) === distance)
  const localIndex = Math.max(0, sameDistance.findIndex((item) => item.id === node.id))
  const localTotal = Math.max(1, sameDistance.length)
  const angle = -Math.PI / 2 + (Math.PI * 2 * localIndex) / localTotal + distance * 0.22
  const radiusX = distance === 1 ? 285 : 410
  const radiusY = distance === 1 ? 190 : 270
  return {
    x: clampGraphX(500 + Math.cos(angle) * radiusX),
    y: clampGraphY(355 + Math.sin(angle) * radiusY),
  }
}

function nodeRank(node: GraphNode) {
  const rank: Record<string, number> = {
    source: 0,
    thought: 1,
    project: 2,
    task: 3,
  }
  return rank[node.type] ?? 9
}

function startNodeDrag(event: PointerEvent, nodeId: string) {
  if (interactionMode.value !== 'arrange') return
  pendingDragNodeId.value = nodeId
  pendingDragAddToSelection.value = event.shiftKey
  pendingDragStart.value = { x: event.clientX, y: event.clientY }
  const point = graphPointFromEvent(event)
  const current = nodePositions.value[nodeId] || { x: 500, y: 340 }
  nodeDragOffset.value = {
    x: current.x - point.x,
    y: current.y - point.y,
  }
  window.addEventListener('pointermove', dragNode)
  window.addEventListener('pointerup', stopNodeDrag, { once: true })
}

function dragNode(event: PointerEvent) {
  if (!draggingNodeId.value) {
    if (!pendingDragNodeId.value) return
    const moved = Math.hypot(event.clientX - pendingDragStart.value.x, event.clientY - pendingDragStart.value.y)
    if (moved < 5) return
    draggingNodeId.value = pendingDragNodeId.value
    selectGraphNode(draggingNodeId.value, pendingDragAddToSelection.value)
  }
  const point = graphPointFromEvent(event)
  nodePositions.value = {
    ...nodePositions.value,
    [draggingNodeId.value]: {
      x: clampGraphX(point.x + nodeDragOffset.value.x),
      y: clampGraphY(point.y + nodeDragOffset.value.y),
    },
  }
}

function stopNodeDrag() {
  draggingNodeId.value = ''
  pendingDragNodeId.value = ''
  pendingDragAddToSelection.value = false
  nodeDragOffset.value = { x: 0, y: 0 }
  window.removeEventListener('pointermove', dragNode)
}

function startGraphPan(event: PointerEvent) {
  const target = event.target as HTMLElement | null
  if (
    event.button !== 0 ||
    interactionMode.value !== 'arrange' ||
    target?.closest('.paper-graph-node, .graph-edge-hit, button, .graph-stage-caption')
  ) {
    return
  }
  panningGraph.value = true
  lastPanPoint.value = { x: event.clientX, y: event.clientY }
  window.addEventListener('pointermove', panGraph)
  window.addEventListener('pointerup', stopGraphPan, { once: true })
}

function panGraph(event: PointerEvent) {
  if (!panningGraph.value) return
  const dx = event.clientX - lastPanPoint.value.x
  const dy = event.clientY - lastPanPoint.value.y
  graphPan.value = {
    x: graphPan.value.x + dx,
    y: graphPan.value.y + dy,
  }
  lastPanPoint.value = { x: event.clientX, y: event.clientY }
}

function stopGraphPan() {
  panningGraph.value = false
  window.removeEventListener('pointermove', panGraph)
}

function zoomGraph(event: WheelEvent) {
  if (!stageContainer.value) return
  const rect = stageContainer.value.getBoundingClientRect()
  const oldZoom = graphZoom.value
  const nextZoom = Math.min(1.9, Math.max(0.68, oldZoom * (event.deltaY > 0 ? 0.9 : 1.1)))
  const pointerX = event.clientX - rect.left
  const pointerY = event.clientY - rect.top
  graphPan.value = {
    x: pointerX - ((pointerX - graphPan.value.x) * nextZoom) / oldZoom,
    y: pointerY - ((pointerY - graphPan.value.y) * nextZoom) / oldZoom,
  }
  graphZoom.value = nextZoom
}

function clampGraphX(value: number) {
  return Math.min(940, Math.max(60, Number.isFinite(value) ? value : 500))
}

function clampGraphY(value: number) {
  return Math.min(620, Math.max(58, Number.isFinite(value) ? value : 340))
}

function shortLabel(label: string) {
  const cleaned = label.replace(/\s+/g, ' ').trim()
  return cleaned.length > 52 ? `${cleaned.slice(0, 50)}...` : cleaned
}

function nodeMapLabel(node: GraphNode) {
  const source = node.type === 'source' ? props.sources.find((item) => item.id === sourceIdForNode(node)) : null
  const cleaned = (source?.title || node.label).replace(/\s+/g, ' ').trim()
  return cleaned.length > 30 ? `${cleaned.slice(0, 28)}...` : cleaned
}

function nodeTypeLabel(type: string) {
  const labels: Record<string, string> = {
    source: '材料',
    thought: '想法',
    project: '项目',
    task: '未闭环',
    question: '问题',
  }
  return labels[type] || type
}

function edgeClasses(edge: GraphEdge) {
  const classes = [`status-${edge.status || 'confirmed'}`]
  if (edge.origin === 'user') classes.push('origin-user')
  if (viewMode.value === 'evidence' && ['evidence_for', 'triggered_thought', 'supports'].includes(edge.relation)) {
    classes.push('mode-emphasis')
  }
  if (viewMode.value === 'action' && ['follow_up'].includes(edge.relation)) {
    classes.push('mode-emphasis')
  }
  return classes.join(' ')
}

function graphStyle() {
  return [
    {
      selector: 'node',
      style: {
        label: 'data(label)',
        'background-color': '#fffefd',
        'border-width': 1,
        'border-color': 'rgba(77, 61, 42, 0.22)',
        color: '#1c1b19',
        'font-size': 13,
        'font-family': 'Inter, -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif',
        'text-wrap': 'wrap',
        'text-max-width': 142,
        shape: 'round-rectangle',
        width: 136,
        height: 42,
        padding: '8px',
      },
    },
    { selector: '.node-source', style: { 'border-color': '#315f9f', color: '#315f9f' } },
    { selector: '.node-thought', style: { 'border-color': '#356f5c', color: '#356f5c' } },
    { selector: '.node-task', style: { 'border-color': '#8b5631', color: '#8b5631' } },
    {
      selector: 'edge',
      style: {
        label: 'data(label)',
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle',
        width: 1.25,
        'line-color': 'rgba(77, 61, 42, 0.28)',
        'target-arrow-color': 'rgba(77, 61, 42, 0.28)',
        color: '#85796d',
        'font-size': 10,
        'text-background-color': '#fbfaf7',
        'text-background-opacity': 0.82,
        'text-background-padding': '3px',
      },
    },
    { selector: '.origin-user', style: { 'line-color': '#356f5c', 'target-arrow-color': '#356f5c', width: 2 } },
    { selector: '.mode-emphasis', style: { 'line-color': '#315f9f', 'target-arrow-color': '#315f9f', width: 2.4 } },
    { selector: '.status-proposed', style: { 'line-style': 'dashed' } },
    { selector: '.status-weakened', style: { opacity: 0.56, 'line-style': 'dashed' } },
    { selector: '.status-rejected', style: { opacity: 0.32, 'line-style': 'dotted' } },
    { selector: ':selected', style: { 'border-width': 3, 'border-color': '#28231d', 'line-color': '#28231d', 'target-arrow-color': '#28231d' } },
  ]
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

function messageFromError(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}
</script>
