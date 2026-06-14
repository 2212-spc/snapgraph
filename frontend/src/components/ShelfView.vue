<template>
  <section id="view-shelf" class="view shelf-view active">
    <div class="eyebrow">书架 · THE SHELF</div>
    <h1 class="title">{{ shelfTitle }}</h1>
    <p class="lede">项目之间互不打扰。来源、历史与诊断，也都收在这一层——不占首页。</p>

    <div class="rule"></div>

    <div class="graph-wrap shelf-graph-system">
      <div class="graph-stack">
        <div class="graph-panel primary-graph-panel">
          <div class="section-label">你的图谱 · 苔绿是你认领的想法 · 灰虚线还是 AI 推的</div>
          <svg class="graph" viewBox="0 0 760 290" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="记忆图谱示意">
            <path class="g-edge" d="M150,90 C230,70 300,90 360,120" />
            <path class="g-edge" d="M150,90 C170,150 200,190 260,210" />
            <path class="g-edge" d="M360,120 C440,100 510,110 560,90" />
            <path class="g-edge" d="M360,120 C420,160 480,180 540,200" />
            <path class="g-edge" d="M260,210 C340,230 440,225 540,200" />
            <path class="g-edge contra" d="M540,200 C600,160 620,120 560,90" />
            <path class="g-edge" d="M150,90 C300,40 430,40 430,68" />
            <path class="g-edge" d="M540,200 C480,120 450,90 430,72" />
            <circle class="g-pulse" cx="430" cy="70" r="24" />
            <circle class="g-node-you" cx="150" cy="90" r="11" />
            <circle class="g-node-you" cx="260" cy="210" r="11" />
            <circle class="g-node-you" cx="560" cy="90" r="11" />
            <circle class="g-node-ai" cx="360" cy="120" r="10" />
            <circle class="g-node-ai" cx="540" cy="200" r="10" />
            <circle class="g-node-new" cx="430" cy="70" r="12" />
            <text class="g-label" x="150" y="74" text-anchor="middle">{{ graphLabels[0] }}</text>
            <text class="g-label" x="262" y="234" text-anchor="middle">{{ graphLabels[1] }}</text>
            <text class="g-label" x="560" y="74" text-anchor="middle">{{ graphLabels[2] }}</text>
            <text class="g-label ai" x="360" y="146" text-anchor="middle">AI 猜的理由</text>
            <text class="g-label ai" x="540" y="226" text-anchor="middle">未闭环问题</text>
            <text class="g-label new" x="430" y="50" text-anchor="middle">新涌现 ★</text>
          </svg>
          <div class="g-legend">
            <span><i class="you"></i>你认领的（宋体·苔绿）</span>
            <span><i class="ai"></i>AI 推的，待认领（虚线）</span>
            <span><i class="con"></i>矛盾（赤）</span>
            <span class="legend-new">★ 刚从「涌现」认领进来的新节点</span>
          </div>
        </div>

        <div class="graph-panel shelf-diagnostics-map">
          <div class="section-label">来源 · 历史 · 诊断 · 第二张图谱</div>
          <div class="diagnostic-graph">
            <svg viewBox="0 0 300 190" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="来源历史诊断图谱">
              <path class="g-edge" d="M48,96 C88,44 126,44 150,92" />
              <path class="g-edge" d="M48,96 C98,142 138,150 190,106" />
              <path class="g-edge contra" d="M190,106 C230,58 260,70 268,112" />
              <path class="g-edge" d="M150,92 C190,62 230,60 268,112" />
              <circle class="g-node-you" cx="48" cy="96" r="11" />
              <circle class="g-node-you" cx="150" cy="92" r="11" />
              <circle class="g-node-ai" cx="190" cy="106" r="10" />
              <circle class="g-node-new" cx="268" cy="112" r="12" />
              <text class="g-label" x="48" y="78" text-anchor="middle">来源 {{ allSources.length }}</text>
              <text class="g-label" x="150" y="74" text-anchor="middle">历史 {{ questions.length }}</text>
              <text class="g-label ai" x="190" y="130" text-anchor="middle">诊断 {{ diagnostics?.warnings.length || 0 }}</text>
              <text class="g-label new" x="268" y="96" text-anchor="middle">未闭环 {{ openLoops.items.length }}</text>
            </svg>
            <div class="diagnostic-stats">
              <article>
                <span>材料</span>
                <strong>{{ allSources.length }}</strong>
              </article>
              <article>
                <span>待确认</span>
                <strong>{{ review.summary.unreviewed }}</strong>
              </article>
              <article>
                <span>未闭环</span>
                <strong>{{ openLoops.items.length }}</strong>
              </article>
              <article>
                <span>诊断</span>
                <strong>{{ diagnostics ? `${diagnostics.warnings.length} 条` : '未加载' }}</strong>
              </article>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="shelf-grid">
      <article
        v-for="(space, index) in visibleSpaces"
        :key="space.id"
        class="space"
        :class="{ alt: index % 2 === 1 }"
      >
        <h3>{{ spaceDisplayName(space) }}</h3>
        <div class="stats">
          <span>{{ space.source_count || 0 }} 份材料</span>
          <span>{{ space.node_count || 0 }} 个判断</span>
          <span>{{ space.pending_suggestions || 0 }} 张回执</span>
        </div>
        <button
          v-if="index === 0 && review.summary.unreviewed"
          class="alert"
          type="button"
          @click="$emit('goEmerge')"
        >
          {{ review.summary.unreviewed }} 个判断等你认领 — 去看看
        </button>
        <div v-else class="ok">✓ 判断稳定</div>
        <div class="mats">
          <button
            v-for="source in sourcesForSpace(space.id)"
            :key="source.id"
            class="mat"
            type="button"
            @click="$emit('openSource', source.id, 'raw')"
          >
            <span class="name">{{ source.title }}</span>
            <span class="meta">{{ sourceMeta(source) }}</span>
          </button>
        </div>
      </article>

      <form class="space new-space-form" @submit.prevent="createSpace">
        <div>
          <span class="tag tag-moss">新建图谱空间</span>
          <h3>新的记忆空间</h3>
        </div>
        <input
          v-model="newSpaceName"
          class="new-space-name"
          :disabled="busy"
          placeholder="空间名"
          autocomplete="off"
        />
        <textarea
          v-model="newSpacePurpose"
          class="new-space-purpose"
          :disabled="busy"
          rows="2"
          placeholder="这个空间用来收什么？"
        ></textarea>
        <button class="btn btn-line" type="submit" :disabled="busy || !newSpaceName.trim()">建立</button>
      </form>

      <div class="inbox-card">
        <div>
          <h3>待认领</h3>
          <p>{{ inboxCopy }}</p>
        </div>
        <span class="spacer"></span>
        <button class="btn btn-line" type="button" @click="$emit('goEmerge')">去认领</button>
      </div>
    </div>

    <div class="shelf-foot">
      <details class="shelf-advanced" open>
        <summary>高级详情 — 来源 · 历史 · 诊断</summary>
        <div class="body">
          <article>
            <span>材料</span>
            <strong>{{ allSources.length }}</strong>
          </article>
          <article>
            <span>待确认</span>
            <strong>{{ review.summary.unreviewed }}</strong>
          </article>
          <article>
            <span>未闭环</span>
            <strong>{{ openLoops.items.length }}</strong>
          </article>
          <article>
            <span>诊断</span>
            <strong>{{ diagnostics ? '已加载' : '未加载' }}</strong>
          </article>
        </div>
      </details>
      <button type="button" @click="$emit('startCollect')">继续收下材料</button>
      <button type="button" @click="$emit('askFromGraph', '结合这些记忆空间，我现在最应该追问什么？')">从书架追问</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GraphSpace, SavedQuestion, Source } from '../types'
import type { TrustDiagnostics, TrustOpenLoopPayload, TrustReviewPayload } from './trustCenterTypes'

type ShelfSpace = GraphSpace & {
  source_ids?: string[]
}

const props = defineProps<{
  busy: boolean
  spaces: GraphSpace[]
  allSources: Source[]
  questions: SavedQuestion[]
  review: TrustReviewPayload
  openLoops: TrustOpenLoopPayload
  diagnostics: TrustDiagnostics | null
}>()

const emit = defineEmits<{
  askFromGraph: [question: string]
  openSource: [sourceId: string, target: 'raw' | 'source_page']
  goEmerge: []
  startCollect: []
  createSpace: [payload: { name: string; purpose?: string; description?: string; color?: string }]
}>()

const newSpaceName = ref('')
const newSpacePurpose = ref('')
const realGraphSpaces = computed<ShelfSpace[]>(() => {
  const active = props.spaces.filter((space) => space.status === 'active')
  return active.sort((a, b) => spaceSortRank(a) - spaceSortRank(b))
})
const visibleSpaces = computed<ShelfSpace[]>(() => realGraphSpaces.value.slice(0, 4))
const shelfTitle = computed(() => `${shelfCountLabel(visibleSpaces.value.length)}记忆空间`)
const graphLabels = computed(() => {
  const firstSources = props.allSources.slice(0, 3).map((source) => compact(source.title, 9))
  return [
    firstSources[0] || '不是搜索，是召回',
    firstSources[1] || '原话一字不改',
    firstSources[2] || '先做核心',
  ]
})
const inboxCopy = computed(() => {
  const inferred = props.review.summary.ai_inferred || 0
  const loops = props.openLoops.items.length
  if (inferred || loops) return `${inferred} 句「AI 猜的理由」，${loops} 个还没处理完的问题。都还是 AI 的——不进图谱，也不丢。`
  return '暂时没有必须处理的连接。你可以继续收下材料，或者从书架追问。'
})

function sourcesForSpace(spaceId: string) {
  const space = visibleSpaces.value.find((item) => item.id === spaceId)
  const matched = space?.source_ids?.length
    ? props.allSources.filter((source) => space.source_ids?.includes(source.id)).slice(0, 3)
    : props.allSources.filter((source) => source.graph_space_id === spaceId).slice(0, 3)
  return matched.length ? matched : props.allSources.slice(0, 3)
}

function spaceDisplayName(space: ShelfSpace) {
  if (space.id === 'default') return '主记忆'
  if (space.id === 'inbox') return '待整理'
  return space.name
}

function sourceMeta(source: Source) {
  if (source.why_saved_status === 'AI-inferred') return '待认领'
  if (source.why_saved_status === 'user-stated') return '回执 ×1'
  if (source.type) return source.type
  return '已备份'
}

function shelfCountLabel(count: number) {
  if (count === 1) return '一个'
  if (count === 2) return '两个'
  return `${count} 个`
}

function spaceSortRank(space: GraphSpace) {
  if (space.id === 'default') return 0
  if (space.id === 'inbox') return 1
  return 2
}

function compact(text: string, limit: number) {
  return text.length <= limit ? text : `${text.slice(0, limit)}…`
}

function createSpace() {
  const name = newSpaceName.value.trim()
  if (!name) return
  emit('createSpace', {
    name,
    purpose: newSpacePurpose.value.trim(),
    description: newSpacePurpose.value.trim(),
    color: '#5f7050',
  })
  newSpaceName.value = ''
  newSpacePurpose.value = ''
}
</script>
