<template>
  <section class="recall-home">
    <div class="recall-hero">
      <p class="eyebrow">涌现式找回</p>
      <h1>想找回什么？</h1>
      <p class="hero-copy">从旧材料、当时写下的理由和图谱连接里，把遗失的判断重新浮上来。</p>

      <form class="recall-box" @submit.prevent="submit">
        <textarea
          v-model="question"
          :disabled="busy"
          placeholder="比如：我之前为什么觉得截图不是核心？"
          autofocus
        />
        <div class="recall-actions">
          <span>{{ statusText }}</span>
          <button class="primary-button" :disabled="busy || !question.trim()">
            <Search :size="17" />
            找回
          </button>
        </div>
      </form>

      <div class="prompt-row">
        <button v-for="prompt in prompts" :key="prompt" :disabled="busy" @click="usePrompt(prompt)">
          {{ prompt }}
        </button>
      </div>
    </div>

    <RecallResult v-if="result || focusGraph" :result="result" :focus-graph="focusGraph" />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Search } from 'lucide-vue-next'
import RecallResult from './RecallResult.vue'
import type { AskResponse, FocusGraph } from '../types'

const props = defineProps<{
  busy: boolean
  busyStage: string
  result: AskResponse | null
  focusGraph: FocusGraph | null
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
const statusText = computed(() => props.busy ? props.busyStage || '正在找回。' : '只要说出一点线索。')

function submit() {
  const text = question.value.trim()
  if (text) emit('recall', text)
}

function usePrompt(prompt: string) {
  question.value = prompt
  emit('recall', prompt)
}
</script>
