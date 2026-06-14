<template>
  <section :class="['recall-result', 'recall-reference-result', `mode-${mode}`, `depth-${depth}`]">
    <article v-if="showDeepProcess && showCurrentThought" class="deeptutor-thought-card" aria-label="本轮 Thought">
      <header class="deeptutor-thought-header">
        <div>
          <span class="deeptutor-thought-kicker">真实 Thought</span>
          <strong>先想，再答</strong>
        </div>
        <span class="deeptutor-thought-mode">Solve mode</span>
      </header>

      <div class="deeptutor-thought-box">
        <div class="thought-box-head">
          <strong>{{ thoughtHeading }}</strong>
          <span>{{ thoughtBoxStatus }}</span>
        </div>
        <div class="thought-trace-list">
          <article
            v-for="item in thoughtTraceItems"
            :key="`${item.id}-${item.label}`"
            :class="['thought-trace-row', { active: item.active }]"
          >
            <span class="thought-trace-label">{{ item.label }}</span>
            <p>{{ item.text }}</p>
          </article>
        </div>
      </div>
      <p class="deeptutor-thought-notice">{{ thoughtNotice }}</p>
    </article>

    <div class="meta-line">
      <span :class="['tag', resultToneClass]">{{ resultToneLabel }}</span>
      <span>{{ resultMeta }}</span>
    </div>

    <article v-if="showFiles" class="local-file-results recall-file-receipts">
      <template v-if="visibleLocalFiles.length">
        <article
          v-for="(file, index) in visibleLocalFiles"
          :key="file.source_id"
          class="receipt-lg local-file-card local-file-compact-card"
          :style="{ animationDelay: `${index * 0.08}s` }"
        >
          <div class="head">
            <span :class="['tag', statusTagClass(file)]">{{ statusLabel(file) }}</span>
            <span class="when">{{ fileSubtitle(file) }}</span>
          </div>
          <div class="quote">「{{ fileQuote(file) }}」</div>
          <div class="src">
            <span>{{ file.title }}</span>
            <button class="open source-link-button" type="button" @click="openLocalFile(file)">打开原文 ↗</button>
          </div>
        </article>

        <details v-if="hiddenLocalFileCount > 0" class="evidence local-file-more-note">
          <summary>还有 {{ hiddenLocalFileCount }} 份材料，先收起来</summary>
          <div class="body">
            <button
              v-for="file in hiddenLocalFiles"
              :key="file.source_id"
              class="web-src compact-source-row"
              type="button"
              @click="openLocalFile(file)"
            >
              <span class="dom">{{ file.space_name || '本地材料' }}</span>
              <span class="ttl">{{ file.title }}</span>
              <span class="take">打开 ↗</span>
            </button>
          </div>
        </details>
      </template>

      <div v-else-if="isResolvingLocalFiles" class="refuse local-file-loading" aria-live="polite">
        <h3>正在找本地文件。</h3>
        <p>找到后会先显示最相关的一两张回执，不会把列表铺满屏幕。</p>
      </div>

      <div v-else class="refuse focus-empty-state">
        <h3>本地没有找到文件。</h3>
        <p>我不会把没找到说成找到了。可以换个项目名、文件名或保存理由再问一次。</p>
      </div>
    </article>

    <article v-if="showAnswer" class="snapgraph-thinking ai-aside">
      <div class="lbl">AI 的补充 · 不冒充你</div>

      <div v-if="isThinking" class="thinking-stream-state" aria-live="polite">
        <strong>{{ thinkingProgressLabel }}</strong>
        <p>{{ thinkingProgressDetail }}</p>
      </div>
      <div v-else class="thinking-markdown-wrap" :class="{ 'is-streaming': isStreamingAnswer }">
        <RichMarkdown :markdown="displayAnswerMarkdown" />
        <span v-if="isStreamingAnswer" class="typing-caret" aria-hidden="true"></span>
      </div>
    </article>

    <details v-if="hasDetails" class="evidence deep-stage-details">
      <summary>证据路径</summary>
      <div class="body">
        <div v-if="memoryTouchpoints.length" class="recall-memory-touchpoints">
          <div v-for="item in memoryTouchpoints" :key="item.source_id || item.title" class="e-src">
            <span class="e-when">{{ memoryKindLabel(item.why_saved_status) }}</span>
            <span class="e-q">「{{ item.title }}」</span>
          </div>
        </div>
        <p v-else>{{ evidenceText }}</p>
        <div v-if="stages.length && depth === 'deep'" class="deep-stage-list">
          <span
            v-for="stage in stages"
            :key="stage.id"
            :class="['deep-stage-pill', `is-${stage.status}`]"
          >
            {{ stage.label }}{{ stage.detail ? ` · ${stageDetailText(stage.detail)}` : '' }}
          </span>
        </div>
        <div class="thinking-footnotes" aria-label="回答边界">
          <article v-for="section in thinkingSections" :key="section.label" class="thinking-block">
            <span class="thinking-block-label">{{ section.label }}</span>
            <p>{{ section.text }}</p>
          </article>
        </div>
      </div>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { filterUserFacingAnswerMarkdown } from '../answerDisplay'
import RichMarkdown from './RichMarkdown.vue'
import type {
  AskResponse,
  FocusGraph,
  LocalFileResult,
  RecallDepth,
  RecallMode,
  RecallThought,
  RecallThoughtTraceEvent,
  ThoughtHistoryPayload,
} from '../types'

const props = defineProps<{
  result: AskResponse | null
  focusGraph: FocusGraph | null
  busy: boolean
  stages: Array<{ id: string; label: string; status: string; detail?: string }>
  question: string
  mode: RecallMode
  depth: RecallDepth
  localFiles?: LocalFileResult[]
  currentThought?: RecallThought | null
  thoughtHistory?: ThoughtHistoryPayload | null
}>()

const emit = defineEmits<{
  askFollowUp: [question: string]
  openLocalFile: [file: LocalFileResult]
}>()

const contexts = computed(() => props.result?.contexts || props.focusGraph?.evidence_cards || [])
const localFiles = computed<LocalFileResult[]>(() => props.localFiles || props.result?.local_files || props.focusGraph?.local_files || [])
const projection = computed(() => props.result?.recall_projection || null)
const mode = computed(() => props.mode || 'auto')
const depth = computed(() => props.depth || 'quick')
const visibleLocalFiles = computed(() => {
  if (mode.value === 'files') return localFiles.value.slice(0, 4)
  return localFiles.value.slice(0, depth.value === 'deep' ? 3 : 2)
})
const hiddenLocalFiles = computed(() => localFiles.value.slice(visibleLocalFiles.value.length))
const hiddenLocalFileCount = computed(() => hiddenLocalFiles.value.length)
const showFiles = computed(() => mode.value !== 'answer')
const showAnswer = computed(() => mode.value !== 'files')
const isResolvingLocalFiles = computed(() => props.busy && !localFiles.value.length)
const answerMarkdown = computed(() => props.result?.text || '')
const displayAnswerMarkdown = computed(() => filterUserFacingAnswerMarkdown(answerMarkdown.value))
const hasAnswerText = computed(() => Boolean(displayAnswerMarkdown.value.trim()))
const isThinking = computed(() => showAnswer.value && props.busy && !hasAnswerText.value)
const isStreamingAnswer = computed(() => props.busy && hasAnswerText.value && !projection.value)
const showDeepProcess = computed(() => depth.value === 'deep' && (showFiles.value || showAnswer.value))
const currentThought = computed(() => props.currentThought || props.result?.thought || null)
const showCurrentThought = computed(() => depth.value === 'deep' && Boolean(currentThought.value))
const isThoughtStreaming = computed(() => currentThought.value?.status === 'thinking')
const thoughtLines = computed(() => currentThought.value?.lines || [])
const thoughtTraceEvents = computed<RecallThoughtTraceEvent[]>(() => currentThought.value?.trace_events || [])
const thoughtHeading = computed(() => currentThought.value?.summary || '正在形成本轮 Thought')
const thoughtBoxStatus = computed(() => isThoughtStreaming.value ? '正在思考 · 流式 solve trace' : '模型具体思考 · 公开 solve trace')
const thoughtNotice = computed(() => currentThought.value?.notice || 'Thought 只来自本轮后端事件，不会伪造。')
const thoughtTraceItems = computed(() => {
  if (thoughtTraceEvents.value.length) {
    return thoughtTraceEvents.value.map((event) => ({
      id: event.trace_id,
      label: traceLabel(event),
      text: localizeThoughtLine(event.text),
      active: isThoughtStreaming.value && event.call_state === 'running',
    }))
  }
  return thoughtLines.value.map((line, index) => {
    const localized = localizeThoughtLine(line)
    const match = localized.match(/^([A-Za-z]+|Context)[：:]\s*(.+)$/)
    return {
      id: `legacy-${index}`,
      label: match ? match[1].toUpperCase() : 'THINK',
      text: match ? match[2] : localized,
      active: isThoughtStreaming.value,
    }
  })
})
const memoryTouchpoints = computed(() => contexts.value.slice(0, 3))
const hasDetails = computed(() => contexts.value.length > 0 || props.stages.length > 0 || props.busy)
const resultToneLabel = computed(() => {
  if (mode.value === 'files') return localFiles.value.length ? '找到本地文件' : '本地检索'
  if (!localFiles.value.length && !hasAnswerText.value && !props.busy) return '没有稳定证据'
  return localFiles.value.length ? '找到你的原话' : 'AI 回复'
})
const resultToneClass = computed(() => {
  if (!localFiles.value.length && !hasAnswerText.value && !props.busy) return 'tag-rust'
  if (localFiles.value.length) return 'tag-moss'
  return 'tag-grey'
})
const resultMeta = computed(() => {
  const scanned = props.focusGraph?.confidence_summary.source_count || contexts.value.length || localFiles.value.length
  if (localFiles.value.length) return `${localFiles.value.length} 份相关材料 · 本地优先 · 可打开原文`
  if (props.busy) return '正在扫本地材料，结果固定前不展示猜测。'
  return scanned ? `${scanned} 条本地线索 · 证据已收起` : '没有达到阈值的本地证据'
})
const thinkingProgressLabel = computed(() => {
  const active = props.stages.find((stage) => stage.status === 'active')
  if (active?.id === 'evidence') return '正在找本地证据'
  if (active?.id === 'thought') return '正在形成 Thought'
  if (active?.id === 'read') return '正在读用户原话'
  if (active?.id === 'connect') return '正在检查连接'
  return '正在组织回答'
})
const thinkingProgressDetail = computed(() => {
  if (contexts.value.length) return '本地证据已经进入工作区，完整回复生成后会自动替换这里。'
  return '先找回本地材料和用户原话，再让 AI 给出有边界的整理。'
})
const evidenceText = computed(() => {
  if (props.busy && !contexts.value.length) return '正在读取本地图谱，还没有把结果固定下来。'
  const userAnchors = contexts.value.filter((item) => item.why_saved_status === 'user-stated')
  if (userAnchors.length) return `优先依据 ${userAnchors.slice(0, 2).map((item) => item.title).join('、')}。`
  if (contexts.value.length) return `当前依据 ${contexts.value.slice(0, 2).map((item) => item.title).join('、')}，但缺少明确用户保存理由。`
  return '没有可靠本地证据时，SnapGraph 不会把猜测当成你的记忆。'
})
const inferenceText = computed(() => {
  const aiCount = contexts.value.filter((item) => item.why_saved_status === 'AI-inferred').length
  if (aiCount) return `${aiCount} 条线索是 AI 猜的理由，只能作为待确认连接。`
  return '这次没有把 AI 推断伪装成用户原意。'
})
const nextText = computed(() => {
  if (props.busy && !hasAnswerText.value) return '等本地证据固定后，可以打开文件或继续追问这条判断。'
  const action = projection.value?.actions.find((item) => item.kind === 'ask' || item.kind === 'open_loop')
  if (action?.detail) return localizeActionDetail(action.detail)
  const loop = contexts.value.flatMap((item) => item.open_loops || []).find((item) => item && item !== 'None')
  if (loop) return loop.replace(/^(Open loop|Todo)[:：]\s*/i, '')
  if (localFiles.value.length) return '先打开最相关的文件，确认这条判断今天是否仍然成立。'
  return '换一个更接近旧材料标题、项目名或保存理由的问题。'
})
const thinkingSections = computed(() => [
  { label: '依据', text: compactSignal(evidenceText.value, 64) },
  { label: 'AI 猜测', text: compactSignal(inferenceText.value, 56) },
  { label: '下一步', text: compactSignal(nextText.value, 64) },
])

function openLocalFile(file: LocalFileResult) {
  emit('openLocalFile', file)
}

function fileSubtitle(file: LocalFileResult) {
  if (file.space_name) return `${file.space_name} · 本地材料`
  if (file.why_saved_status === 'user-stated') return '带有用户写过的保存理由'
  if (file.why_saved_status === 'AI-inferred') return '保存理由需要你确认'
  return '本地材料'
}

function statusLabel(file: LocalFileResult) {
  if (file.why_saved_status === 'user-stated') return '你的原话'
  if (file.why_saved_status === 'AI-inferred') return 'AI 猜的理由'
  return '本地材料'
}

function statusTagClass(file: LocalFileResult) {
  if (file.why_saved_status === 'user-stated') return 'tag-moss'
  if (file.why_saved_status === 'AI-inferred') return 'tag-web'
  return 'tag-grey'
}

function fileQuote(file: LocalFileResult) {
  const value = file.source_excerpt || file.match_reason || file.why_saved || file.title
  return compactSignal(localizeSnippet(value), 118)
}

function memoryKindLabel(status?: string) {
  if (status === 'user-stated') return '你的'
  if (status === 'AI-inferred') return 'AI 推'
  return '材料'
}

function cleanText(text: string) {
  return text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/^\s*(?:[-*+]\s+|\d+[.)]\s+)/gm, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function compactSignal(text: string, limit: number) {
  const cleaned = cleanText(text)
  return cleaned.length <= limit ? cleaned : `${cleaned.slice(0, limit).trim()}…`
}

function localizeActionDetail(detail: string) {
  const cleaned = detail.trim()
  const match = cleaned.match(/^Continue from (.+)\.$/)
  if (match) return `继续围绕 ${match[1]} 追问。`
  return localizeSnippet(cleaned)
}

function stageDetailText(detail: string) {
  return localizeSnippet(detail)
    .replace(/user-stated/g, '用户原话')
    .replace(/AI-inferred/g, 'AI 猜测')
    .replace(/MockLLM/g, '本地模型')
    .replace(/provider/g, '模型')
}

function localizeThoughtLine(text: string) {
  return localizeSnippet(text)
    .replace(/\bthinking\b/gi, 'thought')
    .replace(/\btool events?\b/gi, '工具事件')
}

function traceLabel(event: RecallThoughtTraceEvent) {
  const label = event.label || event.trace_role || 'THINK'
  if (label.toLowerCase() === 'context') return 'CTX'
  if (label.toLowerCase() === 'retrieve') return 'RET'
  if (label.toLowerCase() === 'verify') return 'CHK'
  if (label.toLowerCase() === 'finish') return 'OUT'
  return label.toUpperCase()
}

function localizeSnippet(text: string) {
  return text
    .replace(/^AI-inferred\s*[:：]\s*/i, 'AI 猜测：')
    .replace(/\bAI-inferred\b/g, 'AI 猜测')
    .replace(/\buser-stated\b/g, '用户原话')
    .replace(/\bopen loop\b/gi, '未处理完的问题')
}
</script>
