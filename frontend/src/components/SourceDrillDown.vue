<template>
  <section class="source-drilldown">
    <header class="drilldown-head">
      <button class="text-button" @click="$emit('back')">&larr; 返回全局地图</button>
      <div>
        <p class="eyebrow">{{ drillMode === 'expand' ? '材料展开' : '思路线' }}</p>
        <h3>{{ title }}</h3>
      </div>
    </header>

    <!-- Expand mode: subgraph + inspector -->
    <div v-if="drillMode === 'expand'" class="drilldown-body">
      <div
        ref="stageContainer"
        class="graph-stage drilldown-stage"
        @pointerdown="startPan"
        @pointermove="handlePanMove"
        @pointerup="endPan"
        @pointerleave="endPan"
        @wheel.prevent="handleZoom"
      >
        <div v-if="subgraphNodes.length" class="graph-map-layer" :style="transformStyle">
          <svg class="graph-stage-edges" viewBox="0 0 1000 680" preserveAspectRatio="none">
            <defs>
              <marker id="drilldown-arrow" viewBox="0 0 10 6" refX="9" refY="3" markerWidth="8" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 8 3 L 0 5" fill="none" stroke="rgba(77,61,42,0.42)" />
              </marker>
            </defs>
            <g v-for="edge in subgraphEdges" :key="edge.id">
              <path
                :d="drillEdgePath(edge)"
                class="paper-edge"
                :class="{
                  'paper-edge-touch': true,
                  'paper-edge-proposed': edge.status === 'proposed',
                  'paper-edge-weakened': edge.status === 'weakened',
                  'paper-edge-rejected': edge.status === 'rejected',
                }"
                marker-end="url(#drilldown-arrow)"
              />
            </g>
          </svg>

          <button
            v-for="node in subgraphNodes"
            :key="node.id"
            class="paper-graph-node"
            :class="[`node-${node.type}`, `status-${node.status || 'confirmed'}`]"
            :style="drillNodeStyle(node.id)"
            :title="node.label"
          >
            <span class="node-dot"></span>
            <span class="node-label">{{ shortLabel(node.label) }}</span>
          </button>
        </div>
        <p v-else class="subtle-empty-state drilldown-empty">这个材料还没有图谱节点。先在「收集」中放入材料。</p>
      </div>

      <aside v-if="expandedSource" class="drilldown-inspector">
        <div class="section-head compact">
          <p class="section-kicker">材料详情</p>
          <h4>{{ expandedSource.source_detail.title }}</h4>
        </div>
        <p class="inspector-summary">{{ expandedSource.source_detail.why_saved || expandedSource.source_detail.summary }}</p>
        <dl class="inspector-dl">
          <div><dt>想法数</dt><dd>{{ expandedSource.thought_count }}</dd></div>
          <div><dt>未闭环任务</dt><dd>{{ expandedSource.task_count }}</dd></div>
          <div v-if="expandedSource.project_name"><dt>所属项目</dt><dd>{{ expandedSource.project_name }}</dd></div>
          <div><dt>信任状态</dt><dd>
            <span class="evidence-badge" :class="expandedSource.source_detail.why_saved_status === 'user-stated' ? 'tone-user' : 'tone-ai'">
              {{ expandedSource.source_detail.why_saved_status === 'user-stated' ? '用户原话' : 'AI推断' }}
            </span>
          </dd></div>
        </dl>
        <div class="inspector-actions">
          <button class="paper-button" @click="openSource">打开材料原文</button>
          <button class="paper-button" @click="askHere">从这里追问</button>
        </div>
      </aside>
    </div>

    <!-- Thread mode: horizontal flow -->
    <div v-else class="thread-view">
      <div v-if="threadNodes.length" class="thread-path-flow">
        <div v-for="(node, index) in threadNodes" :key="node.id" class="thread-node-wrapper">
          <div class="thread-node" :class="[`node-${node.type}`, { 'is-endpoint': index === 0 || index === threadNodes.length - 1 }]">
            <span class="thread-node-icon">{{ typeIcon(node.type) }}</span>
            <strong>{{ shortLabel(node.label) }}</strong>
            <small>{{ typeLabel(node.type) }}</small>
          </div>
          <div v-if="index < threadNodes.length - 1" class="thread-connector">
            <span class="thread-edge-label">{{ threadEdges[index]?.relation || '' }}</span>
            <svg viewBox="0 0 60 10" class="thread-arrow">
              <path d="M 0 5 L 50 5 M 42 1 L 54 5 L 42 9" fill="none" stroke="rgba(77,61,42,0.42)" stroke-width="1.5" />
            </svg>
          </div>
        </div>
      </div>
      <p v-else class="subtle-empty-state">未找到连接这两个材料的路径。</p>
      <p v-if="pathDescription" class="thread-description">{{ pathDescription }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GraphNode, GraphEdge, SourceMapEntry } from '../types'

const props = defineProps<{
  drillMode: 'expand' | 'thread'
  expandedSource: SourceMapEntry | null
  subgraphNodes: GraphNode[]
  subgraphEdges: GraphEdge[]
  threadNodes: GraphNode[]
  threadEdges: GraphEdge[]
  pathDescription: string
}>()

const emit = defineEmits<{
  back: []
  askHere: [question: string]
  openSource: [sourceId: string]
}>()

const stageContainer = ref<HTMLDivElement | null>(null)
const drillLayout = ref<Record<string, { x: number; y: number }>>({})
const zoom = ref(1)
const pan = ref({ x: 0, y: 0 })
const panning = ref(false)
const lastPan = ref({ x: 0, y: 0 })

// Layout: BFS concentric rings for expand mode
;(function computeDrillLayout() {
  const nodes = props.subgraphNodes
  if (!nodes.length) return

  // Find anchor (source node) and build adjacency
  const sourceNode = nodes.find((n) => n.type === 'source')
  const anchorId = sourceNode?.id || nodes[0].id
  const adj = new Map<string, string[]>()
  for (const edge of props.subgraphEdges) {
    if (!adj.has(edge.source)) adj.set(edge.source, [])
    if (!adj.has(edge.target)) adj.set(edge.target, [])
    adj.get(edge.source)!.push(edge.target)
    adj.get(edge.target)!.push(edge.source)
  }

  // BFS
  const bfs = new Map<string, number>()
  bfs.set(anchorId, 0)
  const queue = [anchorId]
  while (queue.length) {
    const cur = queue.shift()!
    const dist = bfs.get(cur)!
    for (const nb of adj.get(cur) || []) {
      if (!bfs.has(nb)) {
        bfs.set(nb, dist + 1)
        queue.push(nb)
      }
    }
  }

  // Position by distance ring
  const distGroups = new Map<number, string[]>()
  for (const [nid, d] of bfs) {
    if (!distGroups.has(d)) distGroups.set(d, [])
    distGroups.get(d)!.push(nid)
  }

  for (const [dist, nodeIds] of distGroups) {
    const total = nodeIds.length
    nodeIds.forEach((nid, localIdx) => {
      const angle = -Math.PI / 2 + (2 * Math.PI * localIdx) / total + dist * 0.22
      const r = dist === 0 ? 0 : dist === 1 ? 285 : 410
      drillLayout.value[nid] = {
        x: 500 + r * Math.cos(angle) * (dist === 0 ? 0 : 1) * 0.95,
        y: 340 + r * Math.sin(angle) * 0.68,
      }
    })
  }
})()

const title = computed(() => {
  if (props.drillMode === 'expand') {
    return props.expandedSource?.source_detail.title || '材料图谱'
  }
  return '思路线'
})

const transformStyle = computed(() => ({
  transform: `matrix(${zoom.value}, 0, 0, ${zoom.value}, ${pan.value.x}, ${pan.value.y})`,
}))

function drillNodeStyle(nodeId: string) {
  const pos = drillLayout.value[nodeId]
  if (!pos) return {}
  return { left: `${(pos.x / 1000) * 100}%`, top: `${(pos.y / 680) * 100}%` }
}

function drillEdgePath(edge: GraphEdge) {
  const sp = drillLayout.value[edge.source]
  const tp = drillLayout.value[edge.target]
  if (!sp || !tp) return ''
  const dx = tp.x - sp.x, dy = tp.y - sp.y
  const curve = Math.min(70, Math.max(24, Math.sqrt(dx * dx + dy * dy) * 0.16))
  return `M ${sp.x} ${sp.y} C ${sp.x + dx * 0.34 - dy / curve} ${sp.y + dy * 0.34 + dx / curve}, ${sp.x + dx * 0.66 - dy / curve} ${sp.y + dy * 0.66 + dx / curve}, ${tp.x} ${tp.y}`
}

function shortLabel(text: string): string {
  const cleaned = text.replace(/\s+/g, ' ').trim()
  return cleaned.length <= 80 ? cleaned : cleaned.slice(0, 77) + '...'
}

function typeIcon(type: string): string {
  return { source: '口', thought: '◎', task: '◉', project: '◇', question: '?' }[type] || '·'
}

function typeLabel(type: string): string {
  return { source: '材料', thought: '想法', task: '任务', project: '项目', question: '问题' }[type] || type
}

function openSource() {
  const sid = props.expandedSource?.source_detail.id
  if (sid) emit('openSource', sid)
}

function askHere() {
  emit('askHere', '')
}

// Pan & zoom
function startPan(event: PointerEvent) {
  if ((event.target as HTMLElement)?.closest('.paper-graph-node')) return
  panning.value = true
  lastPan.value = { x: event.clientX, y: event.clientY }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

function handlePanMove(event: PointerEvent) {
  if (!panning.value) return
  const dx = event.clientX - lastPan.value.x
  const dy = event.clientY - lastPan.value.y
  lastPan.value = { x: event.clientX, y: event.clientY }
  pan.value = { x: pan.value.x + dx, y: pan.value.y + dy }
}

function endPan() {
  panning.value = false
}

function handleZoom(event: WheelEvent) {
  const container = stageContainer.value
  if (!container) return
  const rect = container.getBoundingClientRect()
  const px = event.clientX - rect.left
  const py = event.clientY - rect.top
  const factor = event.deltaY < 0 ? 1.08 : 0.92
  const newZoom = Math.max(0.55, Math.min(2.2, zoom.value * factor))
  const ratio = newZoom / zoom.value
  pan.value = {
    x: px - ratio * (px - pan.value.x),
    y: py - ratio * (py - pan.value.y),
  }
  zoom.value = newZoom
}
</script>
