<template>
  <div ref="root" class="rich-markdown" v-html="renderedHtml"></div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const props = defineProps<{
  markdown: string
}>()

const root = ref<HTMLElement | null>(null)
let mermaidApi: Awaited<typeof import('mermaid')>['default'] | null = null
let mermaidReady = false
const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: false,
})

markdown.use(mathPlugin)
markdown.use(iconPlugin)

const defaultFence = markdown.renderer.rules.fence
markdown.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  const info = token.info.trim().split(/\s+/)[0]
  if (info === 'mermaid') {
    const code = markdown.utils.escapeHtml(token.content)
    return `<div class="rich-mermaid" data-mermaid-pending="true"><pre><code>${code}</code></pre></div>`
  }
  return defaultFence ? defaultFence(tokens, idx, options, env, self) : self.renderToken(tokens, idx, options)
}

const defaultLinkOpen = markdown.renderer.rules.link_open
markdown.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const token = tokens[idx]
  token.attrSet('target', '_blank')
  token.attrSet('rel', 'noreferrer')
  return defaultLinkOpen ? defaultLinkOpen(tokens, idx, options, env, self) : self.renderToken(tokens, idx, options)
}

const renderedHtml = computed(() => markdown.render(props.markdown || ''))

watch(renderedHtml, () => {
  void renderMermaidBlocks()
})

onMounted(() => {
  void renderMermaidBlocks()
})

async function renderMermaidBlocks() {
  await nextTick()
  const blocks = Array.from(root.value?.querySelectorAll<HTMLElement>('.rich-mermaid[data-mermaid-pending="true"]') || [])
  if (!blocks.length) return
  const mermaid = await getMermaid()
  await Promise.all(blocks.map(async (block, index) => {
    const code = block.textContent || ''
    const id = `snapgraph-mermaid-${Date.now()}-${index}`
    try {
      const { svg } = await mermaid.render(id, code)
      block.innerHTML = svg
      block.removeAttribute('data-mermaid-pending')
      block.classList.add('is-rendered')
    } catch {
      block.removeAttribute('data-mermaid-pending')
      block.classList.add('has-error')
    }
  }))
}

async function getMermaid() {
  if (!mermaidApi) {
    mermaidApi = (await import('mermaid')).default
  }
  if (!mermaidReady) {
    mermaidApi.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'base',
      themeVariables: {
        background: '#fffdf9',
        primaryColor: '#f5f2ea',
        primaryTextColor: '#1c1816',
        primaryBorderColor: '#d8cbb8',
        lineColor: '#8f7a68',
        secondaryColor: '#fff8ef',
        tertiaryColor: '#fdfcf9',
        fontFamily: 'Inter, PingFang SC, sans-serif',
      },
    })
    mermaidReady = true
  }
  return mermaidApi
}

function renderMath(source: string, displayMode: boolean) {
  try {
    return katex.renderToString(source, {
      displayMode,
      throwOnError: false,
      strict: 'ignore',
      trust: false,
    })
  } catch {
    return `<code>${markdown.utils.escapeHtml(source)}</code>`
  }
}

function mathPlugin(md: MarkdownIt) {
  md.inline.ruler.before('escape', 'math_inline', (state, silent) => {
    const start = state.pos
    if (state.src[start] !== '$' || state.src[start + 1] === '$') return false
    let end = start + 1
    while ((end = state.src.indexOf('$', end)) !== -1) {
      if (state.src[end - 1] !== '\\') break
      end += 1
    }
    if (end === -1 || end === start + 1) return false
    if (!silent) {
      const token = state.push('math_inline', 'math', 0)
      token.content = state.src.slice(start + 1, end)
    }
    state.pos = end + 1
    return true
  })

  md.block.ruler.before('fence', 'math_block', (state, startLine, endLine, silent) => {
    const start = state.bMarks[startLine] + state.tShift[startLine]
    const max = state.eMarks[startLine]
    const firstLine = state.src.slice(start, max).trim()
    if (!firstLine.startsWith('$$')) return false
    if (silent) return true

    const lines: string[] = []
    let nextLine = startLine
    const firstContent = firstLine.slice(2).trim()
    if (firstContent.endsWith('$$') && firstContent.length > 2) {
      lines.push(firstContent.slice(0, -2).trim())
    } else {
      if (firstContent) lines.push(firstContent)
      for (nextLine = startLine + 1; nextLine < endLine; nextLine += 1) {
        const lineStart = state.bMarks[nextLine] + state.tShift[nextLine]
        const lineMax = state.eMarks[nextLine]
        const line = state.src.slice(lineStart, lineMax)
        if (line.trim().endsWith('$$')) {
          lines.push(line.replace(/\$\$\s*$/, ''))
          break
        }
        lines.push(line)
      }
    }

    const token = state.push('math_block', 'math', 0)
    token.block = true
    token.content = lines.join('\n').trim()
    state.line = Math.min(nextLine + 1, endLine)
    return true
  })

  md.renderer.rules.math_inline = (tokens, idx) => renderMath(tokens[idx].content, false)
  md.renderer.rules.math_block = (tokens, idx) => `<div class="math-block">${renderMath(tokens[idx].content, true)}</div>`
}

function iconPlugin(md: MarkdownIt) {
  const allowed = new Set(['file', 'search', 'spark', 'check', 'warning', 'link', 'brain', 'table', 'code', 'graph'])
  md.inline.ruler.before('emphasis', 'snap_icon', (state, silent) => {
    const match = state.src.slice(state.pos).match(/^\[icon:([a-z-]+)\]/)
    if (!match || !allowed.has(match[1])) return false
    if (!silent) {
      const token = state.push('html_inline', '', 0)
      token.content = `<span class="md-icon md-icon-${match[1]}" aria-hidden="true"></span>`
    }
    state.pos += match[0].length
    return true
  })
}
</script>
