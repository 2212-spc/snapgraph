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
  assert.match(file, /只查你的本地 SnapGraph，不是网页搜索。/)
  assert.match(file, /哪些旧材料能帮我判断 agent memory 的方向？/)
  assert.match(file, /recall-command/)
  assert.match(file, /example-chip/)
  assert.match(file, /const heroCopy = computed/)
  assert.match(file, /v-if="!showResult" class="prompt-row example-chip-row"/)
  assert.match(file, /emit\('recall', prompt\)/)
})

test('RecallResult contains phase 1.5 answer cleanup, compact summary, and localized source actions', () => {
  const file = read('frontend/src/components/RecallResult.vue')

  assert.match(file, /answer-card/)
  assert.match(file, /这是我的回答/)
  assert.match(file, /证据链/)
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

test('styles include phase 1.5 recall result mode and mobile summary classes', () => {
  const file = read('frontend/src/styles.css')

  assert.match(file, /\.recall-command/)
  assert.match(file, /\.answer-card/)
  assert.match(file, /\.evidence-chain/)
  assert.match(file, /\.evidence-chip/)
  assert.match(file, /\.subtle-empty-state/)
  assert.match(file, /\.evidence-summary-compact/)
  assert.match(file, /\.source-link-button/)
  assert.match(file, /\.source-inline-detail/)
  assert.match(file, /\.recall-home\.has-result \.recall-command textarea/)
})
