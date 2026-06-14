<template>
  <article class="organize-task-card recall" :class="{ selected }">
    <div class="organize-task-main">
      <div class="rh">
        <span class="organize-task-tag tag" :data-tone="tagTone">{{ tagLabel }}</span>
        <span v-for="item in meta" :key="item">{{ item }}</span>
      </div>
      <h3>{{ title }}</h3>
      <p>{{ reason }}</p>
    </div>

    <div class="organize-task-actions rs">
      <button class="primary-button" type="button" :disabled="busy" @click="$emit('primary')">
        {{ primaryLabel }}
      </button>
      <button class="text-button organize-why-button" type="button" @click="detailsOpen = !detailsOpen">
        为什么
      </button>
    </div>

    <details v-if="actions.length" class="organize-secondary-actions">
      <summary>更多操作</summary>
      <button
        v-for="action in actions"
        :key="action.id"
        type="button"
        :class="actionClass(action)"
        :disabled="busy"
        @click="handleAction(action.id)"
      >
        {{ action.label }}
      </button>
    </details>

    <form v-if="rewriteOpen" class="organize-rewrite-box" @submit.prevent="submitRewrite">
      <textarea v-model="rewriteText" :placeholder="rewritePlaceholder" />
      <div>
        <button class="ghost-button" type="button" @click="rewriteOpen = false">取消</button>
        <button class="primary-button" type="submit" :disabled="busy || !rewriteText.trim()">保存</button>
      </div>
    </form>

    <section v-if="detailsOpen" class="organize-detail-drawer">
      <div v-if="detailItems.length">
        <span>为什么这样判断</span>
        <p v-for="item in detailItems" :key="item">{{ item }}</p>
      </div>
      <div v-if="sourceItems.length">
        <span>查看来源</span>
        <p v-for="item in sourceItems" :key="item">{{ item }}</p>
      </div>
      <div v-if="advancedItems.length">
        <span>高级详情</span>
        <p v-for="item in advancedItems" :key="item">{{ item }}</p>
      </div>
    </section>
  </article>
</template>

<script setup lang="ts">
import { ref } from 'vue'

type TaskTag = 'ai' | 'user' | 'new'
type TaskAction = {
  id: string
  label: string
  tone?: 'quiet' | 'danger'
}

const props = withDefaults(defineProps<{
  title: string
  reason: string
  tag: TaskTag
  primaryLabel: string
  meta?: string[]
  actions?: TaskAction[]
  detailItems?: string[]
  sourceItems?: string[]
  advancedItems?: string[]
  rewritePlaceholder?: string
  selected?: boolean
  busy?: boolean
}>(), {
  meta: () => [],
  actions: () => [],
  detailItems: () => [],
  sourceItems: () => [],
  advancedItems: () => [],
  rewritePlaceholder: '把这条保存理由改成你愿意长期保留的说法。',
  selected: false,
  busy: false,
})

const emit = defineEmits<{
  primary: []
  action: [actionId: string]
  rewrite: [text: string]
}>()

const detailsOpen = ref(false)
const rewriteOpen = ref(false)
const rewriteText = ref('')

const tagLabelByKind: Record<TaskTag, string> = {
  ai: 'AI 猜的理由',
  user: '用户写过理由',
  new: '新材料',
}

const tagLabel = tagLabelByKind[props.tag]
const tagTone = props.tag

function actionClass(action: TaskAction) {
  return {
    'ghost-button': action.tone !== 'danger',
    'paper-button': action.tone === 'danger',
    danger: action.tone === 'danger',
  }
}

function handleAction(actionId: string) {
  if (actionId === 'rewrite' || actionId === 'add-reason') {
    rewriteOpen.value = !rewriteOpen.value
    return
  }
  emit('action', actionId)
}

function submitRewrite() {
  const text = rewriteText.value.trim()
  if (!text) return
  emit('rewrite', text)
  rewriteText.value = ''
  rewriteOpen.value = false
}
</script>
