import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('SpacesView reframes graph spaces as memory spaces', () => {
  const file = read('frontend/src/components/SpacesView.vue')

  assert.match(file, /你的信息在哪些问题里生长？/)
  assert.match(file, /graph-space-card/)
  assert.match(file, /新材料会先放在这里，等待确认和整理。/)
  assert.match(file, /默认记忆空间，保存当前 SnapGraph 工作流的主要材料、判断和开放问题。/)
  assert.match(file, /进入空间/)
  assert.match(file, /最近材料/)
})

test('GraphSpaceView adds overview mode and preserves workbench mode', () => {
  const file = read('frontend/src/components/GraphSpaceView.vue')

  assert.match(file, /graph-overview-mode/)
  assert.match(file, /概览/)
  assert.match(file, /专业模式/)
  assert.match(file, /const surfaceMode = ref<GraphSurfaceMode>\('overview'\)/)
  assert.match(file, /这个空间正在追踪什么/)
  assert.match(file, /最近材料/)
  assert.match(file, /关键节点/)
  assert.match(file, /开放问题 \/ 下一步/)
  assert.match(file, /找回这个空间里的判断/)
  assert.match(file, /整理开放问题/)
  assert.match(file, /进入专业模式/)
  assert.match(file, /选择一个材料或节点，查看它为什么被保存、和哪些问题相连。/)
  assert.match(file, /查看这个空间里材料、想法和项目之间的整体结构。/)
  assert.match(file, /查看某个回答或判断背后的证据路径。/)
  assert.match(file, /查看开放问题、下一步和待处理连接。/)
})

test('styles include phase 2B graph overview and mode switch classes', () => {
  const file = read('frontend/src/styles.css')

  assert.match(file, /\.graph-space-card/)
  assert.match(file, /\.graph-space-stats/)
  assert.match(file, /\.graph-overview-mode/)
  assert.match(file, /\.graph-summary-card/)
  assert.match(file, /\.graph-mode-switch/)
  assert.match(file, /\.graph-workbench/)
  assert.match(file, /\.graph-stat-chip/)
  assert.match(file, /\.graph-recent-source-card/)
  assert.match(file, /\.graph-key-node-card/)
  assert.match(file, /\.open-loop-card/)
  assert.match(file, /\.graph-empty-inspector/)
  assert.match(file, /\.graph-overview-actions/)
})
