import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('RecallHome uses memory-recall framing and example chips', () => {
  const file = read('frontend/src/components/RecallHome.vue')

  assert.match(file, /找回一个过去的判断/)
  assert.match(file, /问问过去的你/)
  assert.match(file, /我之前为什么关注这个问题？/)
  assert.match(file, /哪些材料支持我当时的判断？/)
  assert.match(file, /这个项目还有哪些未闭环问题？/)
  assert.doesNotMatch(file, /今天想学什么？/)
  assert.doesNotMatch(file, /把这个概念讲给初学者听/)
  assert.doesNotMatch(file, /围绕这个知识点考我 3 题/)
  assert.match(file, /recall-command/)
  assert.match(file, /example-chip/)
  assert.match(file, /composer-pill is-active/)
  assert.match(file, /placeholder="找回一个旧判断、证据或保存理由..."/)
  assert.match(file, /v-if="!showResult" class="prompt-row example-chip-row"/)
  assert.match(file, /question\.value = prompt/)
})

test('RecallResult contains phase 1.5 answer cleanup, compact summary, and localized source actions', () => {
  const file = read('frontend/src/components/RecallResult.vue')

  assert.match(file, /answer-card/)
  assert.match(file, /agent-trace-compact/)
  assert.match(file, /:open="busy"/)
  assert.match(file, /traceTitle/)
  assert.match(file, /traceDetail/)
  assert.match(file, /先给结论/)
  assert.match(file, /证据链/)
  assert.match(file, /sectionText\('## 结论'\)/)
  assert.match(file, /sectionText\('## AI 探索回应'\)/)
  assert.match(file, /这次回答不是网页搜索，而是从你的本地记忆材料里推回来的。/)
  assert.match(file, /normalizeAnswerText/)
  assert.match(file, /其中用户原话是主要依据，AI 推断用于补充可能的连接。/)
  assert.match(file, /why_saved_status/)
  assert.match(file, /user\[-_]stated/)
  assert.match(file, /AI\[-_]inferred/)
  assert.match(file, /const evidenceMaterialLimit = 2/)
  assert.match(file, /evidence-summary-compact/)
  assert.match(file, /source-link-button/)
  assert.match(file, /展开材料/)
  assert.match(file, /source-inline-detail/)
  assert.match(file, /查看全部材料/)
})

test('App preserves recent upload batch ids and passes them into recall requests', () => {
  const file = read('frontend/src/App.vue')

  assert.match(file, /recentBatchSourceIds/)
  assert.match(file, /uploadedSourceIds/)
  assert.match(file, /context_source_ids/)
  assert.match(file, /askRecentBatch/)
  assert.match(file, /@ask-batch="askRecentBatch"/)
  assert.match(file, /\/api\/focus[\s\S]*context_source_ids/)
  assert.match(file, /\/api\/ask\/stream[\s\S]*context_source_ids/)
})

test('CollectView exposes a batch receipt and direct follow-up action', () => {
  const file = read('frontend/src/components/CollectView.vue')

  assert.match(file, /batchReceiptVisible/)
  assert.match(file, /本批次/)
  assert.match(file, /追问这批材料/)
  assert.match(file, /askBatch/)
  assert.match(file, /emit\('askBatch'/)
  assert.match(file, /batch-question-button/)
})

test('styles include phase 1.5 recall result mode and mobile summary classes', () => {
  const file = read('frontend/src/styles.css')

  assert.match(file, /\.recall-command/)
  assert.match(file, /\.answer-card/)
  assert.match(file, /\.agent-trace-summary/)
  assert.match(file, /\.agent-step-list/)
  assert.match(file, /\.trace-disclosure/)
  assert.match(file, /\.evidence-chain/)
  assert.match(file, /\.evidence-chip/)
  assert.match(file, /\.subtle-empty-state/)
  assert.match(file, /\.evidence-summary-compact/)
  assert.match(file, /\.source-link-button/)
  assert.match(file, /\.source-inline-detail/)
  assert.match(file, /\.recall-home\.has-result \.recall-command textarea/)
  assert.match(file, /\.batch-receipt-strip/)
  assert.match(file, /\.batch-source-list/)
  assert.match(file, /\.batch-question-button/)
})
