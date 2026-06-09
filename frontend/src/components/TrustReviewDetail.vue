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

      <section class="trust-detail-section">
        <span>当前保存理由</span>
        <p>{{ detail.item.why_saved || '没有稳定保存理由。' }}</p>
        <div class="trust-review-meta">
          <span>{{ detail.item.why_saved_status }}</span>
          <span>{{ detail.item.review_status }}</span>
          <span>{{ detail.item.risk_level }}</span>
        </div>
      </section>

      <section class="trust-detail-section">
        <span>证据路径</span>
        <div v-if="evidencePaths.length" class="trust-path-list">
          <p v-for="path in evidencePaths" :key="path.edge_id">{{ path.path }}</p>
        </div>
        <p v-else class="trust-empty">这条材料还没有可展示的图谱证据路径。</p>
      </section>

      <section class="trust-detail-section">
        <span>Open loops</span>
        <p v-for="loop in detail.open_loops" :key="loop.loop_id" class="trust-loop-line">
          {{ loop.text }} · {{ loop.state }}
        </p>
        <p v-if="!detail.open_loops.length" class="trust-empty">没有关联 open loop。</p>
      </section>

      <section class="trust-detail-section">
        <span>审查历史</span>
        <div v-if="history.length" class="trust-history-list">
          <article v-for="item in history" :key="item.id">
            <strong>{{ item.action }}</strong>
            <small>{{ item.created_at }}</small>
            <p>{{ item.note || '没有备注。' }}</p>
          </article>
        </div>
        <p v-else class="trust-empty">还没有审查历史。</p>
      </section>

      <section class="trust-detail-section trust-detail-actions">
        <span>单项动作</span>
        <textarea v-model="note" placeholder="说明你为什么这样判断" />
        <textarea v-model="rewriteText" placeholder="如果要改写 AI 推断，在这里写用户确认过的理由" />
        <div class="trust-detail-button-row">
          <button class="paper-button" type="button" :disabled="busy" @click="submit('deferred')">稍后</button>
          <button class="paper-button danger" type="button" :disabled="busy" @click="submit('rejected')">拒绝</button>
          <button class="paper-button" type="button" :disabled="busy || !rewriteText.trim()" @click="submitRewrite">改写</button>
          <button class="primary-button" type="button" :disabled="busy" @click="submit('confirmed')">确认</button>
        </div>
      </section>
    </template>
    <p v-else class="trust-empty">从左侧队列选择一条材料查看证据。</p>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { TrustBatchPayload, TrustReviewDetailPayload } from './trustCenterTypes'

const props = defineProps<{
  detail: TrustReviewDetailPayload | null
  busy: boolean
}>()

const emit = defineEmits<{
  close: []
  batchAction: [payload: TrustBatchPayload]
}>()

const note = ref('')
const rewriteText = ref('')
const evidencePaths = computed(() => props.detail?.evidence_paths || [])
const history = computed(() => props.detail?.history || [])

watch(
  () => props.detail?.item.source_id,
  () => {
    note.value = ''
    rewriteText.value = ''
  },
)

function submit(action: TrustBatchPayload['action']) {
  if (!props.detail) return
  emit('batchAction', {
    source_ids: [props.detail.item.source_id],
    action,
    note: note.value.trim(),
  })
}

function submitRewrite() {
  if (!props.detail || !rewriteText.value.trim()) return
  emit('batchAction', {
    source_ids: [props.detail.item.source_id],
    action: 'rewritten',
    note: note.value.trim(),
    rewrites: {
      [props.detail.item.source_id]: rewriteText.value.trim(),
    },
  })
}
</script>
