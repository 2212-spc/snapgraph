import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('App uses backend recall history and exposes the reference chat rail', () => {
  const app = read('frontend/src/App.vue')
  const types = read('frontend/src/types.ts')

  assert.match(types, /export type RecallHistoryItem/)
  assert.match(types, /export type RecallHistoryPayload/)
  assert.match(types, /export type RecallConversationTurn/)
  assert.match(app, /api<RecallHistoryPayload>\('\/api\/recall-history\?limit=12'\)/)
  assert.match(app, /mergeRecallThreads/)
  assert.match(app, /rememberRecallThread\(question, mode, depth, currentRecallSpaceId\.value\)/)
  assert.match(app, /loadRecallHistory/)
  assert.match(app, /class="side-history"/)
  assert.match(app, /最近对话/)
  assert.match(app, /showRecallRail/)
  assert.match(app, /class="rail recall-rail"/)
  assert.match(app, /本场对话碰到的记忆/)
  assert.match(app, /引用到的你的原话/)
  assert.match(app, /最近的对话/)
  assert.match(app, /:class="\{ chat: hasRecallConversation, 'is-recall-chat': hasRecallConversation \}"/)
})

test('RecallHome renders one scrollable thread with multiple backend turns', () => {
  const home = read('frontend/src/components/RecallHome.vue')
  const app = read('frontend/src/App.vue')

  assert.match(home, /turns: RecallConversationTurn\[\]/)
  assert.match(home, /v-for="turn in visibleTurns"/)
  assert.match(home, /:result="turn\.result"/)
  assert.match(home, /:focus-graph="turn\.focusGraph"/)
  assert.match(home, /:depth="turn\.depth"/)
  assert.match(home, /:stages="turn\.stages"/)
  assert.match(app, /const recallTurns = ref<RecallConversationTurn\[\]>\(\[\]\)/)
  assert.match(app, /updateRecallTurn/)
  assert.match(app, /previous_turns: recallPreviousTurnsPayload\(\)/)
  assert.match(app, /thread_id: currentRecallThreadId\.value/)
})

test('Opening a recall history restores saved turns without re-running recall', () => {
  const app = read('frontend/src/App.vue')
  const start = app.indexOf('async function reopenRecallThread(thread: RecallThread)')
  const end = app.indexOf('function rememberRecallThread', start)
  const reopenBody = app.slice(start, end)

  assert.ok(start >= 0, 'reopenRecallThread should exist')
  assert.ok(end > start, 'reopenRecallThread should be isolated before rememberRecallThread')
  assert.match(app, /const recallHistoryItems = ref<RecallHistoryItem\[\]>\(\[\]\)/)
  assert.match(app, /recallHistoryItems\.value = payload\.items/)
  assert.match(app, /async function loadRecallThreadHistory\(threadId: string\)/)
  assert.match(app, /thread_id=\$\{encodeURIComponent\(threadId\)\}/)
  assert.match(app, /function recallHistoryItemsForThread\(threadId: string\)/)
  assert.match(app, /function recallHistoryItemToTurn\(item: RecallHistoryItem\)/)
  assert.match(app, /function restoreRecallThread\(thread: RecallThread/)
  assert.match(reopenBody, /restoreRecallThread\(thread/)
  assert.doesNotMatch(reopenBody, /runRecall\(/)
})

test('Deep Thought stream appends thought_delta before the answer stage', () => {
  const app = read('frontend/src/App.vue')
  const result = read('frontend/src/components/RecallResult.vue')
  const types = read('frontend/src/types.ts')

  assert.match(types, /export type RecallThoughtTraceEvent/)
  assert.match(types, /trace_events\?: RecallThoughtTraceEvent\[\]/)
  assert.match(app, /event === 'thought_delta'/)
  assert.match(app, /appendThoughtDelta/)
  assert.match(app, /traceId/)
  assert.match(app, /trace_events: nextTraceEvents/)
  assert.match(app, /updateRecallStage\(\{ id: 'thought'[\s\S]*status: 'active'/)
  assert.match(result, /currentThought\.value\?\.status === 'thinking'/)
  assert.match(result, /thoughtTraceEvents/)
  assert.match(result, /正在思考/)
})

test('Deep Thought card uses a stable horizontal header instead of channel-block labels', () => {
  const result = read('frontend/src/components/RecallResult.vue')
  const styles = read('frontend/src/styles.css')

  assert.match(result, /class="deeptutor-thought-card"/)
  assert.match(result, /class="deeptutor-thought-header"/)
  assert.doesNotMatch(result, /class="channel-block thought-paper deep-thought-card"/)
  assert.doesNotMatch(result, /class="stamp"/)
  assert.doesNotMatch(result, /class="cl ch-lbl"/)
  assert.match(styles, /\.snapgraph-reference-shell \.deeptutor-thought-header[\s\S]*display: flex !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.deeptutor-thought-card[\s\S]*overflow: hidden !important/)
})

test('Reference CSS uses explicit chat state and protects composer/content from overlap', () => {
  const styles = read('frontend/src/styles.css')

  assert.match(styles, /\.snapgraph-reference-shell \.main\.is-recall-chat/)
  assert.match(styles, /\.snapgraph-reference-shell \.main\.is-recall-chat[\s\S]*overflow: hidden !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.recall-home\.has-result[\s\S]*height: 100% !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.recall-thread\.stream[\s\S]*padding: 30px 30px 28px !important/)
  assert.doesNotMatch(styles, /padding: 30px 30px 42px !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.recall-composer-wrap[\s\S]*position: relative !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.suggests[\s\S]*margin-bottom: 8px !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.c-fine[\s\S]*margin-top: 6px !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.tag[\s\S]*white-space: nowrap !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.deeptutor-thought-kicker[\s\S]*white-space: nowrap !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.recall-thread\.stream[\s\S]*overscroll-behavior: contain !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.recall-stream-inner[\s\S]*padding-top: 12px !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.deeptutor-thought-card[\s\S]*transform: none !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.thought-trace-list[\s\S]*max-height: 260px !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.thought-trace-list[\s\S]*overflow-y: auto !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.rail\.recall-rail[\s\S]*display: flex !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.deck[\s\S]*height: auto !important/)
  assert.match(styles, /\.snapgraph-reference-shell \.claim-card[\s\S]*position: relative !important/)
  assert.doesNotMatch(styles, /\.snapgraph-reference-shell \.main:has\(\.recall-home\.has-result\)/)
})

test('Streaming status text is not collapsed into the animated dot', () => {
  const home = read('frontend/src/components/RecallHome.vue')
  const styles = read('frontend/src/styles.css')

  assert.match(home, /class="status-dot"/)
  assert.match(home, /class="status-copy"/)
  assert.match(styles, /\.result-stream-status \.status-dot/)
  assert.match(styles, /\.snapgraph-reference-shell \.result-stream-status \.status-copy[\s\S]*width: auto/)
  assert.doesNotMatch(styles, /\.result-stream-status span\s*\{/)
  assert.doesNotMatch(styles, /\.snapgraph-reference-shell \.result-stream-status span\s*\{/)
})

test('Recall streaming auto-scroll only follows while the user is near the bottom', () => {
  const app = read('frontend/src/App.vue')

  assert.match(app, /async function scrollRecallThreadToBottom\(options: \{ force\?: boolean \} = \{\}\)/)
  assert.match(app, /if \(!options\.force && !recallThreadIsNearBottom\(thread\)\) return/)
  assert.match(app, /function recallThreadIsNearBottom\(thread: HTMLElement\)/)
  assert.match(app, /distanceFromBottom <= 96/)
  assert.match(app, /scrollRecallThreadToBottom\(\{ force: true \}\)/)
})
