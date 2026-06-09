<template>
  <section class="recall-home" :class="{ 'has-result': showResult }">
    <div class="recall-hero" :class="{ 'is-compact': showResult }">
      <h1>{{ showResult ? displayQuestion || '新对话' : '今天想学什么？' }}</h1>
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
              placeholder="今天我能帮您什么？"
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
  '把这个概念讲给初学者听，再给一个判断例子。',
  '带我一步一步做这道题，并指出最容易错的地方。',
  '把这个系统画成 Mermaid 图，并解释每条边代表什么。',
  '围绕这个知识点考我 3 题，再根据我的答案讲错因。',
]
const showResult = computed(() => Boolean(props.result || props.focusGraph))
const heroCopy = computed(() => showResult.value
  ? '继续从本地材料、保存理由和图谱路径里追问这个判断。'
  : '选择一个方向开始，或者直接输入你想理解、求解、画图、练习的问题。')
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
</script>
