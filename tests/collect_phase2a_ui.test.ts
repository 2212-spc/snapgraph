import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('CollectView follows the redesign take-it-in paper form', () => {
  const file = read('frontend/src/components/CollectView.vue')

  assert.match(file, /收下 · TAKE IT IN/)
  assert.match(file, /带着理由，收下一份/)
  assert.match(file, /class="collect-grid"/)
  assert.match(file, /id="bigcard" class="bigcard"/)
  assert.match(file, /id="dz" class="dz"/)
  assert.match(file, /拖进来，或点击选择/)
  assert.match(file, /给两周后的你，留一句话/)
  assert.match(file, /为什么是它？/)
  assert.match(file, /放到/)
  assert.match(file, /让 AI 放/)
  assert.match(file, /手动选/)
  assert.match(file, /先放待整理/)
  assert.match(file, /id="saveBtn" class="btn btn-ink"/)
  assert.match(file, /class="stackbox"/)
  assert.match(file, /份可找回的记忆/)
  assert.doesNotMatch(file, /collect-intro-msg/)
  assert.doesNotMatch(file, /class="collect-card capture"/)
})

test('CollectView preserves ingest progress and compact receipt actions', () => {
  const file = read('frontend/src/components/CollectView.vue')

  assert.match(file, /ingest-progress/)
  assert.match(file, /正在入库/)
  assert.match(file, /STEP_DEFINITIONS/)
  assert.match(file, /提取内容/)
  assert.match(file, /生成摘要/)
  assert.match(file, /保存理由/)
  assert.match(file, /放入空间/)
  assert.match(file, /寻找连接/)
  assert.match(file, /memory-receipt collect-receipt/)
  assert.match(file, /batchReceiptVisible/)
  assert.match(file, /本批次回执/)
  assert.match(file, /追问这批材料/)
  assert.match(file, /去书架/)
  assert.match(file, /查看材料详情/)
  assert.match(file, /继续收下下一份/)
  assert.match(file, /getReceiptUnderstanding/)
  assert.match(file, /normalizeReceiptSummary/)
  assert.match(file, /这份材料已经被保存，并可作为之后找回相关判断的线索。/)
  assert.match(file, /emit\('openSpace', space\)/)
  assert.match(file, /emit\('askBatch'/)
})

test('collect styles include reference big card, stack, receipt, and progress classes', () => {
  const file = read('frontend/src/styles.css')

  assert.match(file, /\.snapgraph-reference-shell \.collect-grid/)
  assert.match(file, /\.snapgraph-reference-shell \.bigcard/)
  assert.match(file, /\.snapgraph-reference-shell \.dz/)
  assert.match(file, /\.snapgraph-reference-shell \.receipt-field/)
  assert.match(file, /\.snapgraph-reference-shell \.card-foot/)
  assert.match(file, /\.snapgraph-reference-shell \.stackbox/)
  assert.match(file, /\.snapgraph-reference-shell \.mini\.m1/)
  assert.match(file, /\.ingest-progress/)
  assert.match(file, /\.memory-receipt/)
  assert.match(file, /\.batch-source-list/)
})
