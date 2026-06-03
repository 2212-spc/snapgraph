<template>
  <section class="layer-view collect-view" :class="{ 'has-receipt': receiptVisible }">
    <div class="layer-head">
      <p class="eyebrow">收集</p>
      <h1>带着理由收下一份材料</h1>
      <p>把截图、PDF、网页和摘录先交给系统。SnapGraph 会解析、摘要、建立连接，并把保存理由留作未来找回的线索。</p>
    </div>

    <section v-if="activeReceipt && receiptVisible" class="memory-receipt">
      <div class="section-head compact">
        <div class="section-kicker">已放入知识库</div>
        <h3>{{ batchReceiptVisible ? '本批次记忆回执' : '记忆回执' }}</h3>
        <p>{{ batchReceiptVisible ? '这批材料已经被保存，之后可以作为同一组上下文继续追问。' : '这份材料已经被保存，并整理成一张之后可以回看的记忆回执。' }}</p>
      </div>

      <div v-if="batchReceiptVisible" class="batch-receipt-strip">
        <div>
          <span>本批次</span>
          <strong>{{ props.results.length }} 份材料</strong>
        </div>
        <div class="batch-source-list">
          <span v-for="item in batchSourcePreview" :key="item.source_id">{{ item.title }}</span>
        </div>
      </div>

      <div class="receipt-section">
        <article class="receipt-field">
          <span>保存为</span>
          <strong>{{ receiptTitle }}</strong>
        </article>

        <article class="receipt-field">
          <span>保存理由</span>
          <div class="receipt-field-body">
            <span
              v-if="saveReasonBadge"
              class="evidence-badge"
              :class="saveReasonTone"
            >
              {{ saveReasonBadge }}
            </span>
            <p v-if="saveReasonText">{{ saveReasonText }}</p>
            <p v-else class="receipt-empty-state">这次还没有稳定的保存理由，之后可以在知识库里补写。</p>
          </div>
        </article>

        <article class="receipt-field">
          <span>进入知识库</span>
          <div class="receipt-field-body">
            <strong>{{ receiptSpaceLabel }}</strong>
            <p>{{ receiptSpaceNote }}</p>
          </div>
        </article>

        <article class="receipt-field">
          <span>系统理解</span>
          <div class="receipt-field-body">
            <p v-if="systemUnderstanding">{{ systemUnderstanding }}</p>
            <p v-else class="receipt-empty-state">系统已经先收下这份材料，但还没有稳定的摘要说明。</p>
          </div>
        </article>

        <article class="receipt-field">
          <span>建议连接</span>
          <div class="receipt-field-body">
            <div v-if="connectionSuggestions.length" class="connection-chip-row">
              <span
                v-for="item in connectionSuggestions"
                :key="item.id"
                class="connection-chip"
              >
                {{ connectionLabel(item.type, item.label) }}
              </span>
            </div>
            <p v-else class="receipt-empty-state">暂未找到明确连接，可以稍后在知识库中整理。</p>
          </div>
        </article>
      </div>

      <div class="receipt-actions">
        <button
          class="primary-button batch-question-button"
          type="button"
          :disabled="busy"
          @click="askBatch"
        >
          追问这批材料
        </button>

        <button
          class="paper-button"
          type="button"
          :disabled="!canOpenSpace"
          @click="openSpace"
        >
          查看所在记忆
        </button>

        <button class="paper-button" type="button" @click="continueCollect">
          继续收集
        </button>

        <button
          v-if="canOpenSource"
          class="ghost-button source-link-button"
          type="button"
          @click="receiptDetailOpen = !receiptDetailOpen"
        >
          {{ receiptDetailOpen ? '收起材料详情' : '查看材料详情' }}
        </button>
        <button v-else class="ghost-button source-link-button" type="button" disabled>
          查看材料详情
        </button>
      </div>

      <section v-if="receiptDetailOpen" class="receipt-source-detail">
        <span>材料摘录</span>
        <p>{{ receiptDetailText }}</p>
      </section>
    </section>

    <section class="collect-card" @dragover.prevent @drop.prevent="onDrop">
      <input
        ref="fileInput"
        class="file-input"
        type="file"
        multiple
        accept=".md,.markdown,.txt,.html,.htm,.pdf,.png,.jpg,.jpeg,.webp,.gif"
        @change="onFileSelected"
      />
      <button class="paper-button" :disabled="busy" @click="fileInput?.click()">
        <Paperclip :size="17" />
        选择文件
      </button>
      <textarea
        ref="textInput"
        v-model="text"
        placeholder="也可以粘贴网页摘录、对话或一段想法。"
      />

      <div v-if="files.length" class="file-pills">
        <span v-for="file in files" :key="file.name + file.size">{{ file.name }}</span>
        <button class="text-button" type="button" @click="files = []">清空</button>
      </div>

      <label>
        <span>当时为什么觉得它值得留下？</span>
        <textarea
          v-model="why"
          class="why-input"
          placeholder="可选，但这句话会成为未来找回时最可信的线索。"
        />
      </label>

      <div class="route-row">
        <label>
          <span>进入知识库</span>
          <select v-model="routeMode">
            <option value="auto">AI 自动放入</option>
            <option value="manual">手动选择记忆空间</option>
            <option value="inbox">先放待整理</option>
          </select>
        </label>
        <label v-if="routeMode === 'manual'">
          <span>记忆空间</span>
          <select v-model="spaceId">
            <option v-for="space in routableSpaces" :key="space.id" :value="space.id">{{ spaceDisplayName(space) }}</option>
          </select>
        </label>
      </div>

      <footer>
        <span>{{ helperText }}</span>
        <button class="primary-button" :disabled="busy || !canSubmit" @click="submit">
          <Archive :size="17" />
          放进知识库
        </button>
      </footer>
    </section>

    <section v-if="showProgress" class="ingest-progress">
      <div class="section-head compact">
        <div class="section-kicker">正在入库</div>
        <h3>{{ progressTitle }}</h3>
        <p>先把材料收进来，再整理摘要、保存理由和可能连接。</p>
      </div>

      <div class="ingest-step-list">
        <article
          v-for="step in ingestSteps"
          :key="step.id"
          class="ingest-step"
          :class="step.status"
        >
          <i aria-hidden="true"></i>
          <div>
            <strong>{{ step.label }}</strong>
            <small>{{ step.detail }}</small>
          </div>
        </article>
      </div>
    </section>

    <section v-if="otherResults.length" class="queue-list">
      <article v-for="item in otherResults" :key="item.source_id" class="queue-item">
        <span>{{ sourceType(item.type) }} · {{ resultSpaceLabel(item) }}</span>
        <strong>{{ item.title }}</strong>
        <p>{{ item.summary || '系统已收下这份材料。' }}</p>
        <small v-if="item.routing_suggestion">
          {{ item.routing_suggestion.status === 'accepted' ? '已自动放入' : '待确认' }}：
          {{ routeSuggestionReasonText(item.routing_suggestion) }}
        </small>
      </article>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Archive, Paperclip } from 'lucide-vue-next'
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
const receiptDetailOpen = ref(false)

const STEP_DEFINITIONS = [
  { id: 'extract', label: '提取内容', detail: '先把这份材料转成可以整理的文本' },
  { id: 'summary', label: '生成摘要', detail: '整理出之后回看时最先需要的一句话' },
  { id: 'reason', label: '识别保存理由', detail: '把为什么值得保存变成未来可找回的线索' },
  { id: 'space', label: '建议记忆空间', detail: '判断它应该先进入哪个记忆空间' },
  { id: 'connect', label: '寻找可能连接', detail: '看看它和现有材料或节点可能连到哪里' },
] as const
const RECEIPT_UNDERSTANDING_FALLBACK = '这份材料已经被保存，并可作为之后找回相关判断的线索。'

let progressTimer: ReturnType<typeof setInterval> | null = null

const routableSpaces = computed(() => props.spaces.filter((space) => space.status === 'active' && space.id !== 'inbox'))
const canSubmit = computed(() => Boolean(text.value.trim() || files.value.length))
const helperText = computed(() => {
  if (routeMode.value === 'auto') return '默认先让系统判断位置，低置信的材料会先留在待整理。'
  if (routeMode.value === 'manual') return '这次会直接进入你选择的记忆空间。'
  return '这次先留在待整理，之后可以再集中整理。'
})
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
const otherResults = computed(() => props.results.slice(1))
const receiptVisible = computed(() => Boolean(activeReceipt.value) && activeReceipt.value?.source_id !== hiddenReceiptSourceId.value)
const batchReceiptVisible = computed(() => props.results.length > 1 && receiptVisible.value)
const batchSourcePreview = computed(() => props.results.slice(0, 4))
const batchQuestion = computed(() => '结合刚才上传的这批材料，我们下一步最应该优先完善什么？')
const currentEvidenceCard = computed(() => {
  const receipt = activeReceipt.value
  if (!receipt) return null
  return receipt.focus_graph.evidence_cards.find((card) => card.source_id === receipt.source_id) || receipt.focus_graph.evidence_cards[0] || null
})
const receiptTitle = computed(() => activeReceipt.value?.title?.trim() || '新的材料')
const saveReasonText = computed(() => {
  const userReason = lastSubmitted.value?.why.trim()
  if (userReason) return userReason
  const inferred = currentEvidenceCard.value?.why_saved?.trim() || ''
  return inferred || ''
})
const saveReasonStatus = computed(() => {
  if (lastSubmitted.value?.why.trim()) return 'user-stated'
  return currentEvidenceCard.value?.why_saved_status || activeReceipt.value?.status || 'unknown'
})
const saveReasonTone = computed(() => {
  if (saveReasonStatus.value === 'user-stated') return 'tone-user'
  if (saveReasonStatus.value === 'AI-inferred') return 'tone-ai'
  return 'tone-source'
})
const saveReasonBadge = computed(() => {
  if (!saveReasonText.value) return ''
  if (saveReasonStatus.value === 'user-stated') return 'user-stated / 用户原话'
  if (saveReasonStatus.value === 'AI-inferred') return 'AI-inferred / AI 推断'
  return 'source / 材料'
})
const receiptSpaceLabel = computed(() => resultSpaceLabel(activeReceipt.value) || '未指定')
const receiptSpaceNote = computed(() => {
  const receipt = activeReceipt.value
  if (!receipt) return '还没有明确的记忆位置。'

  const suggestion = receipt.routing_suggestion
  const targetSpace = normalizeBuiltInSpaceName(suggestion?.payload?.target_space_name) || friendlySpaceName(suggestion?.payload?.target_space_id)
  if (suggestion?.status === 'accepted' && targetSpace) {
    return `系统已经帮你放进 ${targetSpace}。`
  }
  if (suggestion?.status === 'pending' && targetSpace) {
    return `当前先保存在 ${receiptSpaceLabel.value}，系统建议稍后整理到 ${targetSpace}。`
  }
  if (lastSubmitted.value?.routeMode === 'manual') {
    return '这次按你的选择直接进入了这个记忆空间。'
  }
  if (lastSubmitted.value?.routeMode === 'inbox') {
    return '这次先放进待整理，之后可以再决定是否移动。'
  }
  return '系统已经先选了一个当前最稳妥的位置。'
})
const systemUnderstanding = computed(() => {
  return getReceiptUnderstanding(activeReceipt.value?.summary || '', receiptTitle.value)
})
const connectionSuggestions = computed(() => {
  const receipt = activeReceipt.value
  if (!receipt) return []
  const seen = new Set<string>()
  return receipt.focus_graph.nodes
    .filter((node) => node.id !== `source_${receipt.source_id}` && !String(node.id || '').includes(receipt.source_id))
    .map((node) => ({ id: node.id, label: node.label?.trim() || '', type: node.type || 'node' }))
    .filter((node) => {
      if (!node.label || node.label === receipt.title || seen.has(node.label)) return false
      seen.add(node.label)
      return true
    })
    .slice(0, 3)
})
const canOpenSource = computed(() => Boolean(activeReceipt.value?.source_id))
const canOpenSpace = computed(() => Boolean(activeReceipt.value?.graph_space_id))
const receiptDetailText = computed(() => {
  const excerpt = currentEvidenceCard.value?.source_excerpt?.trim()
  const summary = activeReceipt.value?.summary?.trim()
  return excerpt || summary || '这份材料已经保存，暂时还没有可以展示的摘录。'
})

watch(showProgress, (active) => {
  if (active) {
    startProgress()
    return
  }
  stopProgress()
}, { immediate: true })

watch(
  () => activeReceipt.value?.source_id,
  (sourceId, previous) => {
    if (sourceId && sourceId !== previous) {
      hiddenReceiptSourceId.value = ''
      receiptDetailOpen.value = false
    }
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
  if (activeReceipt.value) {
    hiddenReceiptSourceId.value = activeReceipt.value.source_id
  }
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

function sourceType(type: string) {
  if (type === 'screenshot') return '图片'
  if (type === 'pdf') return 'PDF'
  if (type === 'webpage') return '网页'
  if (type === 'markdown') return 'Markdown'
  return type || '材料'
}

function friendlySpaceName(spaceId?: string) {
  if (!spaceId) return ''
  const matched = props.spaces.find((space) => space.id === spaceId)
  if (matched) return spaceDisplayName(matched)
  if (spaceId === 'default') return '主记忆'
  if (spaceId === 'inbox') return '待整理'
  return spaceId
}

function spaceDisplayName(space: GraphSpace) {
  if (space.id === 'inbox') return '待整理'
  if (space.id === 'default') return '主记忆'
  return space.name
}

function resultSpaceLabel(result?: IngestResponse | null) {
  if (!result) return ''
  return normalizeBuiltInSpaceName(result.space_name) || friendlySpaceName(result.graph_space_id)
}

function routeSuggestionReasonText(suggestion?: IngestResponse['routing_suggestion']) {
  return sanitizeBuiltInSpaceNames(suggestion?.reason || '')
}

function normalizeBuiltInSpaceName(name?: string) {
  if (!name) return ''
  const normalized = name.trim().toLowerCase()
  if (normalized === 'inbox') return '待整理'
  if (normalized === 'default') return '主记忆'
  return name
}

function sanitizeBuiltInSpaceNames(text = '') {
  return text
    .replace(/\bInbox\b/g, '待整理')
    .replace(/\binbox\b/g, '待整理')
    .replace(/\bDefault\b/g, '主记忆')
    .replace(/\bdefault\b/g, '主记忆')
}

function connectionLabel(type: string, label: string) {
  const prefix = type === 'source'
    ? '材料'
    : type === 'thought'
      ? '想法'
      : type === 'task'
        ? '任务'
        : type === 'project'
          ? '项目'
          : type === 'question'
            ? '问题'
            : '节点'
  return `${prefix} · ${label}`
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
  if (countOccurrences(comparableSummary, comparableTitle) >= 2) return true
  return similarityScore(comparableSummary, comparableTitle) >= 0.82
}

function comparableText(text: string) {
  return text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '')
}

function countOccurrences(text: string, target: string) {
  if (!target) return 0
  let count = 0
  let index = text.indexOf(target)
  while (index >= 0) {
    count += 1
    index = text.indexOf(target, index + target.length)
  }
  return count
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
