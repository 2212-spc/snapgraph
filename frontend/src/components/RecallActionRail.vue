<template>
  <section class="recall-action-rail">
    <div class="recall-panel-head">
      <div>
        <span class="section-kicker">下一步动作</span>
        <h3>从这次回答继续推进</h3>
      </div>
    </div>

    <div class="recall-action-list">
      <article v-for="action in actions" :key="action.id" class="recall-action-card" :class="`kind-${action.kind}`">
        <div>
          <strong>{{ action.label }}</strong>
          <p>{{ action.detail }}</p>
        </div>
        <button
          class="paper-button"
          type="button"
          :disabled="!action.question"
          @click="runAction(action)"
        >
          {{ actionButtonLabel(action.kind) }}
        </button>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { RecallActionCard, RecallActionKind } from '../types'

defineProps<{
  actions: RecallActionCard[]
}>()

const emit = defineEmits<{
  askFollowUp: [question: string]
}>()

function runAction(action: RecallActionCard) {
  if (action.question) emit('askFollowUp', action.question)
}

function actionButtonLabel(kind: RecallActionKind) {
  if (kind === 'review') return '去复核'
  if (kind === 'save') return '保存线索'
  if (kind === 'open_loop') return '继续处理'
  if (kind === 'collect') return '先补材料'
  return '继续追问'
}
</script>

