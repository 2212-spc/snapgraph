<template>
  <section class="recall-result">
    <div class="result-kicker">记忆找回</div>
    <h2>{{ hasEvidence ? '找到了这些线索' : '还没有足够线索' }}</h2>

    <div class="result-grid">
      <article class="result-panel primary">
        <span>找回的原话</span>
        <template v-if="originalLines.length">
          <p v-for="line in originalLines" :key="line">{{ line }}</p>
        </template>
        <p v-else>没有用户原话。当前结果只能作为低置信度提示。</p>
      </article>

      <article class="result-panel">
        <span>涌现洞见</span>
        <p>{{ insightText }}</p>
      </article>
    </div>

    <article class="result-panel wide">
      <span>相关材料</span>
      <div class="material-list" v-if="materials.length">
        <div v-for="card in materials" :key="card.source_id" class="material-row">
          <strong>{{ card.title }}</strong>
          <small :class="card.why_saved_status === 'user-stated' ? 'status-user' : 'status-ai'">
            {{ card.why_saved_status === 'user-stated' ? '用户原话' : 'AI 推断' }} · {{ card.space_name || '图谱' }}
          </small>
          <p>{{ displayReason(card.why_saved || card.source_excerpt, card.why_saved_status) }}</p>
        </div>
      </div>
      <p v-else>没有可靠材料。</p>
    </article>

    <div class="result-grid">
      <article class="result-panel">
        <span>连接路径</span>
        <pre>{{ connectionText }}</pre>
      </article>
      <article class="result-panel">
        <span>下一步</span>
        <p>{{ nextText }}</p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AskResponse, EvidenceCard, FocusGraph } from '../types'

const props = defineProps<{
  result: AskResponse | null
  focusGraph: FocusGraph | null
}>()

const materials = computed<EvidenceCard[]>(() => props.result?.contexts || props.focusGraph?.evidence_cards || [])
const hasEvidence = computed(() => materials.value.length > 0)
const originalLines = computed(() => {
  const fromAnswer = sectionLines('## 找回的原话')
  if (fromAnswer.length) return fromAnswer.slice(0, 3)
  return materials.value
    .filter((card) => card.why_saved_status === 'user-stated' && card.why_saved)
    .slice(0, 3)
    .map((card) => `${card.title}：${card.why_saved}`)
})
const insightText = computed(() => sectionText('## 涌现洞见') || fallbackInsight())
const nextText = computed(() => sectionText('## 下一步') || fallbackNext())
const connectionText = computed(() => {
  const text = sectionText('## 连接路径')
  if (text) return text.replace(/```text|```/g, '').trim()
  if (props.result?.graph_paths.length) return props.result.graph_paths.join('\n')
  return '还没有形成可靠连接路径。'
})

function sectionText(heading: string) {
  const markdown = props.result?.text || ''
  const start = markdown.indexOf(heading)
  if (start < 0) return ''
  const after = markdown.slice(start + heading.length)
  const next = after.search(/\n##\s+/)
  return cleanText((next >= 0 ? after.slice(0, next) : after).trim())
}

function sectionLines(heading: string) {
  return sectionText(heading)
    .split('\n')
    .map((line) => line.replace(/^[-\d.]+\s*/, '').trim())
    .filter(Boolean)
}

function fallbackInsight() {
  const userCount = materials.value.filter((card) => card.why_saved_status === 'user-stated').length
  if (!materials.value.length) return '没有证据时不生成洞见。'
  return `${userCount} 条材料带有用户原话。先沿这些原话继续追问，比从泛泛摘要开始更可靠。`
}

function fallbackNext() {
  for (const card of materials.value) {
    const loop = card.open_loops.find((item) => item && item !== 'None')
    if (loop) return loop.replace(/^Open loop:\s*/i, '').replace(/^Todo:\s*/i, '').trim()
  }
  return materials.value.length ? '回看第一条材料，确认这条保存理由现在是否仍然成立。' : '换一个更接近当时材料、项目、判断的线索再问。'
}

function displayReason(reason: string, status: string) {
  const cleaned = cleanText(reason.replace(/^AI-inferred:\s*/i, '').trim())
  if (!cleaned) return '没有可展示的理由。'
  return status === 'user-stated' ? cleaned : `系统推断：${cleaned}`
}

function cleanText(markdown: string) {
  return markdown
    .replace(/^#\s+.*$/gm, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/^---+$/gm, '')
    .trim()
}
</script>
