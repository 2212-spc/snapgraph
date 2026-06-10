import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { filterUserFacingAnswerMarkdown } from '../frontend/src/answerDisplay.ts'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('answer display filters internal retrieval sections from the chat response', () => {
  const rawMarkdown = [
    '# 回答',
    '',
    '## 结论',
    '保留这段给用户看的判断。',
    '',
    '## 找回的原话',
    '这里是内部证据摘录。',
    '',
    '## 相关材料',
    '- source_001 / raw/wiki.md',
    '',
    '## 连接路径',
    'source -> thought -> question',
    '',
    '## AI 探索回应',
    '保留这段真正接住问题的解释，再用相关材料和图谱连接补全。',
    '',
    '## 检索诊断',
    '- top_k: 8',
    '',
    '## 下一步',
    '保留下一步行动。',
  ].join('\n')

  const displayMarkdown = filterUserFacingAnswerMarkdown(rawMarkdown)

  assert.match(displayMarkdown, /## 结论[\s\S]*保留这段给用户看的判断。/)
  assert.match(displayMarkdown, /## AI 探索回应[\s\S]*保留这段真正接住问题的解释，再用本地文件和保存关系补全。/)
  assert.match(displayMarkdown, /## 下一步[\s\S]*保留下一步行动。/)
  assert.doesNotMatch(displayMarkdown, /找回的原话/)
  assert.doesNotMatch(displayMarkdown, /相关材料/)
  assert.doesNotMatch(displayMarkdown, /连接路径/)
  assert.doesNotMatch(displayMarkdown, /检索诊断/)
  assert.doesNotMatch(displayMarkdown, /图谱连接/)
  assert.doesNotMatch(displayMarkdown, /source_001/)
  assert.doesNotMatch(displayMarkdown, /top_k/)
})

test('RecallResult defaults to local files and SnapGraph thinking', () => {
  const result = read('frontend/src/components/RecallResult.vue')
  const app = read('frontend/src/App.vue')
  const types = read('frontend/src/types.ts')
  const styles = read('frontend/src/styles.css')
  const richMarkdown = read('frontend/src/components/RichMarkdown.vue')

  assert.match(result, /local-file-results/)
  assert.match(result, /召回的本地文件/)
  assert.match(result, /snapgraph-thinking/)
  assert.match(result, /SnapGraph 的思考/)
  assert.match(result, /RichMarkdown/)
  assert.match(result, /displayAnswerMarkdown/)
  assert.match(result, /filterUserFacingAnswerMarkdown/)
  assert.match(result, /local-file-compact-card/)
  assert.match(result, /thinking-footnotes/)
  assert.match(result, /AI 推断/)
  assert.match(result, /openLocalFile/)
  assert.doesNotMatch(result, /写回预览/)
  assert.doesNotMatch(result, /需要确认的地方/)

  assert.match(app, /@open-local-file="openLocalFile"/)
  assert.match(app, /\/api\/open-local/)
  assert.match(types, /raw_path: string/)
  assert.match(types, /open_target: 'raw' \| 'source_page'/)
  assert.match(types, /local_files\?: LocalFileResult\[\]/)
  assert.match(types, /export type RecallMode = 'auto' \| 'files' \| 'answer'/)
  assert.match(styles, /\.local-file-results/)
  assert.match(styles, /\.snapgraph-thinking/)
  assert.match(styles, /--snap-title/)
  assert.match(styles, /--snap-cjk-display: var\(--snap-title\)/)
  assert.doesNotMatch(styles, /Kaiti SC/)
  assert.match(styles, /\.recall-response-stack/)
  assert.match(styles, /\.rich-markdown/)
  assert.match(styles, /\.rich-mermaid/)
  assert.match(styles, /\.math-block/)
  assert.match(styles, /\.thinking-stream-state/)
  assert.match(styles, /\.thinking-footnotes/)
  assert.match(richMarkdown, /MarkdownIt/)
  assert.match(richMarkdown, /katex\.renderToString/)
  assert.match(richMarkdown, /mermaid\.render/)
  assert.match(richMarkdown, /html: false/)
  assert.match(styles, /@media \(max-width: 860px\)[\s\S]*\.recall-response-focus\s*{[\s\S]*grid-template-columns: 1fr/)
})
