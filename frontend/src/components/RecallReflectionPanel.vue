<template>
  <section class="recall-reflection-panel" aria-label="设计复盘">
    <div class="reflection-head">
      <div>
        <p class="section-kicker">设计复盘</p>
        <h3>这次找回之后，先验证什么</h3>
      </div>
      <span>{{ contexts.length }} 条证据</span>
    </div>

    <div class="reflection-grid">
      <article class="reflection-card">
        <span>当前判断</span>
        <p>{{ currentJudgment }}</p>
      </article>
      <article class="reflection-card tone-user">
        <span>用户原话</span>
        <p>{{ primaryUserStatement }}</p>
      </article>
      <article class="reflection-card tone-ai">
        <span>证据风险</span>
        <p>{{ evidenceRisk }}</p>
      </article>
      <article class="reflection-card tone-graph">
        <span>下一步验证</span>
        <p>{{ validationQuestion }}</p>
      </article>
    </div>

    <div class="reflection-validation">
      <span>验证问题</span>
      <strong>{{ validationQuestion }}</strong>
      <button class="primary-button" type="button" @click="askValidationQuestion">继续验证</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EvidenceCard } from '../types'

const props = defineProps<{
  question: string
  answer: string
  contexts: EvidenceCard[]
  graphPaths: string[]
  nextStep: string
}>()

const emit = defineEmits<{
  askFollowUp: [question: string]
}>()

const userStatements = computed(() => props.contexts.filter((card) => card.why_saved_status === 'user-stated'))
const aiInferences = computed(() => props.contexts.filter((card) => card.why_saved_status !== 'user-stated'))

const currentJudgment = computed(() => {
  const firstBlock = cleanText(props.answer).split(/[。！？!\n]/).map((item) => item.trim()).find(Boolean)
  if (firstBlock) return firstBlock.length > 96 ? `${firstBlock.slice(0, 94)}...` : firstBlock
  return props.question ? `正在围绕「${props.question}」找回旧判断。` : '这次找回还没有形成稳定判断。'
})

const primaryUserStatement = computed(() => {
  const card = userStatements.value.find((item) => cleanText(item.why_saved))
  if (!card) return '还没有用户原话支撑；需要补一句当时为什么保存。'
  const reason = cleanText(card.why_saved)
  return `${card.title}：${reason}`
})

const evidenceRisk = computed(() => {
  if (!props.contexts.length) return '没有可靠材料进入这次回答，不能把它当成旧判断。'
  if (!userStatements.value.length) return '主要依赖 AI 推断，需要用户确认它是否真的代表当时意图。'
  if (aiInferences.value.length > userStatements.value.length) {
    return `AI 推断有 ${aiInferences.value.length} 条，多于用户原话；下一步应先核对推断是否成立。`
  }
  if (!props.graphPaths.length) return '材料有了，但图谱路径不足；需要补关系或继续收集相邻证据。'
  return '用户原话、材料和图谱路径都有支撑，可以继续验证这个判断今天是否仍然成立。'
})

const validationQuestion = computed(() => {
  const next = cleanText(props.nextStep).replace(/^Open loop:\s*/i, '').replace(/^Todo:\s*/i, '')
  if (next) return `继续验证：${next}`
  const aiCard = aiInferences.value[0]
  if (aiCard) return `「${aiCard.title}」里的 AI 推断，哪些需要我确认或改写？`
  const userCard = userStatements.value[0]
  if (userCard) return `「${userCard.title}」这条用户原话，今天还支持同一个判断吗？`
  return props.question ? `这个问题还有哪些证据没有被找回来：${props.question}` : '这次找回还有哪些证据需要补充？'
})

function askValidationQuestion() {
  emit('askFollowUp', validationQuestion.value)
}

function cleanText(value: string) {
  return (value || '')
    .replace(/^#+\s*/gm, '')
    .replace(/^AI-inferred:\s*/i, '')
    .replace(/\s+/g, ' ')
    .trim()
}
</script>
