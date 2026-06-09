<template>
  <section class="global-source-map">
    <header class="source-map-head">
      <div>
        <p class="eyebrow">全局源地图</p>
        <h2>{{ space?.name }} — 材料全景</h2>
        <p>每个卡片是你放入的一个材料。点击展开它的局部图谱；选中两个以上可追踪思路线。</p>
      </div>
    </header>

    <div
      ref="stageContainer"
      class="graph-stage source-map-stage"
      @pointerdown="startPan"
      @pointermove="handlePanMove"
      @pointerup="endPan"
      @pointerleave="endPan"
      @wheel.prevent="handleZoom"
    >
      <div class="graph-map-layer" :style="transformStyle">
        <svg
          v-if="syntheticEdges.length"
          class="graph-stage-edges"
          viewBox="0 0 1000 680"
          preserveAspectRatio="none"
        >
          <g v-for="edge in syntheticEdges" :key="edge.id">
            <path
              :d="edgePathString(edge)"
              class="source-map-edge"
              :title="edge.reason"
            />
            <text
              :x="edgeMidpoint(edge).x"
              :y="edgeMidpoint(edge).y"
              class="source-map-edge-label"
            >{{ edge.reason }}</text>
          </g>
          <defs>
            <marker id="paper-arrow" viewBox="0 0 10 6" refX="9" refY="3" markerWidth="8" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 8 3 L 0 5" fill="none" stroke="rgba(77,61,42,0.42)" />
            </marker>
          </defs>
        </svg>

        <button
          v-for="source in sources"
          :key="source.node.id"
          class="source-map-node"
          :class="{
            selected: selectedIds.has(source.node.id),
            expanded: expandedIds.includes(source.node.id),
          }"
          :style="positionStyle(source.node.id)"
          @click.stop="handleClick(source, $event)"
        >
          <span class="source-node-title">{{ source.source_detail.title || source.node.label }}</span>
          <span class="source-node-meta">
            <span class="source-stat">{{ source.thought_count }} 想法</span>
            <span v-if="source.task_count" class="source-stat">{{ source.task_count }} 任务</span>
            <span v-if="source.project_name" class="source-stat source-project">{{ source.project_name }}</span>
          </span>
          <span
            class="source-status-badge"
            :class="source.source_detail.why_saved_status === 'user-stated' ? 'tone-user' : 'tone-ai'"
          >
            {{ source.source_detail.why_saved_status === 'user-stated' ? '用户原话' : 'AI推断' }}
          </span>
        </button>
      </div>
    </div>

    <footer class="source-map-actions">
      <span class="selection-hint">{{ selectionText }}</span>
      <div class="source-map-action-btns">
        <button
          class="primary-button"
          :disabled="selectedIds.size < 2"
          @click="traceSelected"
        >追踪思路线</button>
        <button
          class="ghost-button"
          :disabled="!selectedIds.size"
          @click="clear"
        >清空选择</button>
      </div>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SyntheticEdge, SourceMapEntry, GraphSpace } from '../types'

const props = defineProps<{
  space: GraphSpace | null
  sources: SourceMapEntry[]
  syntheticEdges: SyntheticEdge[]
  expandedIds: string[]
}>()

const emit = defineEmits<{
  expandSource: [sourceId: string]
  traceThread: [sourceIds: string[]]
}>()

const stageContainer = ref<HTMLDivElement | null>(null)
const selectedIds = ref<Set<string>>(new Set())
const nodeLayout = ref<Record<string, { x: number; y: number }>>({})
const zoom = ref(1)
const pan = ref({ x: 0, y: 0 })
const panning = ref(false)
const lastPan = ref({ x: 0, y: 0 })

// Layout: grid with deterministic jitter
;(function computeLayout() {
  const items = props.sources
  const total = items.length || 1
  const cols = Math.ceil(Math.sqrt(total * 1.5))
  const cellW = 900 / cols
  const cellH = 600 / Math.ceil(total / cols)
  items.forEach((source, i) => {
    const col = i % cols
    const row = Math.floor(i / cols)
    const jx = pseudoRandom(source.node.id, 0) * 36 - 18
    const jy = pseudoRandom(source.node.id, 1) * 24 - 12
    nodeLayout.value[source.node.id] = {
      x: 75 + col * cellW + jx,
      y: 72 + row * cellH + jy,
    }
  })
})()

const transformStyle = computed(() => ({
  transform: `matrix(${zoom.value}, 0, 0, ${zoom.value}, ${pan.value.x}, ${pan.value.y})`,
}))

const selectionText = computed(() => {
  const n = selectedIds.value.size
  if (n) return `已选择 ${n} 个材料`
  return '点击选择材料；Shift+点击可多选'
})

function positionStyle(nodeId: string) {
  const pos = nodeLayout.value[nodeId]
  if (!pos) return {}
  return { left: `${(pos.x / 1000) * 100}%`, top: `${(pos.y / 680) * 100}%` }
}

function edgePathString(edge: SyntheticEdge) {
  const sourcePos = nodeLayout.value[edge.source]
  const targetPos = nodeLayout.value[edge.target]
  if (!sourcePos || !targetPos) return ''
  const sx = sourcePos.x, sy = sourcePos.y
  const tx = targetPos.x, ty = targetPos.y
  const dx = tx - sx, dy = ty - sy
  const curve = Math.min(70, Math.max(24, Math.sqrt(dx * dx + dy * dy) * 0.16))
  return `M ${sx} ${sy} C ${sx + dx * 0.34 - dy / curve} ${sy + dy * 0.34 + dx / curve}, ${sx + dx * 0.66 - dy / curve} ${sy + dy * 0.66 + dx / curve}, ${tx} ${ty}`
}

function edgeMidpoint(edge: SyntheticEdge) {
  const sourcePos = nodeLayout.value[edge.source]
  const targetPos = nodeLayout.value[edge.target]
  if (!sourcePos || !targetPos) return { x: 0, y: 0 }
  return {
    x: (sourcePos.x + targetPos.x) / 2,
    y: (sourcePos.y + targetPos.y) / 2 - 10,
  }
}

function handleClick(source: SourceMapEntry, event: MouseEvent) {
  if (event.shiftKey) {
    const s = new Set(selectedIds.value)
    if (s.has(source.node.id)) s.delete(source.node.id)
    else s.add(source.node.id)
    selectedIds.value = s
    return
  }
  // Single click: expand
  emit('expandSource', source.node.id)
}

function traceSelected() {
  if (selectedIds.value.size < 2) return
  const actualIds = [...selectedIds.value].map((id) =>
    id.startsWith('source_') ? id.slice('source_'.length) : id
  )
  emit('traceThread', actualIds)
}

function clear() {
  selectedIds.value = new Set()
}

// Pan & zoom
function startPan(event: PointerEvent) {
  if ((event.target as HTMLElement)?.closest('.source-map-node')) return
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

function pseudoRandom(seed: string, offset: number): number {
  let hash = 0
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash << 5) - hash) + seed.charCodeAt(i) + offset
    hash |= 0
  }
  return ((hash % 100) + 100) % 100 / 100
}
</script>
