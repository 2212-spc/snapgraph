<template>
  <section class="trust-batch-bar" :data-empty="!sourceIds.length">
    <div>
      <span>批量审查</span>
      <strong>{{ sourceIds.length ? `${sourceIds.length} 条已选择` : '选择队列项后操作' }}</strong>
    </div>
    <input
      v-model="note"
      :disabled="busy || !sourceIds.length"
      placeholder="给这次判断留一句审查说明"
    />
    <div class="trust-batch-actions">
      <button class="paper-button" type="button" :disabled="disabled" @click="submit('deferred')">稍后</button>
      <button class="paper-button danger" type="button" :disabled="disabled" @click="submit('rejected')">拒绝</button>
      <button class="primary-button" type="button" :disabled="disabled" @click="submit('confirmed')">确认</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TrustBatchPayload } from './trustCenterTypes'

const props = defineProps<{
  sourceIds: string[]
  busy: boolean
}>()

const emit = defineEmits<{
  batchAction: [payload: TrustBatchPayload]
}>()

const note = ref('')
const disabled = computed(() => props.busy || !props.sourceIds.length)

function submit(action: TrustBatchPayload['action']) {
  if (disabled.value) return
  emit('batchAction', {
    source_ids: props.sourceIds,
    action,
    note: note.value.trim(),
  })
  note.value = ''
}
</script>
