<template>
  <section class="recall-home" :class="{ 'has-result': showResult }">
    <div class="recall-hero" :class="{ 'is-compact': showResult }">
<<<<<<< Updated upstream
      <h1>{{ showResult ? displayQuestion || '新对话' : '今天想学什么？' }}</h1>
      <p v-if="showResult" class="hero-copy">{{ heroCopy }}</p>
=======
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
            :placeholder="placeholderText"
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
>>>>>>> Stashed changes

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
const placeholderText = computed(() => {
  if (props.mode === 'files') return '例如：有哪些证据说明我当时在关注这个问题？'
  if (props.mode === 'answer') return '例如：根据这些材料，帮我整理一个可执行判断'
  return '例如：我之前为什么觉得这个方向值得做？'
})
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
