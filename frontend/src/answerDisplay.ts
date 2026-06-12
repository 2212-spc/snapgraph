const hiddenAnswerSectionTitles = new Set([
  '找回的原话',
  '相关材料',
  '连接路径',
  '检索诊断',
])

type MarkdownHeading = {
  level: number
  title: string
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
