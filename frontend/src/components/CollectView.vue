<template>
  <section class="layer-view collect-view">
    <div class="layer-head">
      <p class="eyebrow">收集</p>
      <h1>把材料放进图谱</h1>
      <p>截图、PDF、网页和摘录先进入图谱；解析、摘要、连边和归类交给后端处理。</p>
    </div>

    <section class="collect-card" @dragover.prevent @drop.prevent="onDrop">
      <input
        ref="fileInput"
        class="file-input"
        type="file"
        multiple
        accept=".md,.markdown,.txt,.html,.htm,.pdf,.png,.jpg,.jpeg,.webp,.gif"
        @change="onFileSelected"
      />
      <button class="paper-button" :disabled="busy" @click="fileInput?.click()">
        <Paperclip :size="17" />
        选择文件
      </button>
      <textarea v-model="text" placeholder="也可以粘贴网页摘录、对话或一段想法。" />

      <div v-if="files.length" class="file-pills">
        <span v-for="file in files" :key="file.name + file.size">{{ file.name }}</span>
        <button class="text-button" @click="files = []">清空</button>
      </div>

      <label>
        <span>当时为什么觉得它值得留下？</span>
        <textarea v-model="why" class="why-input" placeholder="可选，但这句话会成为未来找回时最可信的线索。" />
      </label>

      <div class="route-row">
        <label>
          <span>进入图谱</span>
          <select v-model="routeMode">
            <option value="auto">AI 自动放入</option>
            <option value="manual">手动选择图谱</option>
            <option value="inbox">先放 Inbox</option>
          </select>
        </label>
        <label v-if="routeMode === 'manual'">
          <span>图谱空间</span>
          <select v-model="spaceId">
            <option v-for="space in routableSpaces" :key="space.id" :value="space.id">{{ space.name }}</option>
          </select>
        </label>
      </div>

      <footer>
        <span>{{ helperText }}</span>
        <button class="primary-button" :disabled="busy || !canSubmit" @click="submit">
          <Archive :size="17" />
          放进图谱
        </button>
      </footer>
    </section>

    <section v-if="results.length" class="queue-list">
      <article v-for="item in results" :key="item.source_id" class="queue-item">
        <span>{{ sourceType(item.type) }} · {{ item.space_name || item.graph_space_id }}</span>
        <strong>{{ item.title }}</strong>
        <p>{{ item.summary }}</p>
        <small v-if="item.routing_suggestion">
          {{ item.routing_suggestion.status === 'accepted' ? '已自动放入' : '待确认' }}：
          {{ item.routing_suggestion.reason }}
        </small>
      </article>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Archive, Paperclip } from 'lucide-vue-next'
import type { CollectPayload, GraphSpace, IngestResponse, RouteMode } from '../types'

const props = defineProps<{
  busy: boolean
  spaces: GraphSpace[]
  results: IngestResponse[]
}>()

const emit = defineEmits<{
  collect: [payload: CollectPayload]
}>()

const text = ref('')
const why = ref('')
const files = ref<File[]>([])
const routeMode = ref<RouteMode>('auto')
const spaceId = ref('default')
const fileInput = ref<HTMLInputElement | null>(null)

const routableSpaces = computed(() => props.spaces.filter((space) => space.status === 'active' && space.id !== 'inbox'))
const canSubmit = computed(() => Boolean(text.value.trim() || files.value.length))
const helperText = computed(() => {
  if (routeMode.value === 'auto') return '默认让 AI 判断图谱，低置信会留在 Inbox。'
  if (routeMode.value === 'manual') return '这次会直接进入你选择的图谱。'
  return '先留在 Inbox，之后批量整理。'
})

function submit() {
  if (!canSubmit.value) return
  emit('collect', {
    text: text.value,
    files: files.value,
    why: why.value,
    routeMode: routeMode.value,
    spaceId: spaceId.value,
  })
  text.value = ''
  why.value = ''
  files.value = []
}

function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  files.value = [...files.value, ...Array.from(input.files || [])]
  input.value = ''
}

function onDrop(event: DragEvent) {
  const dropped = Array.from(event.dataTransfer?.files || [])
  if (dropped.length) files.value = [...files.value, ...dropped]
  const droppedText = event.dataTransfer?.getData('text/plain')
  if (droppedText) text.value = [text.value, droppedText].filter(Boolean).join('\n')
}

function sourceType(type: string) {
  if (type === 'screenshot') return '图片'
  if (type === 'pdf') return 'PDF'
  if (type === 'webpage') return '网页'
  if (type === 'markdown') return 'Markdown'
  return type || '材料'
}
</script>
