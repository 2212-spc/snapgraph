<template>
  <section class="recall-home" :class="{ 'has-result': showResult, 'is-answering': busy }">
    <div class="recall-hero" :class="{ 'is-compact': showResult }">
      <h1>{{ showResult ? displayQuestion || '新对话' : '找回当时为什么在意它' }}</h1>
      <p class="hero-copy">{{ heroCopy }}</p>
      <div v-if="showResult && busy" class="result-stream-status" aria-live="polite">
        <span aria-hidden="true"></span>
        {{ statusText }}
      </div>

      <div v-if="!showResult" class="recall-mode-switch" aria-label="选择找回模式">
        <button
          v-for="item in modeOptions"
          :key="item.id"
          type="button"
          :class="{ active: mode === item.id }"
          :disabled="busy"
          @click="$emit('modeChanged', item.id)"
        >
          <component :is="item.icon" :size="15" />
          <span>{{ item.label }}</span>
          <small>{{ item.detail }}</small>
        </button>
      </div>

      <form class="recall-box recall-command" @submit.prevent="submit">
        <div class="composer-input-wrap">
          <textarea
            v-model="question"
            :disabled="busy"
            placeholder="例如：我之前为什么觉得这个方向值得做？"
            rows="1"
            autofocus
          />
        </div>
        <div class="composer-send-row">
          <span v-if="busy && !showResult" class="composer-status">{{ statusText }}</span>
          <button class="primary-button recall-submit" :disabled="busy || !question.trim()" title="Send">
            <ArrowUp :size="15" />
          </button>
        </div>
      </form>

      <div v-if="!showResult" class="starter-grid">
        <button
          v-for="prompt in prompts"
          :key="prompt"
          class="example-chip"
          type="button"
          :disabled="busy"
          @click="usePrompt(prompt)"
        >
          {{ prompt }}
        </button>
      </div>

      <div v-if="!showResult && recentQuestions.length" class="recent-question-panel">
        <span>最近问题</span>
        <div class="recent-question-list">
          <button
            v-for="item in recentQuestions.slice(0, 3)"
            :key="item.id"
            type="button"
            class="recent-question-chip"
            :disabled="busy"
            @click="usePrompt(item.question)"
          >
            <strong>{{ item.question }}</strong>
          </button>
        </div>
      </div>
    </div>

    <RecallResult
      v-if="result || focusGraph"
      :result="result"
      :focus-graph="focusGraph"
      :busy="busy"
      :stages="stages"
      :question="displayQuestion"
      :mode="activeResultMode"
      :local-files="localFiles"
      @ask-follow-up="askFollowUp"
      @open-local-file="$emit('openLocalFile', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowUp, Bot, FileSearch, WandSparkles } from 'lucide-vue-next'
import RecallResult from './RecallResult.vue'
import type { AskResponse, FocusGraph, LocalFileResult, RecallMode, RecallStage } from '../types'

const props = defineProps<{
  busy: boolean
  busyStage: string
  mode: RecallMode
  resultMode: RecallMode
  result: AskResponse | null
  focusGraph: FocusGraph | null
  stages: RecallStage[]
  currentQuestion: string
  recentQuestions?: Array<{ id: string; question: string; path?: string }>
}>()

const emit = defineEmits<{
  recall: [question: string, mode: RecallMode]
  modeChanged: [mode: RecallMode]
  openLocalFile: [file: LocalFileResult]
}>()

const question = ref('')
const modeOptions = [
  { id: 'auto' as const, label: '自动', detail: '文件 + 回复', icon: WandSparkles },
  { id: 'files' as const, label: '找文件', detail: '只看来源', icon: FileSearch },
  { id: 'answer' as const, label: '问 AI', detail: '只要回答', icon: Bot },
]
const prompts = [
  '我为什么要从 LLM Wiki 开始？',
  '这批材料里，哪个判断最值得继续追？',
  '哪些内容只是 AI 推断，还需要我确认？',
  '还有哪些 open loop 应该继续处理？',
]
const showResult = computed(() => Boolean(props.result || props.focusGraph))
const activeResultMode = computed(() => showResult.value ? props.resultMode : props.mode)
const heroCopy = computed(() => showResult.value
  ? '继续从本地文件和保存理由里追问这个判断，必要时直接打开原文件回到源头。'
  : '先回到本地文件、用户原话和保存理由，再让 AI 把推断与证据分清。')
const displayQuestion = computed(() => question.value.trim() || props.currentQuestion || props.result?.question || '')
const statusText = computed(() => props.busy ? props.busyStage || '正在回答。' : '按回车或点击发送。')
const recentQuestions = computed(() => props.recentQuestions || [])
const localFiles = computed<LocalFileResult[]>(() => props.result?.local_files || props.focusGraph?.local_files || [])

watch(
  () => props.currentQuestion,
  (value) => {
    if (value && value !== question.value) {
      question.value = value
    }
  },
  { immediate: true },
)

function submit() {
  const text = question.value.trim()
  if (text) emit('recall', text, props.mode)
}

function usePrompt(prompt: string) {
  question.value = prompt
}

function askFollowUp(questionText: string) {
  const text = questionText.trim()
  if (!text) return
  question.value = text
  emit('recall', text, activeResultMode.value)
}
</script>
