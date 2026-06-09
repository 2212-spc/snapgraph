import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('App exposes Trust Center as a primary workspace view', () => {
  const app = read('frontend/src/App.vue')

  assert.match(app, /type ActiveView = 'recall' \| 'spaces' \| 'trust' \| 'collect'/)
  assert.match(app, /label: '信任'/)
  assert.match(app, /ShieldCheck/)
  assert.match(app, /<TrustCenterView/)
  assert.match(app, /loadTrustCenter/)
  assert.match(app, /applyTrustBatch/)
  assert.match(app, /updateTrustOpenLoop/)
  assert.match(app, /\/api\/trust\/review/)
  assert.match(app, /\/api\/trust\/open-loops/)
  assert.match(app, /\/api\/trust\/diagnostics/)
})

test('Trust Center components expose review operations, evidence, open loops, and diagnostics', () => {
  const view = read('frontend/src/components/TrustCenterView.vue')
  const inbox = read('frontend/src/components/TrustReviewInbox.vue')
  const detail = read('frontend/src/components/TrustReviewDetail.vue')
  const batch = read('frontend/src/components/TrustBatchActionBar.vue')
  const loops = read('frontend/src/components/TrustOpenLoopPanel.vue')
  const diagnostics = read('frontend/src/components/TrustDiagnosticsPanel.vue')
  const types = read('frontend/src/components/trustCenterTypes.ts')
  const styles = read('frontend/src/styles.css')

  assert.match(types, /TrustRiskLevel/)
  assert.match(types, /TrustReviewStatus/)
  assert.match(types, /TrustOpenLoopState/)
  assert.match(types, /TrustBatchPayload/)
  assert.match(view, /trust-center-view/)
  assert.match(view, /TrustReviewInbox/)
  assert.match(view, /TrustReviewDetail/)
  assert.match(view, /TrustBatchActionBar/)
  assert.match(view, /TrustOpenLoopPanel/)
  assert.match(view, /TrustDiagnosticsPanel/)
  assert.match(inbox, /risk_level/)
  assert.match(inbox, /selectedSourceIds/)
  assert.match(inbox, /filterChanged/)
  assert.match(detail, /evidence_paths/)
  assert.match(detail, /history/)
  assert.match(detail, /batchAction/)
  assert.match(batch, /batchAction/)
  assert.match(batch, /confirmed/)
  assert.match(batch, /deferred/)
  assert.match(loops, /open-loop/)
  assert.match(loops, /resolved/)
  assert.match(loops, /dismissed/)
  assert.match(diagnostics, /queue_total/)
  assert.match(diagnostics, /ai_inferred_unreviewed/)
  assert.match(styles, /\.trust-center-view/)
  assert.match(styles, /\.trust-summary-grid/)
  assert.match(styles, /\.trust-review-inbox/)
  assert.match(styles, /\.trust-detail-panel/)
  assert.match(styles, /\.trust-batch-bar/)
  assert.match(styles, /\.trust-open-loop-panel/)
  assert.match(styles, /\.trust-diagnostics-panel/)
})
