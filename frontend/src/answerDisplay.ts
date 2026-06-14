const hiddenAnswerSectionTitles = new Set([
  '找回的原话',
  '相关材料',
  '连接路径',
  '检索诊断',
])

const restoredAnswerSectionTitles = [
  '回答',
  '结论',
  '找回的原话',
  '相关材料',
  '连接路径',
  'AI 探索回应',
  '涌现洞见',
  '下一步',
  '检索诊断',
]

type MarkdownHeading = {
  level: number
  title: string
}

export function normalizeRestoredAnswerMarkdown(markdown: string) {
  const text = markdown.replace(/\r\n/g, '\n').trim()
  if (!text) return ''

  const titlePattern = restoredAnswerSectionTitles.map(escapeRegex).join('|')
  const headingPattern = new RegExp(`(#{1,6}\\s+(?:${titlePattern})(?=\\s|$))`, 'g')
  const lineHeadingPattern = new RegExp(`^(#{1,6}\\s+(?:${titlePattern}))(?:\\s+(.+))?$`)
  const withHeadingBreaks = text.replace(headingPattern, (match, heading, offset, source) => {
    if (offset === 0 || source[offset - 1] === '\n') return heading
    return `\n\n${heading}`
  })

  return withHeadingBreaks
    .split('\n')
    .map((line) => {
      const trimmed = line.trimEnd()
      const match = trimmed.match(lineHeadingPattern)
      if (!match || !match[2]) return trimmed
      return `${match[1]}\n\n${match[2]}`
    })
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export function filterUserFacingAnswerMarkdown(markdown: string) {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  const kept: string[] = []
  let hiddenUntilLevel = 0

  for (const line of lines) {
    const heading = parseMarkdownHeading(line)
    if (heading) {
      if (hiddenAnswerSectionTitles.has(heading.title)) {
        hiddenUntilLevel = heading.level
        continue
      }
      if (hiddenUntilLevel && heading.level <= hiddenUntilLevel) {
        hiddenUntilLevel = 0
      }
    }

    if (!hiddenUntilLevel) {
      kept.push(line)
    }
  }

  return polishUserFacingTerms(kept.join('\n').replace(/\n{3,}/g, '\n\n').trim())
}

function parseMarkdownHeading(line: string): MarkdownHeading | null {
  const match = line.match(/^(#{1,6})\s+(.+?)\s*#*\s*$/)
  if (!match) return null
  return {
    level: match[1].length,
    title: match[2].trim(),
  }
}

function polishUserFacingTerms(markdown: string) {
  return markdown
    .replaceAll('相关材料', '本地文件')
    .replaceAll('图谱连接', '保存关系')
    .replaceAll('连接路径', '保存关系')
    .replaceAll('检索诊断', '检索状态')
}

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
