<template>
  <section v-if="item?.sourceId" class="review-decision-panel" aria-label="AI 推断审查">
    <div class="review-decision-head">
      <div>
        <span>AI 推断审查</span>
        <strong>{{ item.title }}</strong>
      </div>
      <small>{{ statusLabel }}</small>
    </div>

    <p class="review-decision-copy">{{ item.originalWhySaved || item.detail }}</p>

    <label class="review-rewrite-box">
      <span>改写为你的真实保存理由</span>
      <textarea v-model="rewriteText" rows="3" placeholder="例如：我保存它是因为..." />
    </label>

    <div class="review-decision-actions">
      <button class="primary-button" type="button" @click="confirmReview">确认</button>
      <button class="paper-button" type="button" :disabled="!rewriteText.trim()" @click="rewriteReview">改写</button>
      <button class="ghost-button danger" type="button" @click="rejectReview">拒绝</button>
      <button class="ghost-button" type="button" @click="deferReview">稍后处理</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ReviewDecisionPayload, ReviewQueueItem } from './reviewQueueTypes'

const props = defineProps<{
  item: ReviewQueueItem | null
}>()

const emit = defineEmits<{
  decide: [decision: ReviewDecisionPayload]
}>()

const rewriteText = ref('')

const statusLabel = computed(() => {
  if (!props.item?.reviewStatus || props.item.reviewStatus === 'unreviewed') return '未审查'
  if (props.item.reviewStatus === 'confirmed') return '已确认'
  if (props.item.reviewStatus === 'rewritten') return '已改写'
  if (props.item.reviewStatus === 'rejected') return '已拒绝'
  if (props.item.reviewStatus === 'deferred') return '稍后处理'
  return props.item.reviewStatus
})

watch(
  () => props.item?.key,
  () => {
    rewriteText.value = ''
  },
)

function confirmReview() {
  if (!props.item?.sourceId) return
  emit('decide', {
    sourceId: props.item.sourceId,
    review_status: 'confirmed',
    review_note: '用户确认这个 AI 推断符合当时的保存意图。',
  })
}

function rewriteReview() {
  if (!props.item?.sourceId) return
  emit('decide', {
    sourceId: props.item.sourceId,
    review_status: 'rewritten',
    why_saved: rewriteText.value.trim(),
    review_note: '用户把 AI 推断改写成了自己的保存理由。',
  })
}

function rejectReview() {
  if (!props.item?.sourceId) return
  emit('decide', {
    sourceId: props.item.sourceId,
    review_status: 'rejected',
    review_note: '用户拒绝这个 AI 推断，它不能代表真实保存意图。',
  })
}

function deferReview() {
  if (!props.item?.sourceId) return
  emit('decide', {
    sourceId: props.item.sourceId,
    review_status: 'deferred',
    review_note: '用户暂时保留这个 AI 推断，稍后再处理。',
  })
}
</script>
