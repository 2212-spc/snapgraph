<template>
  <section :class="['recall-result', 'recall-response-focus', 'recall-response-stack', `mode-${mode}`]">
    <article v-if="showFiles" class="local-file-results">
      <div class="focus-panel-head">
        <div>
          <div class="result-kicker">本地结果</div>
          <h2>{{ filePanelTitle }}</h2>
        </div>
        <span>{{ localFileCountLabel }}</span>
      </div>

      <div v-if="localFiles.length" class="local-file-list">
        <details
          v-for="(file, index) in visibleLocalFiles"
          :key="file.source_id"
          class="local-file-card local-file-compact-card"
          :open="index === 0 && visibleLocalFiles.length <= 3"
        >
          <summary>
            <div class="local-file-icon" aria-hidden="true">
              <span>{{ index + 1 }}</span>
              <FileText :size="15" />
            </div>
            <div class="local-file-main">
              <div class="local-file-title-row">
                <strong>{{ file.title }}</strong>
              </div>
              <small>{{ displayPath(file) }}</small>
            </div>
            <div class="local-file-summary-meta">
              <span :class="['local-file-status', statusTone(file)]">{{ statusLabel(file) }}</span>
              <ChevronDown :size="15" />
            </div>
          </summary>
          <div class="local-file-detail">
            <p>{{ file.match_reason || fileReason(file) }}</p>
            <blockquote v-if="file.source_excerpt">{{ file.source_excerpt }}</blockquote>
            <div class="local-file-actions">
              <button class="source-link-button" type="button" @click="openLocalFile(file)">
                <ExternalLink :size="14" />
                <span>打开</span>
              </button>
              <button class="paper-button" type="button" @click="askAboutFile(file)">
                <MessageSquare :size="14" />
                <span>追问</span>
              </button>
            </div>
          </div>
        </details>
      </div>

      <div v-else-if="isResolvingLocalFiles" class="local-file-loading" aria-live="polite">
        <div class="loading-file-row" aria-hidden="true">
          <span></span>
          <div>
            <i></i>
            <i></i>
          </div>
        </div>
        <p>正在从本地记忆里找文件，找到后会直接出现在这里。</p>
      </div>

      <p v-else class="focus-empty-state">没有找到能支撑这个问题的本地文件。</p>
    </article>

    <article v-if="showAnswer" class="snapgraph-thinking">
      <div class="focus-panel-head">
        <div>
          <div class="result-kicker">AI 回复</div>
          <h2>{{ answerPanelTitle }}</h2>
        </div>
        <span>{{ thinkingStateLabel }}</span>
      </div>

      <div class="thinking-answer" aria-live="polite">
        <div v-if="isThinking" class="thinking-stream-state">
          <span class="thinking-pulse" aria-hidden="true"></span>
          <div>
            <strong>{{ thinkingProgressLabel }}</strong>
            <p>{{ thinkingProgressDetail }}</p>
          </div>
          <div class="thinking-skeleton" aria-hidden="true">
            <i></i>
            <i></i>
            <i></i>
          </div>
        </div>
        <div v-else class="thinking-markdown-wrap" :class="{ 'is-streaming': isStreamingAnswer }">
          <RichMarkdown :markdown="displayAnswerMarkdown" />
          <span v-if="isStreamingAnswer" class="typing-caret" aria-hidden="true"></span>
        </div>
        <div v-if="showAnswerBoundaries" class="thinking-footnotes" aria-label="回答边界">
          <article v-for="section in thinkingSections" :key="section.label" class="thinking-block">
            <span class="thinking-block-label">{{ section.label }}</span>
            <p>{{ section.text }}</p>
          </article>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChevronDown, ExternalLink, FileText, MessageSquare } from 'lucide-vue-next'
import { filterUserFacingAnswerMarkdown } from '../answerDisplay'
import RichMarkdown from './RichMarkdown.vue'
import type { AskResponse, FocusGraph, LocalFileResult, RecallMode } from '../types'

const props = defineProps<{
  result: AskResponse | null
  focusGraph: FocusGraph | null
  busy: boolean
  stages: Array<{ id: string; label: string; status: string; detail?: string }>
  question: string
  mode: RecallMode
  localFiles?: LocalFileResult[]
}>()

const emit = defineEmits<{
  askFollowUp: [question: string]
  openLocalFile: [file: LocalFileResult]
}>()

const contexts = computed(() => props.result?.contexts || props.focusGraph?.evidence_cards || [])
const localFiles = computed<LocalFileResult[]>(() => props.localFiles || props.result?.local_files || props.focusGraph?.local_files || [])
const visibleLocalFiles = computed(() => localFiles.value)
const projection = computed(() => props.result?.recall_projection || null)
const confidenceLabel = computed(() => confidenceText(projection.value?.judgment.confidence_label || props.focusGraph?.confidence_summary.confidence_label || 'mixed'))
const mode = computed(() => props.mode || 'auto')
const showFiles = computed(() => mode.value !== 'answer')
const showAnswer = computed(() => mode.value !== 'files')
const filePanelTitle = computed(() => mode.value === 'files' ? '文件查找结果' : '召回的本地文件')
const answerPanelTitle = computed(() => mode.value === 'answer' ? 'AI 回复' : 'SnapGraph 的思考')
const isResolvingLocalFiles = computed(() => props.busy && !localFiles.value.length)
const answerMarkdown = computed(() => props.result?.text || '')
const displayAnswerMarkdown = computed(() => filterUserFacingAnswerMarkdown(answerMarkdown.value))
const hasAnswerText = computed(() => Boolean(displayAnswerMarkdown.value.trim()))
const isThinking = computed(() => showAnswer.value && props.busy && !hasAnswerText.value)
const isStreamingAnswer = computed(() => props.busy && hasAnswerText.value && !projection.value)
const showAnswerBoundaries = computed(() => mode.value === 'auto' && (contexts.value.length > 0 || props.busy))
const localFileCountLabel = computed(() => {
  if (isResolvingLocalFiles.value) return '查找中'
  return localFiles.value.length ? `${localFiles.value.length} 个文件` : '未找到'
})
const thinkingStateLabel = computed(() => {
  if (isThinking.value) return '整理中'
  if (isStreamingAnswer.value) return '生成中'
  return confidenceLabel.value
})
const thinkingProgressLabel = computed(() => {
  const active = props.stages.find((stage) => stage.status === 'active')
  if (active?.id === 'evidence') return '正在找本地证据'
  if (active?.id === 'read') return '正在读保存理由'
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
  if (userAnchors.length) {
    const titles = userAnchors.slice(0, 2).map((item) => item.title).join('、')
    return `优先依据 ${titles}，因为它们带有用户写下的保存理由。`
  }
  if (contexts.value.length) {
    const titles = contexts.value.slice(0, 2).map((item) => item.title).join('、')
    return `当前依据 ${titles}，但缺少明确的用户保存理由。`
  }
  return '没有可靠本地证据时，SnapGraph 不会把猜测当成你的记忆。'
})
const inferenceText = computed(() => {
  if (props.busy && !contexts.value.length) return 'AI 推断会在找到证据后单独标记，不会混成你的原意。'
  const aiCount = contexts.value.filter((item) => item.why_saved_status === 'AI-inferred').length
  if (aiCount) return `${aiCount} 条线索是 AI-inferred，只能作为待确认连接。`
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
  { label: '依据', text: compactSignal(evidenceText.value, 54) },
  { label: 'AI 推断', text: compactSignal(inferenceText.value, 46) },
  { label: '下一步', text: compactSignal(nextText.value, 48) },
])

function openLocalFile(file: LocalFileResult) {
  emit('openLocalFile', file)
}

function askAboutFile(file: LocalFileResult) {
  emit('askFollowUp', `围绕《${file.title}》，继续解释它和这个问题的关系。`)
}

function displayPath(file: LocalFileResult) {
  return file.raw_path || file.path
}

function statusLabel(file: LocalFileResult) {
  if (file.why_saved_status === 'user-stated') return '用户原话'
  if (file.why_saved_status === 'AI-inferred') return 'AI 推断'
  return '本地材料'
}

function statusTone(file: LocalFileResult) {
  if (file.why_saved_status === 'user-stated') return 'is-user'
  if (file.why_saved_status === 'AI-inferred') return 'is-ai'
  return 'is-source'
}

function fileReason(file: LocalFileResult) {
  if (file.why_saved_status === 'user-stated' && file.why_saved) return file.why_saved
  if (file.source_excerpt) return file.source_excerpt
  return '这份文件和当前问题存在本地命中关系。'
}

function confidenceText(label: string) {
  if (label === 'strong') return '证据较强'
  if (label === 'weak' || label === 'none') return '低置信度'
  return '证据中等'
}

function cleanText(text: string) {
  return text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/^[-\d.]+\s*/gm, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function compactSignal(text: string, limit: number) {
  const cleaned = cleanText(text)
  return cleaned.length <= limit ? cleaned : cleaned.slice(0, limit).trim()
}

function localizeActionDetail(detail: string) {
  const cleaned = detail.trim()
  const match = cleaned.match(/^Continue from (.+)\.$/)
  if (match) return `继续围绕 ${match[1]} 追问。`
  return cleaned
}
</script>
