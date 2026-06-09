<template>
  <div
    v-if="items.length"
    ref="cloudOrbitElement"
    class="cloud-orbit cloud-constellation"
    :class="{ 'is-cloud-dragging': draggingCloudKey, 'is-cloud-recoiling': cloudRecoilKey, 'is-cloud-returning': cloudReturnKey }"
    aria-label="搜索历史星图"
    tabindex="0"
    @keydown.esc.prevent="clearSearch"
  >
    <form class="cloud-search-row constellation-search" @submit.prevent="emit('submitSearch')">
      <Search :size="17" />
      <input :value="searchQuery" placeholder="搜关键词，匹配的点会亮起来..." @input="updateSearchQuery" />
    </form>

    <svg
      class="cloud-constellation-edges"
      :viewBox="`0 0 ${cloudOrbitSize.width} ${cloudOrbitSize.height}`"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <line
        v-for="edge in cloudConstellationEdges"
        :key="edge.id"
        :x1="edge.x1"
        :y1="edge.y1"
        :x2="edge.x2"
        :y2="edge.y2"
        :class="{ active: edge.active }"
      />
      <circle
        v-if="selectedCloudPoint"
        class="cloud-constellation-core-ring"
        :cx="selectedCloudPoint.x"
        :cy="selectedCloudPoint.y"
        r="74"
      />
    </svg>

    <button
      v-for="(item, index) in items"
      :key="item.key"
      type="button"
      class="cloud-node"
      :class="cloudNodeClasses(item)"
      :style="cloudNodeStyle(item, index)"
      :aria-pressed="selectedCloudKey === item.key"
      :title="item.label"
      @click="selectCloudNode($event, item)"
      @pointerdown.stop="startCloudDrag($event, item)"
      @pointermove.stop="moveCloudDrag($event)"
      @pointerup.stop="endCloudDrag"
      @pointercancel.stop="cancelCloudDrag"
      @lostpointercapture.stop="handleCloudLostPointerCapture($event)"
    >
      <span class="cloud-node-halo" aria-hidden="true"></span>
      <span class="cloud-node-dot" aria-hidden="true"></span>
      <strong>{{ cloudLabel(item.label) }}</strong>
    </button>

    <div
      v-if="selectedCloudKey && selectedCloudItem && selectedCloudPoint"
      class="cloud-focus-label"
      :style="cloudFocusLabelStyle"
    >
      {{ cloudLabel(selectedCloudItem.label) }}
    </div>

    <div class="cloud-helper-pill">相关线索会一起亮起</div>
  </div>

  <div v-else class="cloud-empty-state">
    <strong>还没有匹配的记忆点</strong>
    <p>换一个更宽的词，或者先去“收集”里放入材料。</p>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Search } from 'lucide-vue-next'
import type { CloudItem } from './memoryCloudTypes'

type CloudDragState = {
  key: string
  pointerId: number
  startX: number
  startY: number
  originX: number
  originY: number
  active: boolean
  target: HTMLElement | null
}

type CloudDragFrame = {
  pointerId: number
  clientX: number
  clientY: number
}

type CloudGraphPoint = {
  x: number
  y: number
}

type CloudDragInfluence = {
  x: number
  y: number
  strength: number
}

type CloudGraphEdge = {
  id: string
  x1: number
  y1: number
  x2: number
  y2: number
  active: boolean
}

const CLOUD_DRAG_THRESHOLD = 4
const CLOUD_DRAG_INFLUENCE_PULL = 0.28
const CLOUD_SPRING_RESPONSE = 0.25
const CLOUD_SPRING_DAMPING = 0.6
const CLOUD_SPRING_SETTLE_MS = Math.round(CLOUD_SPRING_RESPONSE * 1000 + CLOUD_SPRING_DAMPING * 120 + 98)
const CLOUD_CLICK_SUPPRESSION_MS = CLOUD_SPRING_SETTLE_MS + 780

const props = defineProps<{
  items: CloudItem[]
  searchQuery: string
  selectedKey: string
}>()

const emit = defineEmits<{
  select: [event: MouseEvent, item: CloudItem]
  'update:searchQuery': [value: string]
  updateSelectedKey: [value: string]
  submitSearch: []
}>()

const cloudOrbitElement = ref<HTMLDivElement | null>(null)
const selectedCloudKey = ref(props.selectedKey)
const cloudDragOffsets = ref<Record<string, { x: number; y: number }>>({})
const cloudRecoilOffsets = ref<Record<string, CloudDragInfluence>>({})
const cloudRecoilKey = ref('')
const cloudReturnKey = ref('')
const draggingCloudKey = ref('')
const activeCloudDrag = ref<CloudDragState | null>(null)
const suppressedCloudClickKey = ref('')
const cloudOrbitSize = ref({ width: 560, height: 420 })

let cloudResizeObserver: ResizeObserver | null = null
let cloudDragListenersAttached = false
let pendingCloudDragFrame: CloudDragFrame | null = null
let cloudDragAnimationFrame = 0
let cloudSpringAnimationFrame = 0
let cloudSpringStartedAt = 0
let cloudSpringEntries: [string, CloudDragInfluence][] = []
let suppressedCloudClickUntil = 0

const cloudGraphPoints = computed<Record<string, CloudGraphPoint>>(() => {
  const next: Record<string, CloudGraphPoint> = {}
  props.items.forEach((item, index) => {
    next[item.key] = cloudGraphPoint(item, index)
  })
  return next
})

const cloudDragInfluenceOffsets = computed<Record<string, CloudDragInfluence>>(() => {
  const activeOffsets = activeCloudDragInfluenceOffsets()
  if (Object.keys(activeOffsets).length) return activeOffsets
  return cloudRecoilOffsets.value
})

const selectedCloudItem = computed(() => {
  if (!selectedCloudKey.value) return null
  return props.items.find((item) => item.key === selectedCloudKey.value) || null
})

const selectedCloudPoint = computed(() => {
  if (!selectedCloudKey.value) return null
  if (!selectedCloudItem.value) return null
  return cloudGraphPoints.value[selectedCloudItem.value.key] || null
})

const cloudFocusLabelStyle = computed(() => {
  const point = selectedCloudPoint.value
  if (!point) return {}
  return {
    left: `${point.x}px`,
    top: `${point.y}px`,
  }
})

const cloudConstellationEdges = computed<CloudGraphEdge[]>(() => {
  const activeDrag = activeCloudDrag.value?.active ? activeCloudDrag.value : null
  const anchor = activeDrag
    ? props.items.find((item) => item.key === activeDrag.key) || selectedCloudItem.value
    : selectedCloudKey.value ? selectedCloudItem.value : null
  const anchorPoint = anchor ? cloudGraphPoints.value[anchor.key] : null
  if (!anchor || !anchorPoint) return []

  const query = normalizeSearchText(props.searchQuery)
  return props.items
    .filter((item) => item.key !== anchor.key)
    .map((item) => {
      const point = cloudGraphPoints.value[item.key]
      return {
        item,
        point,
        score: cloudAffinityScore(anchor, item, query),
      }
    })
    .filter((entry) => entry.point && entry.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 7)
    .map(({ item, point }) => ({
      id: `${anchor.key}->${item.key}`,
      x1: anchorPoint.x,
      y1: anchorPoint.y,
      x2: point.x,
      y2: point.y,
      active: Boolean(activeDrag)
        ? item.key === activeDrag.key || Boolean(cloudDragInfluenceOffsets.value[item.key])
        : isCloudMatch(item) || isCloudMatch(anchor),
    }))
})

watch(
  () => props.selectedKey,
  (value) => {
    selectedCloudKey.value = value
  },
)

watch(
  () => props.items,
  (items) => {
    if (!items.length) {
      updateSelectedCloudKey('')
      return
    }
    if (!items.some((item) => item.key === selectedCloudKey.value)) {
      updateSelectedCloudKey('')
    }
  },
  { immediate: true },
)

watch(cloudOrbitElement, (element, previous) => {
  if (previous) cloudResizeObserver?.unobserve(previous)
  if (!element) return
  cloudResizeObserver?.observe(element)
  syncCloudOrbitSize()
}, { flush: 'post' })

onMounted(() => {
  cloudResizeObserver = new ResizeObserver(() => syncCloudOrbitSize())
  if (cloudOrbitElement.value) cloudResizeObserver.observe(cloudOrbitElement.value)
  nextTick(syncCloudOrbitSize)
})

onBeforeUnmount(() => {
  cloudResizeObserver?.disconnect()
  clearPendingCloudDragFrame()
  clearCloudRecoil()
  clearCloudReturn()
  cancelCloudDrag()
})

function updateSearchQuery(event: Event) {
  const target = event.target as HTMLInputElement | null
  emit('update:searchQuery', target?.value || '')
}

function clearSearch() {
  emit('update:searchQuery', '')
}

function updateSelectedCloudKey(key: string) {
  selectedCloudKey.value = key
  emit('updateSelectedKey', key)
}

function activeCloudDragInfluenceOffsets() {
  const drag = activeCloudDrag.value
  if (!drag?.active) return {}

  const anchorIndex = props.items.findIndex((item) => item.key === drag.key)
  const anchor = props.items[anchorIndex]
  if (!anchor) return {}

  const anchorOffset = cloudDragOffsets.value[drag.key] || { x: drag.originX, y: drag.originY }
  const deltaX = anchorOffset.x - drag.originX
  const deltaY = anchorOffset.y - drag.originY
  if (Math.hypot(deltaX, deltaY) < 1) return {}

  const query = normalizeSearchText(props.searchQuery)
  const entries = props.items.flatMap((item, index) => {
    if (item.key === drag.key) return []
    const strength = cloudElasticInfluence(anchor, item, query, anchorIndex, index)
    if (strength <= 0) return []
    return [[item.key, {
      x: roundCloudMotion(deltaX * strength * CLOUD_DRAG_INFLUENCE_PULL),
      y: roundCloudMotion(deltaY * strength * CLOUD_DRAG_INFLUENCE_PULL),
      strength,
    }] as const]
  })
  return Object.fromEntries(entries.sort(([, left], [, right]) => right.strength - left.strength).slice(0, 6))
}

function syncCloudOrbitSize() {
  const element = cloudOrbitElement.value
  if (!element) return
  const rect = element.getBoundingClientRect()
  cloudOrbitSize.value = {
    width: Math.max(320, Math.round(element.clientWidth || rect.width)),
    height: Math.max(320, Math.round(element.clientHeight || rect.height)),
  }
}

function cloudGraphPoint(item: CloudItem, index: number) {
  const base = cloudNodeBasePosition(index)
  const dragOffset = cloudRenderOffset(item.key)
  const width = cloudOrbitSize.value.width
  const height = cloudOrbitSize.value.height
  return {
    x: roundCloudMotion((base.left / 100) * width + dragOffset.x),
    y: roundCloudMotion((base.top / 100) * height + dragOffset.y),
  }
}

function cloudRenderOffset(key: string) {
  const persisted = cloudDragOffsets.value[key] || { x: 0, y: 0 }
  const influence = cloudInfluenceOffset(key)
  const springOwnsOffset = Boolean(cloudReturnKey.value || cloudRecoilKey.value) && Boolean(cloudDragOffsets.value[key])
  return {
    x: roundCloudMotion(persisted.x + (springOwnsOffset ? 0 : influence.x)),
    y: roundCloudMotion(persisted.y + (springOwnsOffset ? 0 : influence.y)),
  }
}

function cloudInfluenceOffset(key: string) {
  return cloudDragInfluenceOffsets.value[key] || { x: 0, y: 0, strength: 0 }
}

function roundCloudMotion(value: number) {
  if (Math.abs(value) < 0.01) return 0
  return Number(value.toFixed(2))
}

function cloudNodeBasePosition(index: number) {
  const positions = [
    [50, 50],
    [43, 36],
    [58, 35],
    [39, 62],
    [61, 62],
    [33, 49],
    [69, 49],
    [50, 26],
    [50, 72],
    [28, 34],
    [72, 34],
    [30, 74],
    [72, 74],
    [41, 23],
    [59, 24],
    [42, 78],
    [61, 77],
    [24, 53],
  ]
  const [left, top] = positions[index % positions.length]
  return { left, top }
}

function isCloudMatch(item: CloudItem) {
  const query = normalizeSearchText(props.searchQuery)
  return !query || cloudSearchText(item).includes(query)
}

function cloudAffinityScore(anchor: CloudItem, candidate: CloudItem, query: string) {
  let score = 0
  if (anchor.kind === candidate.kind) score += 2
  if (anchor.tone === candidate.tone) score += 1
  if (anchor.sourceId && anchor.sourceId === candidate.sourceId) score += 5
  if (anchor.nodeId && anchor.nodeId === candidate.nodeId) score += 4
  if (query && cloudSearchText(candidate).includes(query)) score += 6
  score += sharedCloudEvidenceCount(anchor, candidate) * 4
  score += Math.min(3, candidate.weight / 3)
  return score
}

function cloudElasticInfluence(
  anchor: CloudItem,
  candidate: CloudItem,
  query: string,
  anchorIndex: number,
  candidateIndex: number,
) {
  const anchorBase = cloudNodeBasePosition(anchorIndex)
  const candidateBase = cloudNodeBasePosition(candidateIndex)
  const distanceX = ((candidateBase.left - anchorBase.left) / 100) * cloudOrbitSize.value.width
  const distanceY = ((candidateBase.top - anchorBase.top) / 100) * cloudOrbitSize.value.height
  const distance = Math.hypot(distanceX, distanceY)
  const influenceRadius = Math.max(220, Math.min(cloudOrbitSize.value.width, cloudOrbitSize.value.height) * 0.72)
  const distancePull = Math.max(0, 1 - distance / influenceRadius)
  const affinity = cloudAffinityScore(anchor, candidate, query)
  const semanticPull = Math.min(0.22, Math.max(0, affinity - 2) / 32)
  const evidencePull = sharedCloudEvidenceCount(anchor, candidate) > 0 ? 0.1 : 0
  const sourcePull = anchor.sourceId && anchor.sourceId === candidate.sourceId ? 0.12 : 0
  const searchPull = query && cloudSearchText(candidate).includes(query) ? 0.08 : 0
  const kindPull = anchor.kind === candidate.kind ? 0.04 : 0
  const strength = Math.min(0.38, distancePull * 0.2 + semanticPull + evidencePull + sourcePull + searchPull + kindPull)
  return strength >= 0.12 ? Number(strength.toFixed(3)) : 0
}

function sharedCloudEvidenceCount(left: CloudItem, right: CloudItem) {
  const rightIds = new Set(right.evidenceTitles.map((item) => item.id))
  return left.evidenceTitles.filter((item) => rightIds.has(item.id)).length
}

function selectCloudNode(event: MouseEvent, item: CloudItem) {
  if (shouldSuppressCloudClick(item)) {
    event.preventDefault()
    return
  }
  updateSelectedCloudKey(item.key)
  emit('select', event, item)
}

function shouldSuppressCloudClick(item: CloudItem) {
  const now = performanceNow()
  if (suppressedCloudClickKey.value && now >= suppressedCloudClickUntil) {
    suppressedCloudClickKey.value = ''
    suppressedCloudClickUntil = 0
  }
  return suppressedCloudClickKey.value === item.key && now < suppressedCloudClickUntil
}

function suppressCloudClick(key: string) {
  suppressedCloudClickKey.value = key
  suppressedCloudClickUntil = performanceNow() + CLOUD_CLICK_SUPPRESSION_MS
  window.setTimeout(() => {
    if (suppressedCloudClickKey.value === key && performanceNow() >= suppressedCloudClickUntil) {
      suppressedCloudClickKey.value = ''
      suppressedCloudClickUntil = 0
    }
  }, CLOUD_CLICK_SUPPRESSION_MS)
}

function performanceNow() {
  return window.performance?.now?.() ?? Date.now()
}

function startCloudDrag(event: PointerEvent, item: CloudItem) {
  if (event.button !== 0) return
  if ('isPrimary' in event && !event.isPrimary) return
  beginCloudDrag(event, item, event.pointerId)
  const drag = activeCloudDrag.value
  if (drag?.pointerId === event.pointerId) {
    drag.target?.setPointerCapture?.(event.pointerId)
  }
}

function beginCloudDrag(event: PointerEvent, item: CloudItem, pointerId: number) {
  clearCloudRecoil()
  clearPendingCloudDragFrame()
  clearCloudDragOffsets()
  const existing = cloudDragOffsets.value[item.key] || { x: 0, y: 0 }
  const target = event.currentTarget instanceof HTMLElement ? event.currentTarget : null
  selectedCloudKey.value = item.key
  emit('updateSelectedKey', item.key)
  activeCloudDrag.value = {
    key: item.key,
    pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: existing.x,
    originY: existing.y,
    active: false,
    target,
  }
  attachCloudDragListeners()
}

function moveCloudDrag(event: PointerEvent) {
  moveCloudDragFrame(event, event.pointerId)
}

function moveCloudDragFrame(event: PointerEvent, pointerId: number) {
  const drag = activeCloudDrag.value
  if (!drag || drag.pointerId !== pointerId) return
  event.preventDefault()
  pendingCloudDragFrame = {
    pointerId,
    clientX: event.clientX,
    clientY: event.clientY,
  }
  if (!cloudDragAnimationFrame) {
    cloudDragAnimationFrame = window.requestAnimationFrame(applyPendingCloudDragFrame)
  }
}

function applyPendingCloudDragFrame() {
  cloudDragAnimationFrame = 0
  const frame = pendingCloudDragFrame
  pendingCloudDragFrame = null
  if (!frame) return

  const drag = activeCloudDrag.value
  if (!drag || drag.pointerId !== frame.pointerId) return

  const deltaX = frame.clientX - drag.startX
  const deltaY = frame.clientY - drag.startY
  if (!drag.active && Math.hypot(deltaX, deltaY) >= CLOUD_DRAG_THRESHOLD) {
    drag.active = true
    draggingCloudKey.value = drag.key
  }

  if (!drag.active) return
  cloudDragOffsets.value = {
    [drag.key]: {
      x: roundCloudMotion(drag.originX + deltaX),
      y: roundCloudMotion(drag.originY + deltaY),
    },
  }
}

function endCloudDrag(event: PointerEvent) {
  finishCloudDrag(event, event.pointerId)
}

function finishCloudDrag(event: PointerEvent, pointerId: number) {
  const drag = activeCloudDrag.value
  if (!drag || drag.pointerId !== pointerId) return
  flushPendingCloudDragFrame()
  const releaseOffsets = drag.active ? captureCloudReleaseOffsets(drag.key) : {}
  detachCloudDragListeners()
  const wasActive = drag.active
  activeCloudDrag.value = null
  draggingCloudKey.value = ''
  releaseCloudPointer(drag, pointerId)
  if (wasActive) {
    startCloudSpringReturn(drag.key, releaseOffsets)
    suppressCloudClick(drag.key)
    return
  }
}

function cancelCloudDrag(event?: PointerEvent) {
  const drag = activeCloudDrag.value
  const releaseOffsets = drag?.active ? captureCloudReleaseOffsets(drag.key) : {}
  detachCloudDragListeners()
  clearPendingCloudDragFrame()
  activeCloudDrag.value = null
  draggingCloudKey.value = ''
  if (drag) releaseCloudPointer(drag, event?.pointerId ?? drag.pointerId)
  if (drag?.active) {
    startCloudSpringReturn(drag.key, releaseOffsets)
  }
}

function handleCloudLostPointerCapture(event: PointerEvent) {
  const drag = activeCloudDrag.value
  if (!drag || drag.pointerId !== event.pointerId) return
  cancelCloudDrag(event)
}

function attachCloudDragListeners() {
  if (cloudDragListenersAttached) return
  window.addEventListener('pointermove', moveCloudDrag)
  window.addEventListener('pointerup', endCloudDrag)
  window.addEventListener('pointercancel', cancelCloudDrag)
  cloudDragListenersAttached = true
}

function detachCloudDragListeners() {
  if (!cloudDragListenersAttached) return
  window.removeEventListener('pointermove', moveCloudDrag)
  window.removeEventListener('pointerup', endCloudDrag)
  window.removeEventListener('pointercancel', cancelCloudDrag)
  cloudDragListenersAttached = false
}

function releaseCloudPointer(drag: CloudDragState, pointerId: number) {
  if (!drag.target?.hasPointerCapture?.(pointerId)) return
  drag.target.releasePointerCapture(pointerId)
}

function flushPendingCloudDragFrame() {
  if (cloudDragAnimationFrame) {
    window.cancelAnimationFrame(cloudDragAnimationFrame)
    cloudDragAnimationFrame = 0
  }
  applyPendingCloudDragFrame()
}

function clearPendingCloudDragFrame() {
  if (cloudDragAnimationFrame) {
    window.cancelAnimationFrame(cloudDragAnimationFrame)
    cloudDragAnimationFrame = 0
  }
  pendingCloudDragFrame = null
}

function captureCloudReleaseOffsets(anchorKey: string) {
  const next: Record<string, CloudDragInfluence> = {}
  const activeOffsets = cloudDragInfluenceOffsets.value
  for (const item of props.items) {
    const offset = cloudRenderOffset(item.key)
    if (Math.hypot(offset.x, offset.y) < 0.5) continue
    const influence = activeOffsets[item.key]
    const strength = item.key === anchorKey ? 1 : Math.max(0.08, influence?.strength || 0.12)
    next[item.key] = {
      x: offset.x,
      y: offset.y,
      strength,
    }
  }
  return next
}

function startCloudSpringReturn(key: string, offsets: Record<string, CloudDragInfluence>) {
  clearCloudRecoil()
  clearCloudReturn()
  const entries = Object.entries(offsets).filter(([, offset]) => Math.hypot(offset.x, offset.y) >= 0.5)
  if (!entries.length) {
    clearCloudDragOffsets()
    return
  }
  cloudRecoilKey.value = key
  cloudReturnKey.value = key
  cloudSpringEntries = entries
  cloudSpringStartedAt = performanceNow()
  cloudDragOffsets.value = Object.fromEntries(
    entries.map(([entryKey, offset]) => [entryKey, { x: offset.x, y: offset.y }]),
  )
  cloudRecoilOffsets.value = Object.fromEntries(entries)
  cloudSpringAnimationFrame = window.requestAnimationFrame(stepCloudSpringReturn)
}

function stepCloudSpringReturn(now = performanceNow()) {
  cloudSpringAnimationFrame = 0
  if (!cloudSpringEntries.length) {
    finishCloudSpringReturn()
    return
  }
  const elapsedSeconds = Math.max(0, (now - cloudSpringStartedAt) / 1000)
  const multiplier = cloudSpringReturnMultiplier(elapsedSeconds)
  const nextOffsets: Record<string, { x: number; y: number }> = {}
  const nextRecoil: Record<string, CloudDragInfluence> = {}
  let maxDistance = 0

  for (const [entryKey, offset] of cloudSpringEntries) {
    const x = roundCloudMotion(offset.x * multiplier)
    const y = roundCloudMotion(offset.y * multiplier)
    maxDistance = Math.max(maxDistance, Math.hypot(x, y))
    nextOffsets[entryKey] = { x, y }
    nextRecoil[entryKey] = { x, y, strength: offset.strength }
  }

  cloudDragOffsets.value = nextOffsets
  cloudRecoilOffsets.value = nextRecoil

  if (elapsedSeconds >= CLOUD_SPRING_SETTLE_MS / 1000 || maxDistance < 0.35) {
    finishCloudSpringReturn()
    return
  }
  cloudSpringAnimationFrame = window.requestAnimationFrame(stepCloudSpringReturn)
}

function cloudSpringReturnMultiplier(elapsedSeconds: number) {
  const decay = Math.exp(-7.4 * elapsedSeconds)
  return Number((decay * Math.cos(18 * elapsedSeconds)).toFixed(4))
}

function finishCloudSpringReturn() {
  if (cloudSpringAnimationFrame) {
    window.cancelAnimationFrame(cloudSpringAnimationFrame)
    cloudSpringAnimationFrame = 0
  }
  cloudSpringEntries = []
  cloudSpringStartedAt = 0
  clearCloudDragOffsets()
  cloudRecoilOffsets.value = {}
  cloudRecoilKey.value = ''
  cloudReturnKey.value = ''
}

function clearCloudReturn() {
  if (cloudSpringAnimationFrame) {
    window.cancelAnimationFrame(cloudSpringAnimationFrame)
    cloudSpringAnimationFrame = 0
  }
  cloudSpringEntries = []
  cloudSpringStartedAt = 0
  cloudReturnKey.value = ''
}

function clearCloudDragOffsets() {
  cloudDragOffsets.value = {}
}

function clearCloudRecoil() {
  clearCloudReturn()
  cloudRecoilOffsets.value = {}
  cloudRecoilKey.value = ''
}

function cloudSearchText(item: CloudItem) {
  return normalizeSearchText([
    item.label,
    item.detail,
    item.kindLabel,
    ...item.evidenceTitles.map((source) => source.title),
  ].join(' '))
}

function normalizeSearchText(value: string) {
  return value.toLowerCase().replace(/\s+/g, ' ').trim()
}

function cloudLabel(label: string) {
  const cleaned = label.replace(/\s+/g, ' ').trim()
  return cleaned.length > 36 ? `${cleaned.slice(0, 34)}...` : cleaned
}

function cloudNodeClasses(item: CloudItem) {
  return [
    item.tone,
    `cloud-kind-${item.kind}`,
    {
      selected: selectedCloudKey.value === item.key,
      matched: isCloudMatch(item),
      dimmed: !isCloudMatch(item),
      'is-dragging': draggingCloudKey.value === item.key,
      'is-linked': Boolean(cloudDragInfluenceOffsets.value[item.key]),
      'is-recoiling': Boolean(cloudRecoilOffsets.value[item.key]),
      'is-returning': cloudReturnKey.value === item.key,
      'is-large': item.weight >= 6,
      'is-small': item.weight <= 3,
    },
  ]
}

function cloudNodeStyle(item: CloudItem, index: number) {
  const size = Math.max(22, Math.min(30, 17 + item.weight * 1.45))
  const influence = cloudInfluenceOffset(item.key)
  const point = cloudGraphPoint(item, index)
  return {
    '--cloud-x': `${point.x}px`,
    '--cloud-y': `${point.y}px`,
    '--cloud-size': `${size}px`,
    '--cloud-half-size': `${roundCloudMotion(size / 2)}px`,
    '--cloud-link-strength': `${influence.strength}`,
    '--cloud-linked-scale': `${roundCloudMotion(1.01 + influence.strength * 0.06)}`,
    '--cloud-orbit-delay': `${-0.2 * (index % 9)}s`,
  }
}
</script>
