<template>
  <section class="recall-evidence-ladder">
    <div class="recall-panel-head">
      <div>
        <span class="section-kicker">证据阶梯</span>
        <h3>先看用户原话，再看材料和图谱路径</h3>
      </div>
      <span>{{ items.length }} 条证据</span>
    </div>

    <div v-if="items.length" class="recall-evidence-list">
      <article
        v-for="item in items"
        :key="item.id"
        class="recall-evidence-step"
        :class="[`kind-${item.kind}`, `tone-${item.tone}`]"
      >
        <div class="recall-evidence-index">{{ kindLabel(item.kind) }}</div>
        <div>
          <div class="recall-evidence-title-row">
            <strong>{{ item.title }}</strong>
            <small v-if="item.space_name">{{ item.space_name }}</small>
          </div>
          <p>{{ item.body || emptyText(item.kind) }}</p>
          <div v-if="item.metadata?.open_loops?.length" class="recall-evidence-meta">
            {{ item.metadata.open_loops.length }} 个没处理完的问题
          </div>
        </div>
      </article>
    </div>

    <p v-else class="subtle-empty-state">这次回答没有可展示的本地证据。</p>
  </section>
</template>

<script setup lang="ts">
import type { RecallEvidenceItem, RecallEvidenceKind } from '../types'

defineProps<{
  items: RecallEvidenceItem[]
}>()

function kindLabel(kind: RecallEvidenceKind) {
  if (kind === 'user_anchor') return '原话'
  if (kind === 'ai_inference') return '推断'
  if (kind === 'graph_path') return '路径'
  return '材料'
}

function emptyText(kind: RecallEvidenceKind) {
  if (kind === 'graph_path') return '这条图谱路径暂时没有更详细的说明。'
  return '这条证据暂时没有可展示的摘要。'
}
</script>
