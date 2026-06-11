<template>
  <aside class="trust-detail-panel">
    <template v-if="detail">
      <div class="trust-panel-head">
        <div>
          <span class="section-kicker">当前材料</span>
          <h3>{{ detail.item.title }}</h3>
        </div>
        <button class="ghost-button" type="button" @click="$emit('close')">关闭</button>
      </div>

      <section class="trust-detail-brief">
        <div>
          <span>{{ boundaryLabel(detail.item.why_saved_status) }}</span>
          <strong>{{ detailRiskCopy }}</strong>
        </div>
        <p>{{ cleanTrustText(detail.item.why_saved || '没有稳定保存理由。') }}</p>
        <div class="trust-review-meta">
          <span>{{ detailRiskLabel }}</span>
          <span>{{ reviewStatusLabel(detail.item.review_status) }}</span>
          <span>可信度 {{ Math.round(detail.item.confidence * 100) }}%</span>
        </div>
      </section>

      <TrustDecisionCoach
        :detail="detail"
        :busy="busy"
        @batch-action="$emit('batchAction', $event)"
      />

      <div class="trust-detail-compact-disclosures">
        <details class="trust-detail-disclosure">
          <summary>
            <span>为什么需要你看</span>
            <strong>{{ detailRiskLabel }}</strong>
          </summary>
          <TrustRiskLens :item="detail.item" />
        </details>

        <details class="trust-detail-disclosure">
          <summary>
            <span>系统简短判断</span>
            <strong>{{ analysisScoreLabel }}</strong>
          </summary>
          <TrustAnalysisDigest :detail="detail" />
        </details>
      </div>

      <details class="trust-detail-disclosure">
        <summary>
          <span>证据路径</span>
          <strong>{{ evidencePaths.length }} 条</strong>
        </summary>
        <section class="trust-detail-section">
          <div v-if="evidencePaths.length" class="trust-path-list">
            <p v-for="path in evidencePaths" :key="path.edge_id">{{ path.path }}</p>
          </div>
          <p v-else class="trust-empty">这条材料还没有可展示的图谱证据路径。</p>
        </section>
      </details>

      <details class="trust-detail-disclosure">
        <summary>
          <span>未闭环问题</span>
          <strong>{{ detail.open_loops.length }} 个</strong>
        </summary>
        <section class="trust-detail-section">
          <p v-for="loop in detail.open_loops" :key="loop.loop_id" class="trust-loop-line">
            {{ loop.text }} - {{ loopStateLabel(loop.state) }}
          </p>
          <p v-if="!detail.open_loops.length" class="trust-empty">没有关联未闭环问题。</p>
        </section>
      </details>

      <details class="trust-detail-disclosure">
        <summary>
          <span>审查历史</span>
          <strong>{{ history.length }} 条</strong>
        </summary>
        <section class="trust-detail-section">
          <div v-if="history.length" class="trust-history-list">
            <article v-for="item in history" :key="item.id">
              <strong>{{ item.action }}</strong>
              <small>{{ item.created_at }}</small>
              <p>{{ item.note || '没有备注。' }}</p>
            </article>
          </div>
          <p v-else class="trust-empty">还没有审查历史。</p>
        </section>
      </details>

    </template>
    <p v-else class="trust-empty">先从左侧选择一条材料，这里会显示保存理由、证据和判断按钮。</p>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { boundaryLabel, cleanTrustText, reviewStatusLabel, riskToneLabel } from './trustCenterCopy'
import TrustAnalysisDigest from './TrustAnalysisDigest.vue'
import TrustDecisionCoach from './TrustDecisionCoach.vue'
import TrustRiskLens from './TrustRiskLens.vue'
import type { TrustBatchPayload, TrustReviewDetailPayload } from './trustCenterTypes'

const props = defineProps<{
  detail: TrustReviewDetailPayload | null
  busy: boolean
}>()

const emit = defineEmits<{
  close: []
  batchAction: [payload: TrustBatchPayload]
}>()

const evidencePaths = computed(() => props.detail?.evidence_paths || [])
const history = computed(() => props.detail?.history || [])
const detailRiskLabel = computed(() => {
  const level = props.detail?.item.risk_level
  return level ? riskToneLabel(level) : ''
})
const analysisScoreLabel = computed(() => {
  const analysis = props.detail?.analysis || props.detail?.item.analysis
  return analysis ? `${analysis.trust_score.score} 分` : '已收起'
})
const detailRiskCopy = computed(() => {
  const item = props.detail?.item
  if (!item) return ''
  if (item.risk_level === 'critical') return '这条会直接影响回答可信度'
  if (item.risk_level === 'high') return '建议先看证据再确认'
  if (item.has_open_loops) return '它还连着未闭环问题'
  return '低压力，可以批量处理'
})

function loopStateLabel(state: string) {
  if (state === 'active') return '还需要判断'
  if (state === 'next') return '下一步'
  if (state === 'resolved') return '已解决'
  if (state === 'dismissed') return '已忽略'
  return state
}
</script>
