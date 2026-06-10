<template>
  <section class="recall-home" :class="{ 'has-result': showResult }">
    <div class="recall-hero" :class="{ 'is-compact': showResult }">
      <h1>{{ showResult ? displayQuestion || '新对话' : '找回当时为什么在意它' }}</h1>
      <p v-if="showResult" class="hero-copy">{{ heroCopy }}</p>

      <div v-if="!showResult" class="starter-grid">
        <div v-if="!showResult" class="prompt-row example-chip-row">
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
      </div>

      <div class="composer-shell">
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
          <div class="composer-toolbar">
            <div class="composer-tool-row">
              <button class="composer-pill is-active" type="button" disabled title="聊天">
                <MessageSquare :size="15" />
                <span>聊天</span>
              </button>
              <button class="composer-tool-button" type="button" disabled title="附加证据">
                <Paperclip :size="12" />
                <span>证据</span>
              </button>
              <button class="composer-tool-button" type="button" disabled title="知识库">
                <Database :size="12" />
                <span>知识库</span>
              </button>
              <button class="composer-tool-button" type="button" disabled title="空间">
                <AtSign :size="12" />
                <span>空间</span>
              </button>
            </div>
            <div class="composer-send-row">
              <span v-if="busy" class="composer-status">{{ statusText }}</span>
              <button class="primary-button recall-submit" :disabled="busy || !question.trim()" title="Send">
                <ArrowUp :size="15" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>

    <RecallResult
      v-if="result || focusGraph"
      :result="result"
      :focus-graph="focusGraph"
      :busy="busy"
      :stages="stages"
      :question="displayQuestion"
      @ask-follow-up="askFollowUp"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowUp, AtSign, Database, MessageSquare, Paperclip } from 'lucide-vue-next'
import RecallResult from './RecallResult.vue'
import type { AskResponse, FocusGraph, RecallStage } from '../types'

const props = defineProps<{
  busy: boolean
  busyStage: string
  result: AskResponse | null
  focusGraph: FocusGraph | null
  stages: RecallStage[]
  currentQuestion: string
}>()

const emit = defineEmits<{
  recall: [question: string]
}>()

const question = ref('')
const prompts = [
  '我之前为什么觉得 LLM Wiki 是 SnapGraph 的起点？',
  '刚才上传的这批材料，最值得继续追的判断是什么？',
  '哪些判断只有 AI 推断，还需要我确认？',
  '还有哪些 open loop 现在应该继续处理？',
]
const showResult = computed(() => Boolean(props.result || props.focusGraph))
const heroCopy = computed(() => showResult.value
  ? '继续从本地材料、保存理由和图谱路径里追问这个判断。'
  : '问问过去的你。SnapGraph 会先找回用户原话、保存理由和证据路径，再让 AI 做有边界的整理。')
const displayQuestion = computed(() => question.value.trim() || props.currentQuestion || props.result?.question || '')
const statusText = computed(() => props.busy ? props.busyStage || '正在回答。' : '按回车或点击发送。')

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
  if (text) emit('recall', text)
}

function usePrompt(prompt: string) {
  question.value = prompt
}

function askFollowUp(questionText: string) {
  const text = questionText.trim()
  if (!text) return
  question.value = text
  emit('recall', text)
}
</script>
