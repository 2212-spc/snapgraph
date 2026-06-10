<template>
  <section class="recall-writeback-preview">
    <div class="recall-panel-head">
      <div>
        <span class="section-kicker">写回预览</span>
        <h3>这次值得保存回 wiki 的内容</h3>
      </div>
      <span>{{ preview.source_ids.length }} 个来源</span>
    </div>

    <div class="writeback-preview-body">
      <article>
        <strong>判断</strong>
        <p>{{ preview.judgment || '这次还没有形成足够稳定的判断。' }}</p>
      </article>
      <article>
        <strong>下一步</strong>
        <p>{{ preview.next_step || '暂无明确下一步。' }}</p>
      </article>
      <article>
        <strong>来源</strong>
        <p>{{ preview.source_ids.join(' · ') || '没有可写回的来源。' }}</p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { RecallProjection } from '../types'

defineProps<{
  preview: RecallProjection['write_back_preview']
}>()
</script>

