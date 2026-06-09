import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()

function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('App adopts StudyAgent-style workspace shell structure', () => {
  const file = read('frontend/src/App.vue')

  assert.match(file, /class="study-shell"/)
  assert.match(file, /class="study-sidebar"/)
  assert.match(file, /class="study-chat-shell"/)
  assert.match(file, /class="session-title-button"/)
  assert.match(file, /class="sidebar-new-chat"/)
  assert.match(file, /class="activity-panel"/)
  assert.match(file, /showActivityPanel/)
  assert.match(file, /新对话/)
  assert.match(file, /收集/)
  assert.doesNotMatch(file, /练习/)
  assert.doesNotMatch(file, /label: '可视化'/)
  assert.doesNotMatch(file, /type ActiveView = 'recall' \| 'spaces' \| 'collect' \| 'visualize'/)
  assert.match(file, /runtimeStatusLabel/)
  assert.match(file, /本地记忆已连接/)
  assert.match(file, /本地演示模式/)
  assert.match(file, /<span class="provider-pill">\{\{ runtimeStatusLabel \}\}<\/span>/)
  assert.doesNotMatch(file, /<span class="provider-pill">\{\{ providerLabel \}\}<\/span>/)
  assert.match(file, /SquarePen/)
})

test('RecallHome exposes a compact chat-style starter and composer surface', () => {
  const file = read('frontend/src/components/RecallHome.vue')

  assert.match(file, /今天想学什么？/)
  assert.match(file, /把这个概念讲给初学者听，再给一个判断例子。/)
  assert.match(file, /带我一步一步做这道题，并指出最容易错的地方。/)
  assert.match(file, /把这个系统画成 Mermaid 图，并解释每条边代表什么。/)
  assert.match(file, /围绕这个知识点考我 3 题，再根据我的答案讲错因。/)
  assert.doesNotMatch(file, /问问过去的你/)
  assert.match(file, /class="starter-grid"/)
  assert.match(file, /class="composer-shell"/)
  assert.match(file, /class="composer-input-wrap"/)
  assert.match(file, /class="composer-toolbar"/)
  assert.match(file, /class="composer-pill is-active"/)
  assert.match(file, /placeholder="今天我能帮您什么？"/)
})

test('styles include StudyAgent-derived shell, sidebar, composer, and activity panel classes', () => {
  const file = read('frontend/src/styles.css')

  assert.match(file, /\.study-shell/)
  assert.match(file, /\.study-sidebar/)
  assert.match(file, /\.study-chat-shell/)
  assert.match(file, /\.session-title-button/)
  assert.match(file, /\.sidebar-new-chat/)
  assert.match(file, /\.study-sidebar\s*{[\s\S]*width: 220px/)
  assert.match(file, /\.study-sidebar\[data-collapsed="true"\]\s*{[\s\S]*width: 60px/)
  assert.match(file, /\.brand-mark\s*{[\s\S]*width: 28px/)
  assert.match(file, /\.sidebar-new-chat,[\s\S]*font-size: 13\.5px/)
  assert.match(file, /\.starter-grid/)
  assert.match(file, /\.composer-shell/)
  assert.match(file, /\.composer-toolbar/)
  assert.match(file, /\.recall-box\s*{[\s\S]*border-radius: 26px/)
  assert.match(file, /font-size: 13\.5px/)
  assert.match(file, /\.activity-panel/)
  assert.match(file, /\.activity-card/)
  assert.match(file, /\.activity-toggle[\s\S]*display: none/)
})

test('styles adopt StudyAgent cream palette and dense app typography', () => {
  const file = read('frontend/src/styles.css')

  assert.match(file, /--background: #fdfcf9;/)
  assert.match(file, /--secondary: #f5f2ea;/)
  assert.match(file, /--primary: #b0501e;/)
  assert.match(file, /--blue: #b0501e;/)
  assert.match(file, /--muted: #f1ede2;/)
  assert.match(file, /--muted-foreground: #6d645a;/)
  assert.match(file, /--border-subtle: #e6decc;/)
  assert.match(file, /--card-foreground: #1c1816;/)
  assert.match(file, /--secondary-foreground: #1c1816;/)
  assert.match(file, /--overlay: rgba\(28, 24, 22, 0\.42\);/)
  assert.match(file, /\.layer-head h1[\s\S]*font-family: var\(--sans\)/)
  assert.match(file, /\.layer-head h1[\s\S]*font-size: clamp\(1\.55rem, 2\.6vw, 2\.2rem\)/)
  assert.match(file, /\.graph-space-card[\s\S]*border-radius: 12px/)
  assert.match(file, /\.collect-card[\s\S]*border-radius: 12px/)
})

test('mobile StudyAgent shell keeps the reference-style collapsed sidebar', () => {
  const file = read('frontend/src/styles.css')

  assert.match(file, /@media \(max-width: 760px\)[\s\S]*\.study-shell\s*{[\s\S]*display: flex;/)
  assert.match(file, /@media \(max-width: 760px\)[\s\S]*\.study-sidebar\s*{[\s\S]*display: flex;[\s\S]*width: 60px;[\s\S]*min-width: 60px;/)
  assert.match(file, /@media \(max-width: 760px\)[\s\S]*\.study-sidebar \.brand-copy,[\s\S]*\.study-sidebar \.sidebar-nav span,[\s\S]*display: none;/)
  assert.match(file, /@media \(max-width: 760px\)[\s\S]*\.mobile-nav\s*{[\s\S]*display: none;/)
  assert.doesNotMatch(file, /\.study-sidebar\s*{[^}]*display: none;/)
  assert.doesNotMatch(file, /\.mobile-nav\s*{[^}]*display: grid;/)
})
