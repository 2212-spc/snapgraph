import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('RecallHome mirrors the StudyAgent empty chat surface and example chips', () => {
  const file = read('frontend/src/components/RecallHome.vue')

  assert.match(file, /找回当时为什么在意它/)
  assert.match(file, /displayQuestion \|\| '新对话'/)
  assert.doesNotMatch(file, /今天想学什么？/)
  assert.doesNotMatch(file, /把这个概念讲给初学者听，再给一个判断例子。/)
  assert.match(file, /我之前为什么觉得/)
  assert.match(file, /刚才上传的这批材料/)
  assert.match(file, /哪些判断只有 AI 推断/)
  assert.match(file, /还有哪些 open loop/)
  assert.match(file, /问问过去的你/)
  assert.match(file, /recall-command/)
  assert.match(file, /example-chip/)
  assert.match(file, /composer-pill is-active/)
  assert.match(file, /placeholder="例如：我之前为什么觉得这个方向值得做？"/)
  assert.match(file, /v-if="!showResult" class="prompt-row example-chip-row"/)
  assert.match(file, /question\.value = prompt/)
})

test('RecallResult contains phase 1.5 answer cleanup, compact summary, and localized source actions', () => {
  const file = read('frontend/src/components/RecallResult.vue')

  assert.match(file, /answer-card/)
  assert.match(file, /answer-chat-window/)
  assert.match(file, /answer-chat-thread/)
  assert.match(file, /answer-message is-user/)
  assert.match(file, /answer-message is-assistant/)
  assert.match(file, /agent-trace-compact/)
  assert.match(file, /:open="busy"/)
  assert.match(file, /traceTitle/)
  assert.match(file, /traceDetail/)
  assert.match(file, /SnapGraph/)
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
  assert.match(file, /展开/)
  assert.match(file, /source-inline-detail/)
  assert.match(file, /查看全部材料/)
})

test('RecallResult adds a design-thinking reflection panel for judgment validation', () => {
  const result = read('frontend/src/components/RecallResult.vue')
  const panel = read('frontend/src/components/RecallReflectionPanel.vue')
  const home = read('frontend/src/components/RecallHome.vue')
  const styles = read('frontend/src/styles.css')

  assert.match(result, /import RecallReflectionPanel/)
  assert.match(result, /defineEmits/)
  assert.match(result, /askFollowUp: \[question: string\]/)
  assert.match(result, /<RecallReflectionPanel/)
  assert.match(result, /:question="questionText"/)
  assert.match(result, /:answer="answerText"/)
  assert.match(result, /:contexts="materials"/)
  assert.match(result, /:graph-paths="graphPaths"/)
  assert.match(result, /:next-step="nextText"/)
  assert.match(result, /@ask-follow-up="\$emit\('askFollowUp', \$event\)"/)

  assert.match(home, /@ask-follow-up="askFollowUp"/)
  assert.match(home, /function askFollowUp\(questionText: string\)/)
  assert.match(home, /emit\('recall', text\)/)

  assert.match(panel, /设计复盘/)
  assert.match(panel, /当前判断/)
  assert.match(panel, /用户原话/)
  assert.match(panel, /证据风险/)
  assert.match(panel, /下一步验证/)
  assert.match(panel, /primaryUserStatement/)
  assert.match(panel, /currentJudgment/)
  assert.match(panel, /evidenceRisk/)
  assert.match(panel, /validationQuestion/)
  assert.match(panel, /emit\('askFollowUp', validationQuestion\.value\)/)

  assert.match(styles, /\.recall-reflection-panel/)
  assert.match(styles, /\.reflection-grid/)
  assert.match(styles, /\.reflection-card/)
  assert.match(styles, /\.reflection-validation/)
})

test('App preserves recent upload batch ids and scopes recall requests to the current space', () => {
  const file = read('frontend/src/App.vue')

  assert.match(file, /recentBatchSourceIds/)
  assert.match(file, /uploadedSourceIds/)
  assert.match(file, /context_source_ids/)
  assert.match(file, /askRecentBatch/)
  assert.match(file, /@ask-batch="askRecentBatch"/)
  assert.match(file, /currentRecallSpaceId/)
  assert.match(file, /function recallSpaceScope\(\)/)
  assert.match(file, /space_id: activeTopic\.value\?\.space_id \|\| recallSpaceScope\(\)/)
  assert.doesNotMatch(file, /space_id: 'all'/)
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
