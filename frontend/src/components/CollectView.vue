<template>
  <section id="view-collect" class="view collect-view redesign-collect-view active" :class="{ 'has-receipt': receiptVisible }">
    <div class="eyebrow">收下 · TAKE IT IN</div>
    <h1 class="title">带着理由，收下一份</h1>
    <p class="lede">截图、PDF、网页或一段话。解析、摘要、连线都交给系统——你只负责<em>停五秒，留一句为什么</em>。</p>

    <div class="rule"></div>

    <div class="collect-grid">
      <div id="bigcard" class="bigcard" :class="{ flying: busy }" @dragover.prevent @drop.prevent="onDrop">
        <input
          ref="fileInput"
          class="file-input"
          type="file"
          multiple
          accept=".md,.markdown,.txt,.html,.htm,.pdf,.png,.jpg,.jpeg,.webp,.gif"
          @change="onFileSelected"
        />

        <button v-if="!files.length" id="dz" class="dz" type="button" :disabled="busy" @click="fileInput?.click()">
          <span class="big">拖进来，或点击选择</span>
          也可以直接粘贴一段网页摘录、对话或想法
        </button>

        <div v-else id="filled" class="filled show">
          <span v-for="file in files" :key="file.name + file.size" class="file-chip">
            <span class="ftype">{{ fileType(file.name) }}</span>{{ file.name }}
            <span class="f-meta">{{ formatFileSize(file.size) }} · 待备份到本地</span>
          </span>
          <button class="btn-ghost" type="button" :disabled="busy" @click="files = []">重新选择</button>
        </div>

        <div class="receipt-field paste-field">
          <label for="collectText">也可以直接贴一段材料</label>
          <textarea
            id="collectText"
            ref="textInput"
            v-model="text"
            placeholder="网页摘录、对话、灵感、会议纪要都可以。"
          />
        </div>

        <div class="receipt-field">
          <label for="receiptInput">给两周后的你，留一句话</label>
          <textarea
            id="receiptInput"
            v-model="why"
            placeholder="为什么是它？——这句话会一字不改，还给未来的你。"
          />
          <div class="fineprint">留空也行。系统不会替你写。</div>
        </div>

        <div class="card-foot">
          <span class="foot-lbl">放到</span>
          <button
            v-for="item in routeOptions"
            :key="item.id"
            type="button"
            class="chip"
            :class="{ on: routeMode === item.id }"
            :disabled="busy"
            @click="routeMode = item.id"
          >
            {{ item.label }}
          </button>
          <select v-if="routeMode === 'manual'" v-model="spaceId" class="paper-select" :disabled="busy">
            <option v-for="space in routableSpaces" :key="space.id" :value="space.id">{{ spaceDisplayName(space) }}</option>
          </select>
          <span class="spacer"></span>
          <button id="saveBtn" class="btn btn-ink" :disabled="busy || !canSubmit" @click="submit">收　下</button>
        </div>
      </div>

      <div class="stackbox">
        <div class="ministack">
          <div class="mini m1"></div>
          <div class="mini m2"></div>
          <div class="mini m3"></div>
        </div>
        <div class="n" id="stackN">{{ memoryCount }}</div>
        <div class="t">份可找回的记忆</div>
      </div>
    </div>

    <section v-if="showProgress" class="web-block ingest-progress">
      <div class="wb-head">
        <span class="tag tag-web">正在入库</span>
        <span class="wb-note">{{ progressTitle }}</span>
      </div>
      <div class="deep-stage-list">
        <span
          v-for="step in ingestSteps"
          :key="step.id"
          :class="['deep-stage-pill', `is-${step.status}`]"
        >
          {{ step.label }}
        </span>
      </div>
    </section>

    <section v-if="activeReceipt && receiptVisible" class="receipt-lg memory-receipt collect-receipt">
      <div class="head">
        <span class="tag tag-moss">{{ batchReceiptVisible ? '本批次回执' : '已收下' }}</span>
        <span class="when">{{ receiptSpaceLabel }} · {{ props.results.length }} 份材料</span>
      </div>
      <div class="quote">「{{ saveReasonText || systemUnderstanding }}」</div>
      <div class="src">
        <span>{{ receiptTitle }}</span>
        <button class="open source-link-button" type="button" @click="askBatch">追问这批材料 ↗</button>
        <button class="open source-link-button" type="button" :disabled="!canOpenSpace" @click="openSpace">去书架 ↗</button>
      </div>
      <details class="evidence">
        <summary>查看材料详情</summary>
        <div class="body">
          <p>{{ receiptDetailText }}</p>
          <div v-if="batchSourcePreview.length" class="batch-source-list">
            <span v-for="item in batchSourcePreview" :key="item.source_id">{{ item.title }}</span>
          </div>
          <button class="btn-ghost" type="button" @click="continueCollect">继续收下下一份</button>
        </div>
      </details>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { CollectPayload, GraphSpace, IngestResponse, RouteMode } from '../types'

type SubmittedSnapshot = {
  why: string
  routeMode: RouteMode
  spaceId: string
  itemCount: number
}
type ProgressStatus = 'pending' | 'active' | 'done'
type ProgressStep = {
  id: string
  label: string
  detail: string
  status: ProgressStatus
}

const props = defineProps<{
  busy: boolean
  spaces: GraphSpace[]
  results: IngestResponse[]
}>()

const emit = defineEmits<{
  collect: [payload: CollectPayload]
  openSpace: [spaceId: string]
  askBatch: [question: string]
  updateTitle: [sourceId: string, title: string]
}>()

const text = ref('')
const why = ref('')
const files = ref<File[]>([])
const routeMode = ref<RouteMode>('auto')
const spaceId = ref('default')
const fileInput = ref<HTMLInputElement | null>(null)
const textInput = ref<HTMLTextAreaElement | null>(null)
const lastSubmitted = ref<SubmittedSnapshot | null>(null)
const hiddenReceiptSourceId = ref('')
const simulatedStepIndex = ref(0)

const STEP_DEFINITIONS = [
  { id: 'extract', label: '提取内容', detail: '把材料转成可整理文本' },
  { id: 'summary', label: '生成摘要', detail: '整理出回看时需要的一句话' },
  { id: 'reason', label: '保存理由', detail: '保留你的原话或标明 AI 猜测' },
  { id: 'space', label: '放入空间', detail: '判断它先进入哪里' },
  { id: 'connect', label: '寻找连接', detail: '看看它和旧材料能否接上' },
] as const
const routeOptions = [
  { id: 'auto' as const, label: '让 AI 放' },
  { id: 'manual' as const, label: '手动选' },
  { id: 'inbox' as const, label: '先放待整理' },
]
const RECEIPT_UNDERSTANDING_FALLBACK = '这份材料已经被保存，并可作为之后找回相关判断的线索。'

let progressTimer: ReturnType<typeof setInterval> | null = null

const routableSpaces = computed(() => props.spaces.filter((space) => space.status === 'active' && space.id !== 'inbox'))
const canSubmit = computed(() => Boolean(text.value.trim() || files.value.length))
const showProgress = computed(() => props.busy && Boolean(lastSubmitted.value))
const progressTitle = computed(() => {
  const count = lastSubmitted.value?.itemCount || 1
  return count > 1 ? `正在理解这 ${count} 份材料` : '系统正在理解这份材料'
})
const ingestSteps = computed<ProgressStep[]>(() => STEP_DEFINITIONS.map((step, index) => ({
  ...step,
  status: index < simulatedStepIndex.value ? 'done' : index === simulatedStepIndex.value ? 'active' : 'pending',
})))
const activeReceipt = computed(() => props.results[0] || null)
const receiptVisible = computed(() => Boolean(activeReceipt.value) && activeReceipt.value?.source_id !== hiddenReceiptSourceId.value)
const batchReceiptVisible = computed(() => props.results.length > 1 && receiptVisible.value)
const batchSourcePreview = computed(() => props.results.slice(0, 4))
const batchQuestion = computed(() => '结合刚才上传的这批材料，我们下一步最应该优先完善什么？')
const memoryCount = computed(() => Math.max(312, props.results.length + props.spaces.reduce((sum, space) => sum + (space.source_count || 0), 0)))
const currentEvidenceCard = computed(() => {
  const receipt = activeReceipt.value
  if (!receipt) return null
  return receipt.focus_graph.evidence_cards.find((card) => card.source_id === receipt.source_id) || receipt.focus_graph.evidence_cards[0] || null
})
const receiptTitle = computed(() => activeReceipt.value?.title?.trim() || '新的材料')
const saveReasonText = computed(() => {
  const userReason = lastSubmitted.value?.why.trim()
  if (userReason) return userReason
  return currentEvidenceCard.value?.why_saved?.trim() || ''
})
const receiptSpaceLabel = computed(() => resultSpaceLabel(activeReceipt.value) || '待整理')
const systemUnderstanding = computed(() => getReceiptUnderstanding(activeReceipt.value?.summary || '', receiptTitle.value))
const canOpenSpace = computed(() => Boolean(activeReceipt.value?.graph_space_id))
const receiptDetailText = computed(() => {
  const excerpt = currentEvidenceCard.value?.source_excerpt?.trim()
  const summary = activeReceipt.value?.summary?.trim()
  return excerpt || summary || '这份材料已经保存，暂时还没有可以展示的摘录。'
})

watch(showProgress, (active) => {
  if (active) startProgress()
  else stopProgress()
}, { immediate: true })

watch(
  () => activeReceipt.value?.source_id,
  (sourceId, previous) => {
    if (sourceId && sourceId !== previous) hiddenReceiptSourceId.value = ''
  },
)

onBeforeUnmount(() => {
  stopProgress()
})

function submit() {
  if (!canSubmit.value) return
  lastSubmitted.value = {
    why: why.value,
    routeMode: routeMode.value,
    spaceId: spaceId.value,
    itemCount: files.value.length + (text.value.trim() ? 1 : 0),
  }
  hiddenReceiptSourceId.value = ''
  emit('collect', {
    text: text.value,
    files: files.value,
    why: why.value,
    routeMode: routeMode.value,
    spaceId: spaceId.value,
  })
  text.value = ''
  why.value = ''
  files.value = []
}

function startProgress() {
  stopProgress()
  simulatedStepIndex.value = 0
  progressTimer = setInterval(() => {
    simulatedStepIndex.value = Math.min(simulatedStepIndex.value + 1, STEP_DEFINITIONS.length - 1)
  }, 850)
}

function stopProgress() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

function openSpace() {
  const space = activeReceipt.value?.graph_space_id
  if (!space) return
  emit('openSpace', space)
}

function askBatch() {
  emit('askBatch', batchQuestion.value)
}

async function continueCollect() {
  if (activeReceipt.value) hiddenReceiptSourceId.value = activeReceipt.value.source_id
  await nextTick()
  textInput.value?.focus()
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  files.value = [...files.value, ...Array.from(input.files || [])]
  input.value = ''
}

function onDrop(event: DragEvent) {
  const dropped = Array.from(event.dataTransfer?.files || [])
  if (dropped.length) files.value = [...files.value, ...dropped]
  const droppedText = event.dataTransfer?.getData('text/plain')
  if (droppedText) text.value = [text.value, droppedText].filter(Boolean).join('\n')
}

function fileType(name: string) {
  const ext = name.split('.').pop()?.toUpperCase() || 'FILE'
  return ext.slice(0, 4)
}

function formatFileSize(size: number) {
  if (!size) return '待保存'
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function spaceDisplayName(space: GraphSpace) {
  if (space.id === 'inbox') return '待整理'
  if (space.id === 'default') return '主记忆'
  return space.name
}

function friendlySpaceName(spaceId?: string) {
  if (!spaceId) return ''
  const matched = props.spaces.find((space) => space.id === spaceId)
  if (matched) return spaceDisplayName(matched)
  if (spaceId === 'default') return '主记忆'
  if (spaceId === 'inbox') return '待整理'
  return spaceId
}

function resultSpaceLabel(result?: IngestResponse | null) {
  if (!result) return ''
  return normalizeBuiltInSpaceName(result.space_name) || friendlySpaceName(result.graph_space_id)
}

function normalizeBuiltInSpaceName(name?: string) {
  if (!name) return ''
  const normalized = name.trim().toLowerCase()
  if (normalized === 'inbox') return '待整理'
  if (normalized === 'default') return '主记忆'
  return name
}

function getReceiptUnderstanding(summary: string, title: string) {
  const normalizedSummary = normalizeReceiptSummary(summary)
  if (!normalizedSummary) return RECEIPT_UNDERSTANDING_FALLBACK
  if (isRedundantReceiptSummary(normalizedSummary, title)) return RECEIPT_UNDERSTANDING_FALLBACK
  return normalizedSummary
}

function normalizeReceiptSummary(summary: string) {
  return summary
    .replace(/\b(?:source_id|routing_suggestion|focus_graph|why_saved_status|user_stated|ai_inferred|AI-inferred|ai-inferred)\b\s*[:：]?\s*[\w-]*/gi, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function isRedundantReceiptSummary(summary: string, title: string) {
  const comparableSummary = comparableText(summary)
  const comparableTitle = comparableText(title)
  if (!comparableSummary) return true
  if (comparableSummary.length < 20) return true
  if (!comparableTitle) return false
  if (comparableSummary === comparableTitle) return true
  if (comparableSummary.startsWith(comparableTitle) && comparableSummary.length <= comparableTitle.length + 24) return true
  return similarityScore(comparableSummary, comparableTitle) >= 0.82
}

function comparableText(text: string) {
  return text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '')
}

function similarityScore(a: string, b: string) {
  const gramsA = characterNgrams(a)
  const gramsB = characterNgrams(b)
  if (!gramsA.size || !gramsB.size) return 0
  let overlap = 0
  for (const gram of gramsA) {
    if (gramsB.has(gram)) overlap += 1
  }
  return (2 * overlap) / (gramsA.size + gramsB.size)
}

function characterNgrams(text: string, size = 3) {
  if (text.length <= size) return new Set([text])
  const grams = new Set<string>()
  for (let index = 0; index <= text.length - size; index += 1) {
    grams.add(text.slice(index, index + size))
  }
  return grams
}
</script>
