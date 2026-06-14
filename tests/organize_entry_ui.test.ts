import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('App exposes redesign emergence and shelf entries instead of old knowledge/trust split', () => {
  const app = read('frontend/src/App.vue')

  assert.match(app, /type ActiveView = 'recall' \| 'emerge' \| 'collect' \| 'shelf'/)
  assert.match(app, /label: '涌现'/)
  assert.match(app, /label: '书架'/)
  assert.match(app, /<OrganizeView/)
  assert.match(app, /<ShelfView/)
  assert.doesNotMatch(app, /label: '知识库'/)
  assert.doesNotMatch(app, /label: '信任'/)
  assert.doesNotMatch(app, /activeView === 'spaces'/)
  assert.doesNotMatch(app, /activeView === 'trust'/)
})

test('OrganizeView is the redesign emergence card deck', () => {
  const organizePath = resolve(root, 'frontend/src/components/OrganizeView.vue')
  assert.equal(existsSync(organizePath), true)

  const view = read('frontend/src/components/OrganizeView.vue')

  assert.match(view, /涌现 · WHAT EMERGES/)
  assert.match(view, /把你的想法接上/)
  assert.match(view, /AI 连出来的/)
  assert.match(view, /claim-top/)
  assert.match(view, /class="deck"/)
  assert.match(view, /ghost-card g2/)
  assert.match(view, /claim-card emerge-card/)
  assert.match(view, /图谱把上面两条接上/)
  assert.match(view, /一个你没明说过的想法浮了出来/)
  assert.match(view, /怎么连的/)
  assert.match(view, /这是我的/)
  assert.match(view, /改两笔/)
  assert.match(view, /不是这样/)
  assert.match(view, /goShelf/)
  assert.match(view, /batchAction/)
  assert.match(view, /updateOpenLoop/)
  assert.match(view, /rewrites/)
  assert.match(view, /note: '在涌现卡片中认领。'/)
  assert.doesNotMatch(view, /OrganizeTaskCard/)
  assert.doesNotMatch(view, /今天建议先处理/)
  assert.doesNotMatch(view, /Trust Operations|Review Inbox|Evidence Detail/)
})

test('ShelfView carries spaces, graph, inbox, and folded advanced details', () => {
  const shelfPath = resolve(root, 'frontend/src/components/ShelfView.vue')
  assert.equal(existsSync(shelfPath), true)

  const shelf = read('frontend/src/components/ShelfView.vue')

  assert.match(shelf, /书架 · THE SHELF/)
  assert.match(shelf, /记忆空间/)
  assert.match(shelf, /class="graph-wrap shelf-graph-system"/)
  assert.match(shelf, /class="graph-stack"/)
  assert.match(shelf, /class="graph-panel primary-graph-panel"/)
  assert.match(shelf, /class="graph-panel shelf-diagnostics-map"/)
  assert.match(shelf, /class="graph"/)
  assert.match(shelf, /g-node-you/)
  assert.match(shelf, /g-node-ai/)
  assert.match(shelf, /g-node-new/)
  assert.match(shelf, /shelf-grid/)
  assert.match(shelf, /class="space"/)
  assert.match(shelf, /class="inbox-card"/)
  assert.match(shelf, /待认领/)
  assert.match(shelf, /goEmerge/)
  assert.match(shelf, /高级详情/)
  assert.match(shelf, /diagnostics/)
  assert.match(shelf, /openSource/)
  assert.match(shelf, /askFromGraph/)
  assert.match(shelf, /createSpace/)
  assert.match(shelf, /new-space-form/)
  assert.match(shelf, /新建图谱空间/)
  assert.match(shelf, /realGraphSpaces/)
  assert.doesNotMatch(shelf, /projectClusterSpaces/)
  assert.doesNotMatch(shelf, /SnapGraph 项目/)
  assert.doesNotMatch(shelf, /AI Agent 调研/)
})

test('Organize and shelf styles follow the reference card deck and graph layout', () => {
  const styles = read('frontend/src/styles.css')

  assert.match(styles, /\.snapgraph-reference-shell \.claim-top/)
  assert.match(styles, /\.snapgraph-reference-shell \.deck/)
  assert.match(styles, /\.snapgraph-reference-shell \.ghost-card/)
  assert.match(styles, /\.snapgraph-reference-shell \.claim-card/)
  assert.match(styles, /\.snapgraph-reference-shell \.claim-card\.exit-l/)
  assert.match(styles, /\.snapgraph-reference-shell \.claim-card\.exit-r/)
  assert.match(styles, /\.snapgraph-reference-shell \.emerge-idea/)
  assert.match(styles, /\.snapgraph-reference-shell \.graph-wrap/)
  assert.match(styles, /\.snapgraph-reference-shell \.shelf-graph-system[\s\S]*display: grid/)
  assert.match(styles, /grid-template-columns: minmax\(0, 1\.45fr\) minmax\(260px, 0\.78fr\)/)
  assert.match(styles, /\.snapgraph-reference-shell \.shelf-grid/)
  assert.match(styles, /\.snapgraph-reference-shell \.space:hover/)
  assert.match(styles, /\.snapgraph-reference-shell \.inbox-card/)
  assert.match(styles, /\.snapgraph-reference-shell \.new-space-form/)
  assert.match(styles, /\.snapgraph-reference-shell \.new-space-form input/)
})

test('App wires shelf-created spaces to the backend graph space API', () => {
  const app = read('frontend/src/App.vue')

  assert.match(app, /@create-space="createSpace"/)
  assert.match(app, /async function createSpace/)
  assert.match(app, /api<GraphSpace>\('\/api\/spaces'/)
  assert.match(app, /method: 'POST'/)
  assert.match(app, /await loadSpaces\(\)/)
})
