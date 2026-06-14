<template>
  <section id="view-ask" class="view recall-home redesign-ask-view active" :class="{ 'has-result': showResult, 'is-answering': busy }">
    <template v-if="!showResult">
      <div class="eyebrow">问过去 · ASK YOUR PAST SELF</div>
      <h1 class="title">问问过去的你</h1>
      <p class="lede">
        不用记得关键词，大致问问就好。找得到，把<em>原话</em>一字不改还给你；库里没有，就替你<em>出网找回</em>；
        想听听当时的判断，它还能<em>扮演过去的你</em>——但永远标清，哪句是你的，哪句是它的。
      </p>

      <div class="rule"></div>

      <form class="ask-card recall-command" @submit.prevent="submit">
        <div class="ask-row">
          <input
            v-model="question"
            class="ask-input"
            :disabled="busy"
            :placeholder="placeholderText"
            autocomplete="off"
            autofocus
          />
          <button class="btn btn-ink recall-submit" :disabled="busy || !question.trim()">找　回</button>
        </div>

        <div class="ask-meta">
          <span>模式</span>
          <button
            v-for="item in modeOptions"
            :key="item.id"
            type="button"
            class="chip"
            :class="{ on: mode === item.id }"
            :disabled="busy"
            @click="$emit('modeChanged', item.id)"
          >
            {{ item.label }}
          </button>
          <span class="spacer"></span>
          <span>思考</span>
          <button
            v-for="item in depthOptions"
            :key="item.id"
            type="button"
            class="chip depth-chip"
            :class="{ on: depth === item.id }"
            :disabled="busy"
            @click="$emit('depthChanged', item.id)"
          >
            {{ item.label }}
          </button>
          <span>{{ statusText }}</span>
        </div>
      </form>

      <div id="homeArea" class="home-area">
      <div class="section-label">桌上最近的回执 · 问题就长在卡片上</div>
      <div class="receipts">
        <article
          v-for="(receipt, index) in receiptCards"
          :key="receipt.question"
          class="receipt"
          :style="{ '--receipt-tilt': receiptTilt(index) }"
        >
          <div class="r-date">{{ receipt.when }}</div>
          <div class="r-quote">「{{ receipt.quote }}」</div>
          <div class="r-file">{{ receipt.file }}</div>
          <div class="r-ask">
            <button type="button" :disabled="busy" @click="usePrompt(receipt.question)">
              {{ receipt.shortQuestion }}
            </button>
          </div>
        </article>
      </div>
      <p class="hint">找文件、问 AI、深度 Thought 都在同一张纸上切换；找到的本地材料可以直接打开。</p>
      </div>
    </template>

    <template v-else>
      <div class="chat-top recall-chat-top">
        <button class="t-title" type="button" :disabled="busy" @click="resetThread">
          <span>{{ chatTitle }}</span>
        </button>
        <span class="t-scope">在 <b>{{ scopeLabel }}</b> 里找 · {{ chatModeLabel }}</span>
      </div>

      <div id="thread" class="thread recall-thread stream">
        <div class="stream-inner recall-stream-inner">
          <div class="backline">
            <button class="btn-ghost" type="button" :disabled="busy" @click="resetThread">← 回到书桌</button>
          </div>

          <template v-for="turn in visibleTurns" :key="turn.turnId">
            <article class="msg user">
              <div class="u-bubble q-bubble">{{ turn.question || displayQuestion || '新对话' }}</div>
            </article>

            <article class="msg ai">
              <div class="ai-name"><span class="mk">S</span>SnapGraph</div>
              <div class="ai-body">
                <div v-if="turnBusy(turn)" class="meta-line result-stream-status" aria-live="polite">
                  <span class="status-dot" aria-hidden="true"></span>
                  <span class="tag tag-grey">{{ turn.depth === 'deep' ? (turn.currentThought ? 'Thought 已到' : '先想，再答') : '本地优先' }}</span>
                  <span class="status-copy">{{ busyStage || '正在找回本地证据。' }}</span>
                </div>

                <RecallResult
                  :result="turn.result"
                  :focus-graph="turn.focusGraph"
                  :busy="turnBusy(turn)"
                  :stages="turn.stages"
                  :question="turn.question"
                  :mode="turn.mode"
                  :depth="turn.depth"
                  :local-files="turnLocalFiles(turn)"
                  :current-thought="turn.currentThought"
                  :thought-history="thoughtHistory"
                  @ask-follow-up="askFollowUp"
                  @open-local-file="$emit('openLocalFile', $event)"
                />
              </div>
            </article>
          </template>
        </div>
      </div>

      <form class="composer-wrap recall-composer-wrap" @submit.prevent="submitFollowUp">
        <div class="composer-inner">
          <div class="suggests">
            <button
              v-for="item in composerSuggestions"
              :key="item"
              type="button"
              class="sugg"
              :disabled="busy"
              @click="askFollowUp(item)"
            >
              {{ item }}
            </button>
          </div>
          <div class="composer recall-command">
            <button class="c-tool" type="button" :disabled="busy" title="回到书桌" @click="resetThread">＋</button>
            <textarea
              v-model="followUpDraft"
              rows="1"
              class="composer-input"
              :disabled="busy"
              placeholder="问问过去的你，或一起接着想……"
              @keydown.enter.exact.prevent="submitFollowUp"
            ></textarea>
            <button
              class="c-pill"
              :class="{ on: depth === 'deep' }"
              type="button"
              :disabled="busy"
              title="显示真实 Thought 后再回答"
              @click="$emit('depthChanged', depth === 'deep' ? 'quick' : 'deep')"
            >
              扮演过去的我
            </button>
            <button class="c-send" type="submit" :disabled="busy || !followUpDraft.trim()">↑</button>
          </div>
          <div class="c-fine">你的原话用宋体苔绿弹回 · AI 的话用黑体 · 找不到会拒答，永远标清来源</div>
        </div>
      </form>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import RecallResult from './RecallResult.vue'
import type {
  AskResponse,
  FocusGraph,
  LocalFileResult,
  RecallConversationTurn,
  RecallDepth,
  RecallMode,
  RecallStage,
  RecallThought,
  ThoughtHistoryPayload,
} from '../types'

const props = defineProps<{
  busy: boolean
  busyStage: string
  mode: RecallMode
  depth: RecallDepth
  resultMode: RecallMode
  result: AskResponse | null
  focusGraph: FocusGraph | null
  stages: RecallStage[]
  currentThought?: RecallThought | null
  thoughtHistory?: ThoughtHistoryPayload | null
  currentQuestion: string
  recentQuestions?: Array<{ id: string; question: string; path?: string }>
  turns: RecallConversationTurn[]
}>()

const emit = defineEmits<{
  recall: [question: string, mode: RecallMode, depth: RecallDepth]
  modeChanged: [mode: RecallMode]
  depthChanged: [depth: RecallDepth]
  openLocalFile: [file: LocalFileResult]
  reset: []
}>()

const question = ref('')
const followUpDraft = ref('')
const modeOptions = [
  { id: 'auto' as const, label: '自动模式' },
  { id: 'files' as const, label: '文件找回' },
  { id: 'answer' as const, label: '只要回答' },
]
const depthOptions = [
  { id: 'quick' as const, label: '快速' },
  { id: 'deep' as const, label: '深度 Thought' },
]
const fallbackReceipts = [
  {
    when: '两周前 · 深夜 23:40',
    quote: '普通聊天只给答案，但它不会保存你为什么相信这个答案。',
    file: 'note_snapgraph_idea.md',
    question: '我之前为什么觉得这个方向值得做？',
    shortQuestion: '我当时为什么觉得这个方向值得做？',
  },
  {
    when: '三周前 · 午后',
    quote: '如果只是做搜索，用户会直接问 ChatGPT。我们的价值是让用户找回自己说过的话。',
    file: 'meeting_research_plan.md',
    question: '我们和普通 AI 助手的区别到底是什么？',
    shortQuestion: '我们和普通 AI 助手的区别是什么？',
  },
  {
    when: '三个月前 · 上午',
    quote: '不做协作编辑。6/8 个用户只需要导出。先把核心做到极致。',
    file: 'meeting_product_decision.md',
    question: '我当时为什么不做协作编辑？',
    shortQuestion: '我当时为什么不做协作编辑？',
  },
]

const latestTurn = computed(() => props.turns[props.turns.length - 1] || null)
const showResult = computed(() => Boolean(props.turns.length || props.result || props.focusGraph || props.busy || props.currentQuestion))
const activeResultMode = computed(() => latestTurn.value?.mode || (showResult.value ? props.resultMode : props.mode))
const displayQuestion = computed(() => props.currentQuestion || latestTurn.value?.question || props.result?.question || question.value.trim())
const legacyLocalFilesFallback = computed<LocalFileResult[]>(() => props.result?.local_files || props.focusGraph?.local_files || [])
const localFiles = computed<LocalFileResult[]>(() => latestTurn.value?.localFiles || legacyLocalFilesFallback.value)
const visibleTurns = computed<RecallConversationTurn[]>(() => {
  if (props.turns.length) return props.turns
  if (!showResult.value) return []
  return [{
    threadId: 'current',
    turnId: 'current',
    turnIndex: 1,
    question: displayQuestion.value || '新对话',
    mode: activeResultMode.value,
    depth: props.depth,
    spaceId: 'all',
    result: props.result,
    focusGraph: props.focusGraph,
    stages: props.stages,
    currentThought: props.currentThought,
    localFiles: localFiles.value,
    busy: props.busy,
  }]
})
const chatTitle = computed(() => compactTitle(displayQuestion.value || '新对话', 22))
const scopeLabel = computed(() => {
  if (activeResultMode.value === 'files') return '本地文件'
  if (activeResultMode.value === 'answer') return 'AI 回复'
  return '全部材料'
})
const chatModeLabel = computed(() => props.depth === 'deep' ? '深度 Thought' : '本地优先')
const statusText = computed(() => props.busy ? '正在找回' : nowSegment())
const statusLead = computed(() => {
  if (props.depth === 'deep') return props.currentThought ? 'Thought 已到' : '先想，再答'
  return '本地优先'
})
const placeholderText = computed(() => {
  if (props.mode === 'files') return '比如：帮我找到那份关于软件体系结构作业的材料'
  if (props.mode === 'answer') return '比如：根据这些材料，帮我整理一个判断'
  return '比如：我之前为什么觉得这个方向值得做？'
})
const receiptCards = computed(() => {
  const recent = props.recentQuestions?.slice(0, 3).map((item, index) => ({
    when: index === 0 ? '刚刚问过' : index === 1 ? '最近问过' : '早些时候',
    quote: item.question,
    file: item.path || 'SnapGraph 对话',
    question: item.question,
    shortQuestion: item.question,
  })) || []
  return recent.length >= 3 ? recent : [...recent, ...fallbackReceipts].slice(0, 3)
})
const composerSuggestions = computed(() => {
  if (activeResultMode.value === 'files') return ['换个文件名再找', '只要回答这件事']
  if (localFiles.value.length) return ['让过去的我来回答', '只打开最相关的文件']
  return ['换个问法', '改用只找文件']
})

watch(
  () => props.currentQuestion,
  (value) => {
    if (!value) followUpDraft.value = ''
  },
  { immediate: true },
)

function submit() {
  const text = question.value.trim()
  if (!text) return
  emit('recall', text, props.mode, props.depth)
}

function usePrompt(prompt: string) {
  question.value = prompt
  emit('recall', prompt, props.mode, props.depth)
}

function askFollowUp(questionText: string) {
  const text = questionText.trim()
  if (!text) return
  followUpDraft.value = ''
  emit('recall', text, activeResultMode.value, props.depth)
}

function turnBusy(turn: RecallConversationTurn) {
  return Boolean(turn.busy)
}

function turnLocalFiles(turn: RecallConversationTurn) {
  return turn.localFiles || turn.result?.local_files || turn.focusGraph?.local_files || []
}

function submitFollowUp() {
  const text = followUpDraft.value.trim()
  if (!text) return
  askFollowUp(text)
}

function resetThread() {
  question.value = ''
  followUpDraft.value = ''
  emit('reset')
}

function receiptTilt(index: number) {
  return index === 0 ? '-1deg' : index === 1 ? '.8deg' : '-.5deg'
}

function nowSegment() {
  const hour = new Date().getHours()
  const segment = hour < 5 ? '深夜' : hour < 8 ? '清晨' : hour < 12 ? '上午' : hour < 14 ? '午后' : hour < 18 ? '下午' : hour < 23 ? '夜里' : '深夜'
  return `${segment} · 本地优先 · 找不到才出网`
}

function compactTitle(value: string, limit: number) {
  const cleaned = value.replace(/\s+/g, ' ').trim()
  return cleaned.length <= limit ? cleaned : `${cleaned.slice(0, limit).trim()}…`
}
</script>
