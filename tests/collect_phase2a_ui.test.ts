import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('CollectView includes ingest progress and memory receipt UX', () => {
  const file = read('frontend/src/components/CollectView.vue')

  assert.match(file, /SnapGraph 会解析、摘要、连边，并把保存理由留作未来找回的线索。/)
  assert.match(file, /ingest-progress/)
  assert.match(file, /先把材料收进来，再整理摘要、保存理由和可能连接。/)
  assert.match(file, /记忆回执/)
  assert.match(file, /保存为/)
  assert.match(file, /保存理由/)
  assert.match(file, /进入图谱/)
  assert.match(file, /系统理解/)
  assert.match(file, /建议连接/)
  assert.match(file, /查看所在图谱/)
  assert.match(file, /继续收集/)
  assert.match(file, /查看材料详情/)
  assert.match(file, /receipt-source-detail/)
  assert.match(file, /getReceiptUnderstanding/)
  assert.match(file, /normalizeReceiptSummary/)
  assert.match(file, /这份材料已经被保存，并可作为之后找回相关判断的线索。/)
  assert.match(file, /emit\('openSpace', space\)/)
})

test('styles include collect receipt and ingest progress classes', () => {
  const file = read('frontend/src/styles.css')

  assert.match(file, /\.ingest-progress/)
  assert.match(file, /\.ingest-step/)
  assert.match(file, /\.memory-receipt/)
  assert.match(file, /\.receipt-section/)
  assert.match(file, /\.receipt-field/)
  assert.match(file, /\.receipt-actions/)
  assert.match(file, /\.connection-chip/)
  assert.match(file, /\.receipt-empty-state/)
  assert.match(file, /\.receipt-source-detail/)
})
