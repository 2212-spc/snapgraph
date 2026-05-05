<template>
  <section class="recall-result">
    <article class="answer-card">
      <div class="answer-card-head">
        <div>
          <div class="result-kicker">记忆找回</div>
          <h2>这是我的回答</h2>
        </div>
        <div v-if="evidenceSummaryChips.length" class="evidence-summary">
          <span
            v-for="chip in evidenceSummaryChips"
            :key="chip.label"
            class="evidence-chip"
            :class="chip.tone"
          >
            {{ chip.label }}
          </span>
        </div>
        <p v-if="evidenceCompactSummary" class="evidence-summary-compact">
          {{ evidenceCompactSummary }}
        </p>
      </div>

      <div class="answer-question-block">
        <span class="answer-question-label">你的问题</span>
        <p class="answer-question">{{ questionText }}</p>
      </div>

      <div class="answer-card-body">
        <p v-for="block in answerBlocks" :key="block">{{ block }}</p>
      </div>
    </article>

    <div v-if="stages.length" class="agent-trace" aria-label="AI response progress">
      <div
        v-for="stage in stages"
        :key="stage.id"
        class="agent-step"
        :class="stage.status"
      >
        <i aria-hidden="true"></i>
        <div>
          <strong>{{ stage.label }}</strong>
          <small>{{ stage.detail || stageLabel(stage.status) }}</small>
        </div>
      </div>
    </div>

    <section class="evidence-chain">
      <div class="section-head">
        <div class="section-kicker">证据链</div>
        <h3>证据链</h3>
        <p>这次回答不是网页搜索，而是从你的本地记忆材料里推回来的。</p>
      </div>

      <div class="evidence-grid">
        <article class="evidence-block">
          <div class="evidence-block-head">
            <div>
              <span class="evidence-badge tone-user">user-stated / 用户原话</span>
              <strong>用户原话</strong>
            </div>
            <small v-if="userStatements.length">{{ userStatements.length }} 条</small>
          </div>

          <div v-if="userStatements.length" class="evidence-list">
            <article
              v-for="card in userStatements"
              :key="card.source_id"
              class="evidence-row evidence-row-user"
            >
              <strong>{{ card.title }}</strong>
              <p>{{ displayReason(card.why_saved || card.source_excerpt, card.why_saved_status) }}</p>
            </article>
          </div>
          <p v-else class="subtle-empty-state">这次结果里还没有稳定可用的用户原话。</p>
        </article>

        <article class="evidence-block">
          <div class="evidence-block-head">
            <div>
              <span class="evidence-badge tone-source">source / 材料</span>
              <strong>相关材料</strong>
            </div>
            <small v-if="materials.length">{{ materials.length }} 条</small>
          </div>

          <p v-if="evidenceMaterialPreview.length" class="evidence-block-caption">
            这几条材料最直接支撑了当前回答，完整列表仍放在下方。
          </p>
          <div v-if="evidenceMaterialPreview.length" class="evidence-list">
            <article
              v-for="card in evidenceMaterialPreview"
              :key="card.source_id"
              class="evidence-row"
            >
              <strong>{{ card.title }}</strong>
              <p>{{ materialSupportText(card) }}</p>
            </article>
          </div>
          <p v-else class="subtle-empty-state">还没有可展示的相关材料。</p>
        </article>

        <details class="evidence-block collapsible">
          <summary class="evidence-block-head">
            <div>
              <span class="evidence-badge tone-graph">graph-path / 图谱路径</span>
              <strong>图谱路径</strong>
            </div>
            <small>{{ graphPaths.length ? `${graphPaths.length} 条` : '暂时没有' }}</small>
          </summary>

          <div v-if="graphPaths.length" class="path-list">
            <p v-for="path in graphPaths" :key="path" class="graph-path-row">{{ path }}</p>
          </div>
          <p v-else class="subtle-empty-state">这次结果还没有稳定的图谱路径可展示。</p>
        </details>

        <details class="evidence-block collapsible">
          <summary class="evidence-block-head">
            <div>
              <span class="evidence-badge tone-ai">AI-inferred / AI 推断</span>
              <strong>AI 推断</strong>
            </div>
            <small>{{ aiInferences.length ? `${aiInferences.length} 条` : '暂时没有' }}</small>
          </summary>

          <div v-if="aiInferences.length" class="evidence-list">
            <article
              v-for="card in aiInferences"
              :key="card.source_id"
              class="evidence-row evidence-row-ai"
            >
              <strong>{{ card.title }}</strong>
              <p>{{ displayReason(card.why_saved || card.source_excerpt, card.why_saved_status) }}</p>
            </article>
          </div>
          <p v-else class="subtle-empty-state">这次回答没有额外使用 AI 推断来补足线索。</p>
        </details>
      </div>
    </section>

    <section class="result-panel wide related-materials">
      <div class="section-head compact">
        <div class="section-kicker">相关材料</div>
        <h3>相关材料</h3>
        <p>默认先展开最相关的 3 条，其余材料按需查看。</p>
      </div>

      <div v-if="visibleMaterials.length" class="source-card-list">
        <article v-for="card in visibleMaterials" :key="card.source_id" class="source-card">
          <div class="source-card-head">
            <div class="source-card-meta">
              <strong>{{ card.title }}</strong>
              <span class="evidence-badge" :class="materialTone(card)">
                {{ materialBadge(card) }}
              </span>
            </div>
            <a
              class="source-link-button"
              :href="sourceHref(card.source_id)"
              target="_blank"
              rel="noopener noreferrer"
            >
              打开来源
            </a>
          </div>
          <p>{{ displayReason(card.why_saved || card.source_excerpt, card.why_saved_status) }}</p>
        </article>

        <button
          v-if="materials.length > previewLimit"
          class="ghost-button materials-toggle"
          type="button"
          @click="showAllMaterials = !showAllMaterials"
        >
          {{ showAllMaterials ? '收起材料' : `查看全部材料（+${materials.length - previewLimit}）` }}
        </button>
      </div>
      <p v-else class="subtle-empty-state">这次找回还没有返回可展示的相关材料。</p>
    </section>

    <article v-if="nextText" class="result-panel wide recall-next-step">
      <span>下一步</span>
      <p>{{ nextText }}</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AskResponse, EvidenceCard, FocusGraph, RecallStage } from '../types'

type SummaryChip = {
  label: string
  tone: string
}

const props = defineProps<{
  result: AskResponse | null
  focusGraph: FocusGraph | null
  busy: boolean
  stages: RecallStage[]
  question: string
}>()

const previewLimit = 3
const evidenceMaterialLimit = 2
const showAllMaterials = ref(false)

const materials = computed<EvidenceCard[]>(() => props.result?.contexts || props.focusGraph?.evidence_cards || [])
const userStatements = computed(() => materials.value.filter((card) => card.why_saved_status === 'user-stated'))
const aiInferences = computed(() => materials.value.filter((card) => card.why_saved_status !== 'user-stated'))
const evidenceMaterialPreview = computed(() => materials.value.slice(0, evidenceMaterialLimit))
const visibleMaterials = computed(() => showAllMaterials.value ? materials.value : materials.value.slice(0, previewLimit))
const graphPaths = computed(() => {
  if (props.result?.graph_paths?.length) {
    return props.result.graph_paths.map((item) => item.trim()).filter(Boolean)
  }
  return sectionText('## 连接路径')
    .split('\n')
    .map((line) => line.replace(/^[-\d.]+\s*/, '').trim())
    .filter(Boolean)
})
const answerText = computed(() => normalizeAnswerText(sectionText('## AI 探索回应') || fallbackAnswerText()))
const answerBlocks = computed(() => splitBlocks(answerText.value))
const nextText = computed(() => sectionText('## 下一步') || fallbackNext())
const questionText = computed(() => props.question || props.result?.question || '正在从你的本地记忆里组织这个问题。')
const evidenceCompactSummary = computed(() => {
  const parts: string[] = []
  if (materials.value.length) parts.push(`${materials.value.length} 材料`)
  if (userStatements.value.length) parts.push(`${userStatements.value.length} 原话`)
  if (graphPaths.value.length) parts.push(`${graphPaths.value.length} 路径`)
  if (aiInferences.value.length) parts.push(`${aiInferences.value.length} 推断`)
  return parts.join(' · ')
})
const evidenceSummaryChips = computed<SummaryChip[]>(() => {
  const chips: SummaryChip[] = []
  if (materials.value.length) {
    chips.push({ label: `基于 ${materials.value.length} 条材料`, tone: 'tone-source' })
  }
  if (userStatements.value.length) {
    chips.push({ label: `${userStatements.value.length} 条用户原话`, tone: 'tone-user' })
  }
  if (graphPaths.value.length) {
    chips.push({ label: `${graphPaths.value.length} 条图谱路径`, tone: 'tone-graph' })
  }
  if (aiInferences.value.length) {
    chips.push({ label: `${aiInferences.value.length} 条 AI 推断`, tone: 'tone-ai' })
  }
  return chips
})

watch(materials, () => {
  showAllMaterials.value = false
})

function sectionText(heading: string) {
  const markdown = props.result?.text || ''
  const start = markdown.indexOf(heading)
  if (start < 0) return ''
  const after = markdown.slice(start + heading.length)
  const next = after.search(/\n##\s+/)
  return cleanText((next >= 0 ? after.slice(0, next) : after).trim())
}

function fallbackAnswerText() {
  if (!materials.value.length) {
    return '还没有足够证据支撑回答。换一个更接近旧材料、保存理由或图谱连接的问题再试一次。'
  }
  if (props.busy) {
    return '我已经先找到了本地线索，正在把这些材料、保存理由和图谱连接整理成一条可读的判断链。'
  }

  const titles = materials.value.slice(0, 3).map((card) => card.title).join('、')
  return `这次找回优先参考了 ${titles}。我会先把用户原话和关键材料对齐，再补上图谱路径与 AI 推断，让答案尽量回到你当时真正的判断依据。`
}

function normalizeAnswerText(text: string) {
  const evidenceGuidanceSentence = '其中用户原话是主要依据，AI 推断用于补充可能的连接。'
  const evidencePlaceholder = '__SNAPGRAPH_EVIDENCE_GUIDANCE__'
  const fieldPatterns = [
    /(?:当前)?(?:证据状态(?:是)?|evidence status)\s*[：:]\s*[^。！？!\n]*/gi,
    /\bwhy_saved_status\b\s*[：:]?\s*[\w-]*/gi,
    /\b(?:user[-_]stated|AI[-_]inferred|ai[-_]inferred)\b\s*[：:]?\s*\d*/gi,
  ]

  let cleaned = text
  for (const pattern of fieldPatterns) {
    cleaned = cleaned.replace(pattern, evidencePlaceholder)
  }

  const alreadyExplained = cleaned.includes(evidenceGuidanceSentence)
  let insertedGuidance = false

  return cleaned
    .replace(new RegExp(`(?:\\s*[，,；;:：-]?\\s*${evidencePlaceholder}\\s*)+`, 'g'), ` ${evidencePlaceholder} `)
    .replace(new RegExp(evidencePlaceholder, 'g'), () => {
      if (alreadyExplained || insertedGuidance) return ''
      insertedGuidance = true
      return evidenceGuidanceSentence
    })
    .replace(/\s+(?=其中用户原话是主要依据，AI 推断用于补充可能的连接。)/g, '，')
    .replace(/([；;，,])\s*(?=其中用户原话是主要依据，AI 推断用于补充可能的连接。)/g, ' ')
    .replace(/(?:其中用户原话是主要依据，AI 推断用于补充可能的连接。[。！？!\s]*){2,}/g, evidenceGuidanceSentence)
    .replace(/([。！？；，]){2,}/g, '$1')
    .replace(/[。.]{2,}/g, '。')
    .replace(/\s+([，。！？；])/g, '$1')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function fallbackNext() {
  for (const card of materials.value) {
    const loop = card.open_loops.find((item) => item && item !== 'None')
    if (loop) {
      return loop.replace(/^Open loop:\s*/i, '').replace(/^Todo:\s*/i, '').trim()
    }
  }
  return materials.value.length ? '从最相关的 1 到 2 条材料继续追问，确认这条判断今天是否仍然成立。' : ''
}

function displayReason(reason: string, status: string) {
  const cleaned = cleanText((reason || '').replace(/^AI-inferred:\s*/i, '').trim())
  if (!cleaned) {
    return '这条材料暂时还没有可直接展示的一句话摘要。'
  }
  return status === 'user-stated' ? cleaned : `系统推断：${cleaned}`
}

function materialSupportText(card: EvidenceCard) {
  const cleaned = cleanText((card.why_saved || card.source_excerpt || '').replace(/^AI-inferred:\s*/i, '').trim())
  if (!cleaned) {
    return '它说明了这条材料与当前回答有关，但暂时没有更具体的一句话摘要。'
  }
  if (card.why_saved_status === 'user-stated') {
    return `它直接说明了当时为什么会保存这条材料：${cleaned}`
  }
  if (card.why_saved_status === 'AI-inferred') {
    return `它补充了这次回答可能依赖的连接：${cleaned}`
  }
  return `它提供了这次回答所依赖的材料线索：${cleaned}`
}

function materialBadge(card: EvidenceCard) {
  if (card.why_saved_status === 'user-stated') return 'user-stated / 用户原话'
  if (card.why_saved_status === 'AI-inferred') return 'AI-inferred / AI 推断'
  return 'source / 材料'
}

function materialTone(card: EvidenceCard) {
  if (card.why_saved_status === 'user-stated') return 'tone-user'
  if (card.why_saved_status === 'AI-inferred') return 'tone-ai'
  return 'tone-source'
}

function sourceHref(sourceId: string) {
  return `/api/sources/${encodeURIComponent(sourceId)}`
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

function splitBlocks(text: string) {
  return text
    .split(/\n{2,}|\n(?=[^\n]{24,})/)
    .map((block) => block.replace(/^[-\d.]+\s*/, '').trim())
    .filter(Boolean)
}

function stageLabel(status: RecallStage['status']) {
  if (status === 'active') return '正在处理'
  if (status === 'done') return '完成'
  if (status === 'error') return '暂时失败'
  return '等待中'
}
</script>
