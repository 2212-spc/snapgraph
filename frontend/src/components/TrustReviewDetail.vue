<template>
  <aside class="trust-detail-panel">
    <template v-if="detail">
      <div class="trust-panel-head">
        <div>
          <span class="section-kicker">Evidence Detail</span>
          <h3>{{ detail.item.title }}</h3>
        </div>
        <button class="ghost-button" type="button" @click="$emit('close')">关闭</button>
      </div>

      <section class="trust-detail-brief">
        <div>
          <span>{{ boundaryLabel(detail.item.why_saved_status) }}</span>
          <strong>{{ detailRiskCopy }}</strong>
        </div>
        <p>{{ detail.item.why_saved || '没有稳定保存理由。' }}</p>
        <div class="trust-review-meta">
          <span>{{ detail.item.risk_level }}</span>
          <span>{{ detail.item.review_status }}</span>
          <span>可信度 {{ Math.round(detail.item.confidence * 100) }}%</span>
        </div>
      </section>

      <TrustReviewSignals :item="detail.item" />

      <TrustRiskLens :item="detail.item" />

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
          <span>Open loops</span>
          <strong>{{ detail.open_loops.length }} 个</strong>
        </summary>
        <section class="trust-detail-section">
          <p v-for="loop in detail.open_loops" :key="loop.loop_id" class="trust-loop-line">
            {{ loop.text }} · {{ loop.state }}
          </p>
          <p v-if="!detail.open_loops.length" class="trust-empty">没有关联 open loop。</p>
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

      <TrustDecisionCoach
        :detail="detail"
        :busy="busy"
        @batch-action="$emit('batchAction', $event)"
      />
    </template>
    <p v-else class="trust-empty">从左侧队列选择一条材料查看证据。</p>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { boundaryLabel } from './trustCenterCopy'
import TrustDecisionCoach from './TrustDecisionCoach.vue'
import TrustReviewSignals from './TrustReviewSignals.vue'
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
const detailRiskCopy = computed(() => {
  const item = props.detail?.item
  if (!item) return ''
  if (item.risk_level === 'critical') return '这条会直接影响回答可信度'
  if (item.risk_level === 'high') return '建议先看证据再确认'
  if (item.has_open_loops) return '它还连着未闭环问题'
  return '低压力，可以批量处理'
})
</script>
