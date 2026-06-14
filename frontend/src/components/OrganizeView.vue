<template>
  <section id="view-emerge" class="view organize-view emerge-view active">
    <div class="eyebrow">涌现 · WHAT EMERGES</div>
    <h1 class="title">把你的想法接上，<br>看看长出了什么</h1>
    <p class="lede">
      这几句不是你存的。是图谱把你<em>相隔很远的两条想法</em>接在一起，自己长出来的第三句。
      它生下来是 AI 的——<em>你认领，它才成为你的。</em>
    </p>

    <div class="rule"></div>

    <div v-if="activeTask" id="emergeWrap">
      <div class="claim-top">
        <div class="dots" id="eDots">
          <span
            v-for="(task, index) in tasks"
            :key="task.id"
            class="pdot"
            :class="{ done: task.status === 'claim', rej: task.status === 'rej' }"
            :title="`第 ${index + 1} 条`"
          ></span>
        </div>
        <span class="claim-rest">今晚 {{ tasks.length }} 条新连接 · 不急，留着也行</span>
      </div>

      <div class="deck">
        <div class="ghost-card g2"></div>
        <div class="ghost-card g1"></div>
        <div id="eCardTop" class="claim-card emerge-card" :class="{ enter: cardEntering, 'exit-l': cardExiting === 'l', 'exit-r': cardExiting === 'r' }">
          <div class="cc-head">
            <span class="tag tag-grey">{{ activeTask.tag }}</span>
            <span>{{ activeTask.when }}</span>
            <button id="eSkip" class="btn-ghost skip" type="button" :disabled="busy" @click="advance('skip', 'l')">留着再看</button>
          </div>

          <div class="emerge-sources" id="eSources">
            <div v-for="source in activeTask.sources" :key="source.when + source.quote" class="e-src">
              <span class="e-when">{{ source.when }}</span>
              <span class="e-q">「{{ source.quote }}」</span>
            </div>
            <div class="e-join">图谱把上面两条接上 ↓</div>
          </div>

          <div class="emerge-new">
            <div class="en-lbl">于是，一个你没明说过的想法浮了出来 —</div>
            <div
              id="eNew"
              ref="ideaBox"
              class="guess-text emerge-idea"
              :class="{ owned: activeTask.status === 'claim', editing }"
              :contenteditable="editing"
              @input="onEditInput"
            >
              {{ editText }}
            </div>
          </div>

          <div class="cc-evi">
            <b>怎么连的</b>　<span>{{ activeTask.evidence }}</span>
          </div>
          <div class="cc-actions">
            <button id="eClaim" class="btn btn-ink" type="button" :disabled="busy" @click="claimActive">
              {{ editing ? '存成我的想法' : '这是我的' }}
            </button>
            <button id="eEdit" class="btn btn-line" type="button" :disabled="busy" @click="toggleEdit">改两笔</button>
            <button id="eReject" class="btn-rust" type="button" :disabled="busy" @click="rejectActive">不是这样</button>
          </div>
        </div>
      </div>

      <div class="claim-foot">认领的那一刻，它从灰虚线的「AI 推的」翻成苔绿宋体的「你的」，真正长进你的图谱。</div>
    </div>

    <div v-else id="emergeDone" class="claim-done" style="display:block">
      <h3>今晚的连接，看完了。</h3>
      <p>{{ doneSummary }}</p>
      <div class="row">
        <button id="eAgainBtn" class="btn btn-line" type="button" @click="resetDeck">再连 {{ originalTaskCount || 3 }} 条</button>
        <button id="eGoShelf" class="btn btn-ink" type="button" @click="$emit('goShelf')">去图谱上看看它们</button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { Source } from '../types'
import type {
  TrustBatchPayload,
  TrustOpenLoopPayload,
  TrustOpenLoopUpdatePayload,
  TrustReviewDetailPayload,
  TrustReviewItem,
  TrustReviewPayload,
} from './trustCenterTypes'

type EmergenceSource = {
  when: string
  quote: string
}
type EmergenceStatus = 'claim' | 'rej' | 'skip' | null
type EmergenceTask = {
  id: string
  kind: 'review' | 'loop' | 'source' | 'demo'
  tag: string
  when: string
  idea: string
  evidence: string
  sources: EmergenceSource[]
  sourceId?: string
  loopId?: string
  status: EmergenceStatus
}

const props = defineProps<{
  busy: boolean
  review: TrustReviewPayload
  detail: TrustReviewDetailPayload | null
  openLoops: TrustOpenLoopPayload
  allSources: Source[]
}>()

const emit = defineEmits<{
  batchAction: [payload: TrustBatchPayload]
  updateOpenLoop: [loopId: string, payload: TrustOpenLoopUpdatePayload]
  askFromGraph: [question: string]
  openSource: [sourceId: string, target: 'raw' | 'source_page']
  goShelf: []
}>()

const tasks = ref<EmergenceTask[]>([])
const activeIndex = ref(0)
const editing = ref(false)
const editText = ref('')
const ideaBox = ref<HTMLElement | null>(null)
const cardEntering = ref(false)
const cardExiting = ref<'l' | 'r' | ''>('')
const originalTaskCount = ref(0)

const activeTask = computed(() => tasks.value[activeIndex.value] || null)
const doneSummary = computed(() => {
  const claimed = tasks.value.filter((task) => task.status === 'claim').length
  const rejected = tasks.value.filter((task) => task.status === 'rej').length
  const skipped = tasks.value.filter((task) => task.status === 'skip').length
  const parts = [`${claimed} 条认领成「你的想法」`]
  if (rejected) parts.push(`${rejected} 条退回，不入图谱`)
  if (skipped) parts.push(`${skipped} 条留着明天再看`)
  return `${parts.join('，')}。没有数字催你，它们会等。`
})

watch(
  () => [props.review.items, props.openLoops.items, props.allSources],
  () => resetDeck(),
  { immediate: true, deep: true },
)

watch(activeTask, (task) => {
  editText.value = task?.idea || ''
  editing.value = false
})

function resetDeck() {
  tasks.value = buildTasks().slice(0, 3)
  originalTaskCount.value = tasks.value.length
  activeIndex.value = 0
  editText.value = activeTask.value?.idea || ''
  editing.value = false
  enterCard()
}

function buildTasks(): EmergenceTask[] {
  const reviewTasks = props.review.items
    .filter((item) => item.needs_review || item.review_status === 'unreviewed' || item.review_status === 'deferred')
    .slice(0, 2)
    .map(reviewToTask)
  const loopTasks = props.openLoops.items
    .filter((loop) => loop.state === 'active' || loop.state === 'next')
    .slice(0, 1)
    .map((loop) => ({
      id: `loop:${loop.loop_id}`,
      kind: 'loop' as const,
      tag: '还没处理完的问题',
      when: loopStateLabel(loop.state),
      idea: `这个问题还没有闭环：${loop.text}。如果现在继续追问，它可能会把散在材料里的判断接成一条更稳的线。`,
      evidence: loop.note || `${loop.evidence_count} 条来源线索，还没有被你标成已解决。`,
      sources: (loop.source_titles.length ? loop.source_titles : ['未命名材料']).slice(0, 2).map((title, index) => ({
        when: index === 0 ? '旧材料' : '相关材料',
        quote: title,
      })),
      loopId: loop.loop_id,
      status: null,
    }))
  const sourceTasks = props.allSources
    .filter((source) => source.why_saved_status === 'AI-inferred' || !source.why_saved || source.graph_space_id === 'inbox')
    .slice(0, 1)
    .map(sourceToTask)
  const built = [...reviewTasks, ...loopTasks, ...sourceTasks]
  return built.length ? built : demoTasks()
}

function reviewToTask(item: TrustReviewItem): EmergenceTask {
  const sourceHints = [
    item.summary || item.title,
    item.why_saved || item.recommended_action || '这条保存理由还需要你确认。',
  ].filter(Boolean)
  return {
    id: `review:${item.source_id}`,
    kind: 'review',
    tag: item.why_saved_status === 'user-stated' ? '用户写过理由' : 'AI 猜的理由',
    when: formatDate(item.imported_at),
    idea: item.why_saved || `这份材料可能和「${item.title}」有关，但这句话还只是 AI 猜的。`,
    evidence: item.risk_reasons?.[0] || item.recommended_action || '证据还没有被你认领，因此不会当成你的真实意图。',
    sources: sourceHints.slice(0, 2).map((quote, index) => ({
      when: index === 0 ? '材料摘要' : '保存理由',
      quote: compactText(cleanTrustText(quote), 90),
    })),
    sourceId: item.source_id,
    status: null,
  }
}

function sourceToTask(source: Source): EmergenceTask {
  return {
    id: `source:${source.id}`,
    kind: 'source',
    tag: '新材料',
    when: formatDate(source.imported_at),
    idea: source.why_saved || `这份材料刚收进来，还没有一句你确认过的保存理由。`,
    evidence: source.routing_reason || source.summary || '它先待整理，不会抢进图谱核心位置。',
    sources: [
      { when: '新收进来', quote: source.title },
      { when: '系统摘要', quote: compactText(source.summary || '还没有摘要。', 90) },
    ],
    sourceId: source.id,
    status: null,
  }
}

function demoTasks(): EmergenceTask[] {
  return [
    {
      id: 'demo:loop',
      kind: 'demo',
      tag: 'AI 连出来的',
      when: '连接了 3 月 与 11 月',
      sources: [
        { when: '3 月 · 深夜', quote: '我总在不同笔记里重复想到同一件事，却以为是新想法。' },
        { when: '11 月 · 午后', quote: '反证之所以有用，是因为它逼我承认我变了。' },
      ],
      idea: '你真正怕的也许不是忘记，而是没察觉自己在原地打转。SnapGraph 不该只做「记得住」，更该做「让你看见自己的想法在循环」。',
      evidence: '两条都在谈「重复 / 变化」，图谱顺着「自我觉察」这个隐含主题把它们接上。',
      status: null,
    },
    {
      id: 'demo:memory',
      kind: 'demo',
      tag: 'AI 连出来的',
      when: '连接了 项目笔记 与 调研',
      sources: [
        { when: '两周前', quote: '我们的价值是让用户找回自己说过的话。' },
        { when: '上月 · 调研', quote: '人类记忆本就是重构，不是回放。' },
      ],
      idea: '如果连人脑都做不到一字不改地回放，那 SnapGraph 的「原话一字不改」就不只是技术指标，而是它能给人、人自己却给不了的东西。',
      evidence: '你的产品主张和你收藏的认知科学结论，指向同一处张力：人会篡改记忆，而你的系统不会。',
      status: null,
    },
    {
      id: 'demo:decision',
      kind: 'demo',
      tag: '新证据可能挑战旧判断',
      when: '连接了 决策 与 反馈',
      sources: [
        { when: '三个月前', quote: '先把核心做到极致，不做协作编辑。' },
        { when: '三天前', quote: '第二轮里 3 个人主动要协作。' },
      ],
      idea: '你或许不必在「做 / 不做协作」里二选一。真正变的是判断的依据，把「依据变了，所以该重估」做成产品里看得见的一条线，本身就是 SnapGraph 的杀手锏。',
      evidence: '这是你已经标过的一处矛盾；图谱把它从「冲突」升级成了「方法」。',
      status: null,
    },
  ]
}

async function toggleEdit() {
  editing.value = !editing.value
  if (editing.value) {
    await nextTick()
    ideaBox.value?.focus()
  }
}

function onEditInput(event: Event) {
  editText.value = (event.target as HTMLElement).innerText.trim()
}

function claimActive() {
  const task = activeTask.value
  if (!task) return
  if (task.kind === 'review' && task.sourceId) {
    emit('batchAction', {
      source_ids: [task.sourceId],
      action: editing.value ? 'rewritten' : 'confirmed',
      note: '在涌现卡片中认领。',
      rewrites: editing.value ? { [task.sourceId]: editText.value } : undefined,
    })
  } else if (task.kind === 'loop' && task.loopId) {
    emit('askFromGraph', editText.value || task.idea)
  }
  task.status = 'claim'
  advance('claim', 'l')
}

function rejectActive() {
  const task = activeTask.value
  if (!task) return
  if (task.kind === 'review' && task.sourceId) {
    emit('batchAction', {
      source_ids: [task.sourceId],
      action: 'rejected',
      note: '这条涌现连接不是我的想法。',
    })
  } else if (task.kind === 'loop' && task.loopId) {
    emit('updateOpenLoop', task.loopId, { state: 'dismissed', note: '在涌现中标记为不是这样。' })
  }
  advance('rej', 'r')
}

function advance(status: Exclude<EmergenceStatus, null>, dir: 'l' | 'r') {
  const task = activeTask.value
  if (!task) return
  task.status = status
  cardExiting.value = dir
  editing.value = false
  window.setTimeout(() => {
    cardExiting.value = ''
    activeIndex.value += 1
    editText.value = activeTask.value?.idea || ''
    enterCard()
  }, 340)
}

function enterCard() {
  cardEntering.value = true
  window.setTimeout(() => {
    cardEntering.value = false
  }, 40)
}

function loopStateLabel(state: string) {
  if (state === 'next') return '已经有下一步'
  if (state === 'resolved') return '已解决'
  if (state === 'dismissed') return '已搁置'
  return '还需要判断'
}

function formatDate(value?: string) {
  if (!value) return '最近'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '最近'
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function cleanTrustText(text: string) {
  return text
    .replace(/\bAI-inferred\b/g, 'AI 猜的理由')
    .replace(/\buser-stated\b/g, '用户写过理由')
    .replace(/\bopen loop\b/gi, '还没处理完的问题')
    .replace(/\s+/g, ' ')
    .trim()
}

function compactText(text: string, limit: number) {
  const cleaned = cleanTrustText(text)
  return cleaned.length <= limit ? cleaned : `${cleaned.slice(0, limit).trim()}…`
}
</script>
