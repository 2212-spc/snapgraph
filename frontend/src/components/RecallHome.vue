<template>
  <section class="recall-home" :class="{ 'has-result': showResult }">
    <div class="recall-hero" :class="{ 'is-compact': showResult }">
      <p class="eyebrow">记忆找回</p>
      <h1>找回一个过去的判断</h1>
      <p class="hero-copy">{{ heroCopy }}</p>

      <form class="recall-box recall-command" @submit.prevent="submit">
        <textarea
          v-model="question"
          :disabled="busy"
          placeholder="例如：我之前为什么觉得截图不是核心？"
          autofocus
        />
        <div class="recall-actions">
          <span>{{ statusText }}</span>
          <button class="primary-button recall-submit" :disabled="busy || !question.trim()">
            <Search :size="17" />
            找回
          </button>
        </div>
      </form>

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

      <p v-if="!showResult" class="recall-hint">只查你的本地 SnapGraph，不是网页搜索。</p>
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
import { Search } from 'lucide-vue-next'
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
  '我之前为什么觉得截图不是核心？',
  '最近我围绕 SnapGraph 真正在追什么问题？',
  '哪些旧材料能帮我判断 agent memory 的方向？',
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
