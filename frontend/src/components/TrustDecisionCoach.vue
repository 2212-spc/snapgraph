<template>
  <section class="trust-decision-coach">
    <div class="trust-decision-coach-head">
      <div>
        <span class="section-kicker">你的判断</span>
        <h4>这条理由能不能长期保存？</h4>
      </div>
      <strong>{{ selectedActionLabel }}</strong>
    </div>

    <div class="trust-decision-options" role="list" aria-label="审查动作说明">
      <button
        v-for="option in detail.item.decision_options"
        :key="option.action"
        type="button"
        :class="{ active: selectedAction === option.action }"
        @click="selectedAction = option.action"
      >
        <strong>{{ decisionActionLabel(option.action) }}</strong>
      </button>
    </div>

    <p class="trust-decision-current-help">{{ selectedActionHelp }}</p>

    <details class="trust-decision-note-drawer" :open="needsDraftDetails">
      <summary>
        <span>补充说明</span>
        <strong>{{ noteDrawerLabel }}</strong>
      </summary>

      <label class="trust-decision-field">
        <span>审查备注</span>
        <textarea v-model="note" placeholder="说明你为什么这样判断，后续可以回溯。" />
      </label>

      <label v-if="selectedAction === 'rewritten'" class="trust-decision-field" data-required="true">
        <span>改写后的保存理由</span>
        <textarea v-model="rewriteText" placeholder="如果要改写 AI 猜测，在这里写成用户确认过的理由。" />
      </label>
    </details>

    <p v-if="validationMessage" class="trust-decision-validation">{{ validationMessage }}</p>

    <div class="trust-decision-submit-row">
      <button class="paper-button" type="button" :disabled="busy" @click="resetDraft">清空</button>
      <button class="primary-button" type="button" :disabled="busy || Boolean(validationMessage)" @click="submitSelected">
        {{ selectedActionLabel }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { decisionActionDescription, decisionActionLabel } from './trustCenterCopy'
import type { TrustBatchPayload, TrustReviewDetailPayload, TrustReviewStatus } from './trustCenterTypes'

const props = defineProps<{
  detail: TrustReviewDetailPayload
  busy: boolean
}>()

const emit = defineEmits<{
  batchAction: [payload: TrustBatchPayload]
}>()

const selectedAction = ref<Exclude<TrustReviewStatus, 'unreviewed'>>('confirmed')
const note = ref('')
const rewriteText = ref('')

const selectedActionLabel = computed(() => decisionActionLabel(selectedAction.value))
const selectedActionHelp = computed(() => decisionActionDescription(selectedAction.value))

const selectedOption = computed(() => {
  return props.detail.item.decision_options.find((option) => option.action === selectedAction.value)
})
const needsDraftDetails = computed(() => Boolean(selectedOption.value?.requires_note || selectedOption.value?.requires_rewrite))
const noteDrawerLabel = computed(() => {
  if (selectedOption.value?.requires_rewrite) return '需要改写理由'
  if (selectedOption.value?.requires_note) return '建议写备注'
  return note.value ? '已有备注' : '可选'
})

const validationMessage = computed(() => {
  if (selectedOption.value?.requires_rewrite && !rewriteText.value.trim()) {
    return '改写需要填写新的保存理由。'
  }
  if (selectedOption.value?.requires_note && !note.value.trim()) {
    return '这个高风险动作建议留下审查备注。'
  }
  return ''
})

watch(
  () => props.detail.item.source_id,
  () => {
    selectedAction.value = 'confirmed'
    resetDraft()
  },
)

function submitSelected() {
  if (selectedAction.value === 'rewritten') {
    submitRewrite()
    return
  }
  emit('batchAction', {
    source_ids: [props.detail.item.source_id],
    action: selectedAction.value,
    note: note.value.trim(),
  })
  resetDraft()
}

function submitRewrite() {
  if (!rewriteText.value.trim()) return
  emit('batchAction', {
    source_ids: [props.detail.item.source_id],
    action: 'rewritten',
    note: note.value.trim(),
    rewrites: {
      [props.detail.item.source_id]: rewriteText.value.trim(),
    },
  })
  resetDraft()
}

function resetDraft() {
  note.value = ''
  rewriteText.value = ''
}
</script>
