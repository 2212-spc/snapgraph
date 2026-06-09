<template>
  <section class="recall-home" :class="{ 'has-result': showResult }">
    <div class="recall-hero" :class="{ 'is-compact': showResult }">
      <h1>{{ showResult ? '找回一个过去的判断' : '问问过去的你' }}</h1>
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
              placeholder="找回一个旧判断、证据或保存理由..."
              rows="1"
              autofocus
            />
          </div>
          <div class="composer-toolbar">
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
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowUp } from 'lucide-vue-next'
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
  '我之前为什么关注这个问题？',
  '哪些材料支持我当时的判断？',
  '找出我保存过的用户原话和证据。',
  '这个项目还有哪些未闭环问题？',
]
const showResult = computed(() => Boolean(props.result || props.focusGraph))
const heroCopy = computed(() => showResult.value
  ? '继续从本地材料、保存理由和图谱路径里追问这个判断。'
  : '问一个你曾经想过、保存过、但现在记不清来龙去脉的问题。SnapGraph 会从本地材料、保存理由和图谱路径里，重新拼回当时的判断依据。')
const displayQuestion = computed(() => question.value.trim() || props.currentQuestion || props.result?.question || '')
const statusText = computed(() => props.busy ? props.busyStage || '正在从本地记忆里找回线索。' : '按回车或点击找回。')

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
</script>
