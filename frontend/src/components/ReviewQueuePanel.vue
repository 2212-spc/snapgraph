<template>
  <section v-if="items.length" class="space-panel review-queue-panel" aria-label="Needs Review">
    <div class="review-queue-head">
      <div>
        <p class="section-kicker">Needs Review</p>
        <h3>需要验证的假设</h3>
        <p>把系统推断、弱证据路径、空间建议和开放问题变成下一次可以验证的判断。</p>
      </div>
      <span class="review-queue-stage">define-test-decide</span>
    </div>

    <div class="review-queue-list">
      <article
        v-for="item in visibleItems"
        :key="item.key"
        class="review-queue-card"
        :class="[item.tone, reviewStatusClass(item)]"
      >
        <div class="review-queue-card-head">
          <span>{{ kindLabel(item.kind) }}</span>
          <small>{{ reviewStatusLabel(item) || item.confidenceLabel || item.stageLabel }}</small>
        </div>
        <strong>{{ item.title }}</strong>
        <p>{{ item.detail }}</p>
        <div class="review-queue-validation">
          <span>验证问题</span>
          <p>{{ item.validationQuestion }}</p>
        </div>
        <div class="review-queue-actions">
          <button class="paper-button" type="button" :disabled="!item.sourceId" @click="selectedReviewItem = item">审查</button>
          <button class="primary-button" type="button" @click="emit('ask', item)">从这里追问</button>
          <button class="paper-button" type="button" :disabled="!item.sourceId" @click="emit('focusSource', item)">看来源</button>
          <button class="ghost-button" type="button" @click="emit('openAudit', item)">进入审计</button>
        </div>
      </article>
    </div>

    <ReviewDecisionPanel
      :item="selectedReviewItem"
      @decide="emit('decide', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ReviewDecisionPanel from './ReviewDecisionPanel.vue'
import type { ReviewDecisionPayload, ReviewQueueItem, ReviewQueueItemKind } from './reviewQueueTypes'

const props = defineProps<{
  items: ReviewQueueItem[]
}>()

const emit = defineEmits<{
  ask: [item: ReviewQueueItem]
  focusSource: [item: ReviewQueueItem]
  openAudit: [item: ReviewQueueItem]
  decide: [decision: ReviewDecisionPayload]
}>()

const selectedReviewItem = ref<ReviewQueueItem | null>(null)
const visibleItems = computed(() => props.items.slice(0, 6))

watch(visibleItems, (items) => {
  if (!selectedReviewItem.value) return
  selectedReviewItem.value = items.find((item) => item.key === selectedReviewItem.value?.key) || null
})

function kindLabel(kind: ReviewQueueItemKind) {
  if (kind === 'ai-inference') return '系统推断'
  if (kind === 'weak-path') return '弱证据路径'
  if (kind === 'route-suggestion') return '空间建议'
  return '开放问题'
}

function reviewStatusClass(item: ReviewQueueItem) {
  if (item.reviewStatus === 'confirmed') return 'review-status-confirmed'
  if (item.reviewStatus === 'rewritten') return 'review-status-confirmed'
  if (item.reviewStatus === 'rejected') return 'review-status-rejected'
  if (item.reviewStatus === 'deferred') return 'review-status-deferred'
  return ''
}

function reviewStatusLabel(item: ReviewQueueItem) {
  if (item.reviewStatus === 'confirmed') return '已确认'
  if (item.reviewStatus === 'rewritten') return '已改写'
  if (item.reviewStatus === 'rejected') return '已拒绝'
  if (item.reviewStatus === 'deferred') return '稍后处理'
  return ''
}
</script>
