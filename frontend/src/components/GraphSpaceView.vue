<template>
  <section class="space-detail graph-space-detail" v-if="space">
    <header class="space-detail-head">
      <div>
        <p class="eyebrow">{{ surfaceMode === 'source-map' ? '全局源地图' : surfaceMode === 'overview' ? '知识库 / 记忆云' : '知识库 / 高级审计' }}</p>
        <h2>{{ spaceDisplayName }}</h2>
        <p>{{ spaceDescription }}</p>
      </div>
      <div class="space-detail-topbar">
        <div class="space-stats graph-space-stats">
          <span v-for="stat in graphHeaderStats" :key="stat" class="graph-stat-chip">{{ stat }}</span>
        </div>

        <div class="graph-mode-switch" role="tablist" aria-label="知识库视图切换">
          <button
            :class="{ active: surfaceMode === 'source-map' }"
            role="tab"
            :aria-selected="surfaceMode === 'source-map'"
            @click="surfaceMode = 'source-map'"
          >
            全局地图
          </button>
          <button
            :class="{ active: surfaceMode === 'overview' }"
            role="tab"
            :aria-selected="surfaceMode === 'overview'"
            @click="surfaceMode = 'overview'"
          >
            记忆云
          </button>
          <button
            :class="{ active: surfaceMode === 'workbench' }"
            role="tab"
            :aria-selected="surfaceMode === 'workbench'"
            @click="surfaceMode = 'workbench'"
          >
            高级审计
          </button>
        </div>
      </div>
    </header>

    <section v-if="surfaceMode === 'source-map'" class="graph-source-map-mode">
      <GlobalSourceMap
        v-if="!drillDownState"
        :space="space"
        :sources="sourceMapEntries"
        :synthetic-edges="sourceMapSyntheticEdges"
        :expanded-ids="expandedSourceIds"
        @expand-source="handleExpandSource"
        @trace-thread="handleTraceThread"
      />
      <SourceDrillDown
        v-else
        :drill-mode="drillDownState.mode"
        :expanded-source="drillDownState.expandedSource"
        :subgraph-nodes="drillDownState.subgraphNodes"
        :subgraph-edges="drillDownState.subgraphEdges"
        :thread-nodes="drillDownState.threadNodes"
        :thread-edges="drillDownState.threadEdges"
        :path-description="drillDownState.pathDescription"
        @back="drillDownState = null"
        @ask-here="(q) => $emit('askFromGraph', q)"
        @open-source="(sid) => openSourceDetail(sid)"
      />
    </section>

    <section v-if="surfaceMode === 'overview'" class="graph-overview-mode">
      <div class="graph-guided-actions" aria-label="这个空间的下一步">
        <button class="graph-guided-action primary" type="button" @click="askFromSpace">
          <span>找回旧判断</span>
          <strong>先问一句过去的你</strong>
          <small>{{ userStatedSourceCount ? `优先找 ${userStatedSourceCount} 条用户原话和证据` : '先从本地材料里找证据' }}</small>
        </button>
        <button class="graph-guided-action" type="button" @click="openActionWorkbench">
          <span>继续处理</span>
          <strong>{{ overviewOpenCount ? `${overviewOpenCount} 个未闭环线索` : '暂时没有急着处理的问题' }}</strong>
          <small>{{ openLoopGuidance }}</small>
        </button>
        <button class="graph-guided-action" type="button" @click="openAuditWorkbench">
          <span>高级审计</span>
          <strong>{{ reviewQueueCount ? `${reviewQueueCount} 条可审查线索` : '查看证据路径和关系' }}</strong>
          <small>只在你想检查来源、关系或 AI 建议时进入。</small>
        </button>
      </div>

      <section class="space-panel memory-cloud-console">
        <div class="memory-cloud-head">
          <div>
            <p class="section-kicker">记忆云</p>
            <h3>搜一个词，找过去的证据</h3>
            <p>
              记忆星图里，每条线索都是一颗星。保存过的问题、用户原话、材料暗示的问题和开放事项会聚在一起。先点一个线索，
              看它对应哪些来源，再决定要不要追问。
            </p>
          </div>
          <span>{{ cloudItems.length }} 条记忆线索</span>
        </div>

        <div class="memory-cloud-layout">
          <div
            v-if="visibleCloudItems.length"
            ref="cloudOrbitElement"
            class="cloud-orbit cloud-constellation"
            :class="{ 'is-cloud-dragging': draggingCloudKey, 'is-cloud-recoiling': cloudRecoilKey, 'is-cloud-returning': cloudReturnKey }"
            aria-label="搜索历史星图"
            tabindex="0"
            @keydown.esc.prevent="clearCloudSearch"
          >
            <form class="cloud-search-row constellation-search" @submit.prevent="askCloudSearch">
              <Search :size="17" />
              <input v-model="graphSearchQuery" placeholder="搜关键词，匹配的点会亮起来..." />
            </form>

            <svg
              class="cloud-constellation-edges"
              :viewBox="`0 0 ${cloudOrbitSize.width} ${cloudOrbitSize.height}`"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <line
                v-for="edge in cloudConstellationEdges"
                :key="edge.id"
                :x1="edge.x1"
                :y1="edge.y1"
                :x2="edge.x2"
                :y2="edge.y2"
                :class="{ active: edge.active }"
              />
              <circle
                v-if="selectedCloudPoint"
                class="cloud-constellation-core-ring"
                :cx="selectedCloudPoint.x"
                :cy="selectedCloudPoint.y"
                r="74"
              />
            </svg>

            <button
              v-for="(item, index) in visibleCloudItems"
              :key="item.key"
              type="button"
              class="cloud-node"
              :class="cloudNodeClasses(item)"
              :style="cloudNodeStyle(item, index)"
              :aria-pressed="selectedCloudKey === item.key"
              :title="item.label"
              @click="selectCloudNode($event, item)"
              @pointerdown.stop="startCloudDrag($event, item)"
              @pointermove.stop="moveCloudDrag($event)"
              @pointerup.stop="endCloudDrag"
              @pointercancel.stop="cancelCloudDrag"
              @lostpointercapture.stop="handleCloudLostPointerCapture($event)"
            >
              <span class="cloud-node-halo" aria-hidden="true"></span>
              <span class="cloud-node-dot" aria-hidden="true"></span>
              <strong>{{ cloudLabel(item.label) }}</strong>
            </button>

            <div
              v-if="selectedCloudKey && selectedCloudItem && selectedCloudPoint"
              class="cloud-focus-label"
              :style="cloudFocusLabelStyle"
            >
              {{ cloudLabel(selectedCloudItem.label) }}
            </div>

            <div class="cloud-helper-pill">相关线索会一起亮起</div>
          </div>
          <div v-else class="cloud-empty-state">
            <strong>还没有匹配的记忆点</strong>
            <p>换一个更宽的词，或者先去“收集”里放入材料。</p>
          </div>

          <aside class="cloud-inspector-card cloud-context-dock">
            <template v-if="selectedCloudItem">
              <span>{{ selectedCloudItem.kindLabel }}</span>
              <strong>{{ selectedCloudItem.label }}</strong>
              <p>{{ selectedCloudItem.detail }}</p>
              <div v-if="selectedCloudItem.evidenceTitles.length" class="cloud-evidence-list">
                <small>证据来源</small>
                <button
                  v-for="source in selectedCloudItem.evidenceTitles"
                  :key="source.id"
                  type="button"
                  @click="selectSourceById(source.id)"
                >
                  {{ source.title }}
                </button>
              </div>
              <div class="cloud-actions">
                <button class="primary-button" @click="continueFromCloud(selectedCloudItem)">继续从这里追问</button>
                <button class="paper-button" @click="focusCloudItem(selectedCloudItem)">看连接</button>
              </div>
            </template>
            <template v-else>
              <span>记忆星图</span>
              <strong>先点一个记忆点</strong>
              <p>这里会解释它为什么出现，以及它对应哪些来源。</p>
            </template>
          </aside>

          <section
            v-if="selectedQuestionDetail || questionDetailLoading || questionDetailError"
            class="cloud-history-panel cloud-conversation-window"
            :class="{ 'is-loading': questionDetailLoading }"
            aria-live="polite"
          >
            <div class="cloud-history-head">
              <div>
                <span>对话记录</span>
                <strong>历史问答窗口</strong>
              </div>
              <button class="text-button" type="button" @click="closeQuestionHistory">关闭</button>
            </div>

            <template v-if="selectedQuestionDetail">
              <div class="cloud-chat-thread">
                <article class="cloud-chat-message is-user">
                  <span class="cloud-chat-avatar">你</span>
                  <div class="cloud-chat-bubble">
                    <small>当初的问题</small>
                    <p>{{ selectedQuestionDetail.question }}</p>
                  </div>
                </article>
                <article class="cloud-chat-message is-assistant">
                  <span class="cloud-chat-avatar">S</span>
                  <div class="cloud-chat-bubble">
                    <small>当初的回答</small>
                    <p v-for="block in selectedQuestionAnswerBlocks" :key="block">{{ block }}</p>
                  </div>
                </article>
              </div>
              <div class="cloud-history-actions">
                <button class="primary-button" type="button" @click="continueFromQuestionHistory">
                  继续从这里追问
                </button>
                <button class="paper-button" type="button" @click="focusQuestionEvidence">
                  看当时证据
                </button>
              </div>
            </template>
            <p v-else-if="questionDetailLoading">正在打开当初的问答...</p>
            <p v-else>{{ questionDetailError }}</p>
          </section>
        </div>
      </section>

      <div class="graph-overview-grid">
        <article class="space-panel graph-summary-card">
          <div class="section-head compact">
            <p class="section-kicker">可以直接问</p>
            <h3>这个空间能帮你找回什么</h3>
          </div>
          <p>{{ overviewSummary }}</p>
          <div class="space-question-starters">
            <button
              v-for="prompt in spacePromptExamples"
              :key="prompt"
              type="button"
              @click="askSuggestedPrompt(prompt)"
            >
              {{ prompt }}
            </button>
          </div>
        </article>

        <article class="space-panel graph-summary-card">
          <div class="section-head compact">
            <p class="section-kicker">最近证据</p>
            <h3>最近保存的材料</h3>
          </div>
          <div v-if="overviewRecentSources.length" class="graph-overview-list">
            <article
              v-for="source in overviewRecentSources"
              :key="source.id"
              class="graph-recent-source-card"
            >
              <div class="graph-card-row">
                <strong>{{ source.title }}</strong>
                <span class="evidence-badge" :class="sourceToneClass(source)">
                  {{ sourceBadgeLabel(source) }}
                </span>
              </div>
              <p>{{ sourcePreview(source) }}</p>
            </article>
          </div>
          <p v-else class="subtle-empty-state">还没有最近材料。继续收集后，这里会先出现新的线索。</p>
        </article>

        <article class="space-panel graph-summary-card">
          <div class="section-head compact">
            <p class="section-kicker">反复出现</p>
            <h3>这个空间的主题</h3>
          </div>
          <div v-if="overviewKeyNodes.length" class="graph-overview-list">
            <article
              v-for="node in overviewKeyNodes"
              :key="node.id"
              class="graph-key-node-card"
            >
              <div class="graph-card-row">
                <strong>{{ node.label }}</strong>
                <span class="evidence-badge" :class="nodeToneClass(node)">
                  {{ nodeTypeLabel(node.type) }}
                </span>
              </div>
              <p>{{ keyNodeSummary(node) }}</p>
            </article>
          </div>
          <p v-else class="subtle-empty-state">
            还没有足够节点。继续收集材料后，SnapGraph 会逐步形成结构。
          </p>
        </article>

        <article class="space-panel graph-summary-card">
          <div class="section-head compact">
            <p class="section-kicker">下一步</p>
            <h3>待处理线索</h3>
          </div>
          <div v-if="overviewOpenItems.length" class="graph-overview-list">
            <article
              v-for="item in overviewOpenItems"
              :key="item.key"
              class="open-loop-card"
            >
              <div class="graph-card-row">
                <strong>{{ item.title }}</strong>
                <span v-if="item.badge" class="evidence-badge" :class="item.tone">
                  {{ item.badge }}
                </span>
              </div>
              <p>{{ item.detail }}</p>
            </article>
          </div>
          <p v-else class="subtle-empty-state">
            暂时没有明确开放问题。你可以继续收集材料，或进入高级审计整理连接。
          </p>
        </article>
      </div>
    </section>

    <section v-else class="graph-workbench">
      <details class="space-editor">
        <summary>编辑空间</summary>
        <div>
          <input v-model="editSpaceName" placeholder="空间名称" />
          <input v-model="editSpacePurpose" placeholder="这个空间追什么问题？" />
          <textarea v-model="editSpaceDescription" placeholder="补充描述，可选。" />
          <label>
            <small>颜色</small>
            <input v-model="editSpaceColor" type="color" />
          </label>
          <button class="paper-button" :disabled="busy || !editSpaceName.trim()" @click="saveSpace">
            保存空间
          </button>
        </div>
      </details>

      <div class="graph-toolbar" aria-label="Graph workspace controls">
        <div class="graph-toolbar-group">
          <span>视图</span>
          <div class="graph-toolbar-buttons">
            <button
              v-for="mode in viewModes"
              :key="mode.id"
              :class="{ active: viewMode === mode.id }"
              @click="viewMode = mode.id"
            >
              <component :is="mode.icon" :size="15" />
              {{ mode.label }}
            </button>
          </div>
          <p class="graph-view-caption">{{ modeDescription }}</p>
        </div>
        <div class="graph-toolbar-group">
          <span>操作</span>
          <div class="graph-toolbar-buttons">
            <button
              v-for="mode in interactionModes"
              :key="mode.id"
              :class="{ active: interactionMode === mode.id }"
              @click="setInteractionMode(mode.id)"
            >
              <component :is="mode.icon" :size="15" />
              {{ mode.label }}
            </button>
          </div>
        </div>
      </div>

      <div class="workbench-grid">
        <aside class="space-panel graph-left-panel">
          <span>材料</span>
          <input v-model="sourceFilter" placeholder="筛选材料" />
          <div class="source-scroll">
            <button
              v-for="source in visibleSources"
              :key="source.id"
              class="source-row"
              :class="{ selected: selectedSource?.id === source.id }"
              @click="selectSource(source)"
            >
              <strong>{{ source.title }}</strong>
              <small>{{ source.why_saved_status === 'user-stated' ? '用户原话' : 'AI 推断' }}</small>
            </button>
            <p v-if="!visibleSources.length">这个图谱还没有可显示的材料。</p>
          </div>

          <section v-if="themes.length" class="theme-list">
            <span>主题分组</span>
            <button
              v-for="theme in themes"
              :key="theme.id"
              :class="{ selected: selectedThemeId === theme.id }"
              @click="selectTheme(theme.id)"
            >
              <strong>{{ theme.label }}</strong>
              <small>{{ theme.origin }} · {{ theme.status }}</small>
            </button>
          </section>

          <section v-if="suggestions.length" class="route-suggestions">
            <span>AI 路由建议</span>
            <article v-for="suggestion in suggestions" :key="suggestion.id">
              <small>{{ Math.round(suggestion.confidence * 100) }}%</small>
              <p>{{ routeSuggestionReasonText(suggestion) }}</p>
              <button class="paper-button" :disabled="busy" @click="$emit('acceptSuggestion', suggestion.id)">接受</button>
              <button class="ghost-button" :disabled="busy" @click="$emit('rejectSuggestion', suggestion.id)">忽略</button>
            </article>
          </section>
        </aside>

        <article class="space-panel graph-canvas-panel" :class="{ 'is-expanded': graphExpanded }">
          <div class="canvas-head">
            <div>
              <span>{{ currentViewLabel }}</span>
              <p>{{ modeDescription }}</p>
            </div>
            <div class="canvas-actions">
              <button class="paper-button" :disabled="!visibleGraphNodes.length" @click="toggleGraphExpanded">
                <component :is="graphExpanded ? Minimize2 : Maximize2" :size="15" />
                {{ graphExpanded ? '退出放大' : '放大图谱' }}
              </button>
              <button class="paper-button" :disabled="!visibleGraphNodes.length" @click="resetAutoLayout">
                重新排布
              </button>
              <button class="paper-button" :disabled="!graph.nodes.length || savingLayout" @click="saveCurrentLayout">
                保存布局
              </button>
            </div>
          </div>

          <div
            v-if="visibleGraphNodes.length"
            ref="stageContainer"
            class="graph-stage"
            @dblclick="toggleGraphExpanded"
            @pointerdown="startGraphPan"
            @wheel.prevent="zoomGraph"
          >
            <div class="graph-map-layer" :style="graphTransformStyle">
              <svg class="graph-stage-edges" viewBox="0 0 1000 680" preserveAspectRatio="none" aria-hidden="true">
                <defs>
                  <marker id="paper-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" />
                  </marker>
                </defs>
                <g>
                  <g
                    v-for="edge in visibleGraphEdges"
                    :key="edge.id"
                    class="graph-edge-hit"
                    :aria-label="`${labelFor(edge.source)} ${edge.relation} ${labelFor(edge.target)}`"
                    @click="selectGraphEdge(edge.id)"
                  >
                    <path :d="edgePath(edge)" class="paper-edge-touch" />
                    <path
                      :d="edgePath(edge)"
                      class="paper-edge"
                      :class="edgeClasses(edge)"
                      marker-end="url(#paper-arrow)"
                    />
                  </g>
                  <text
                    v-for="edge in labeledGraphEdges"
                    :key="`label-${edge.id}`"
                    class="paper-edge-label"
                    :x="edgeMidpoint(edge).x"
                    :y="edgeMidpoint(edge).y"
                  >
                    {{ edge.relation }}
                  </text>
                </g>
              </svg>
              <button
                v-for="node in visibleGraphNodes"
                :key="node.id"
                class="paper-graph-node"
                :class="[
                  `node-${node.type}`,
                  `status-${node.status || 'confirmed'}`,
                  { selected: selectedNodeIds.includes(node.id) },
                ]"
                :style="nodePositionStyle(node.id)"
                :title="node.label"
                :aria-label="`${nodeTypeLabel(node.type)}：${node.label}`"
                @click.stop="selectGraphNode(node.id, $event.shiftKey)"
                @dblclick.stop="toggleGraphExpanded"
              >
                <span class="node-dot" aria-hidden="true" @pointerdown.stop="startNodeDrag($event, node.id)"></span>
                <span class="node-label">{{ nodeMapLabel(node) }}</span>
              </button>
            </div>
            <div v-if="selectedNode" class="graph-stage-caption">
              <small>{{ nodeTypeLabel(selectedNode.type) }}</small>
              <strong>{{ shortLabel(selectedNode.label) }}</strong>
            </div>
          </div>
          <div v-else class="empty-canvas">
            <strong>这个空间还没有节点</strong>
            <p>先去“收集”放入材料，或者从待整理接受一条路由建议。</p>
          </div>

          <section class="mode-guide">
            <span>怎么用这一层</span>
            <p>{{ interactionGuide }}</p>
          </section>

          <div class="selection-strip">
            <span>{{ selectionSummary }}</span>
            <button class="ghost-button" :disabled="!selectedNodeIds.length" @click="clearSelection">清空选择</button>
          </div>

          <section v-if="interactionMode === 'connect'" class="operation-card">
            <span>手动连边</span>
            <p>选择两个节点，写下为什么它们应该被连起来。这个原因会记录进审计日志。</p>
            <input v-model="edgeRelation" placeholder="关系，例如 supports / contradicts / clarifies" />
            <textarea v-model="edgeReason" placeholder="为什么这两个节点有关？" />
            <button class="primary-button" :disabled="busy || selectedNodeIds.length < 2 || !edgeReason.trim()" @click="createEdge">
              确认连边
            </button>
          </section>

          <section v-if="interactionMode === 'synthesize'" class="operation-card">
            <span>框选归纳</span>
            <p>选择多个节点，把它们沉淀成一条用户判断，或者保存成主题分组。</p>
            <input v-model="synthesisLabel" placeholder="判断或主题名称" />
            <textarea v-model="synthesisReason" placeholder="为什么这些节点放在一起？" />
            <textarea v-model="themeDescription" placeholder="主题描述，可选" />
            <div>
              <button class="primary-button" :disabled="busy || selectedNodeIds.length < 2 || !synthesisLabel.trim() || !synthesisReason.trim()" @click="createThought">
                生成用户判断
              </button>
              <button class="paper-button" :disabled="busy || !selectedNodeIds.length || !synthesisLabel.trim()" @click="createTheme">
                保存主题
              </button>
            </div>
          </section>

          <section v-if="interactionMode === 'prune'" class="operation-card">
            <span>削弱 / 拒绝边</span>
            <p>选择一条边，再给出原因。削弱、拒绝、隐藏都必须说明理由。</p>
            <select v-model="pruneStatus">
              <option value="confirmed">确认</option>
              <option value="proposed">改为待确认</option>
              <option value="weakened">削弱</option>
              <option value="rejected">拒绝</option>
              <option value="hidden">隐藏</option>
            </select>
            <textarea v-model="pruneReason" placeholder="为什么这样处理这条边？" />
            <button class="primary-button" :disabled="busy || !selectedEdge || pruneNeedsReason" @click="updateEdgeStatus">
              更新边状态
            </button>
          </section>
        </article>

        <aside class="space-panel graph-inspector">
          <span>线索详情</span>
          <template v-if="selectedTheme">
            <strong>{{ selectedTheme.label }}</strong>
            <p>{{ selectedTheme.description || selectedTheme.reason || '这个主题还没有说明。' }}</p>
            <dl>
              <div>
                <dt>来源</dt>
                <dd>{{ originLabel(selectedTheme.origin) }}</dd>
              </div>
              <div>
                <dt>状态</dt>
                <dd>{{ graphStatusLabel(selectedTheme.status) }}</dd>
              </div>
              <div>
                <dt>线索数</dt>
                <dd>{{ selectedTheme.member_node_ids.length }}</dd>
              </div>
            </dl>
          </template>

          <template v-else-if="selectedEdge">
            <strong>{{ labelFor(selectedEdge.source) }} → {{ relationLabel(selectedEdge.relation) }} → {{ labelFor(selectedEdge.target) }}</strong>
            <p>{{ selectedEdge.explanation || selectedEdge.weakened_reason || selectedEdge.rejected_reason || '这条边还没有解释。' }}</p>
            <dl>
              <div>
                <dt>状态</dt>
                <dd>{{ graphStatusLabel(selectedEdge.status || 'confirmed') }}</dd>
              </div>
              <div>
                <dt>来源</dt>
                <dd>{{ originLabel(selectedEdge.origin || 'AI-inferred') }}</dd>
              </div>
              <div>
                <dt>可信度</dt>
                <dd>{{ confidenceLabel(selectedEdge.confidence) }}</dd>
              </div>
            </dl>
          </template>

          <template v-else-if="selectedNode">
            <strong>{{ selectedNode.label }}</strong>
            <p>{{ nodeSummary(selectedNode) }}</p>
            <dl>
              <div>
                <dt>类型</dt>
                <dd>{{ nodeTypeLabel(selectedNode.type) }}</dd>
              </div>
              <div>
                <dt>状态</dt>
                <dd>{{ graphStatusLabel(selectedNode.status || 'confirmed') }}</dd>
              </div>
              <div v-if="sourceForSelectedNode">
                <dt>保存理由</dt>
                <dd>{{ sourceToneLabel(sourceForSelectedNode) }}</dd>
              </div>
            </dl>
            <div class="inspector-actions">
              <button class="paper-button" :disabled="!sourceIdForSelectedNode" @click="openSource">
                <ExternalLink :size="15" />
                打开来源
              </button>
              <button class="paper-button" @click="askFromHere">
                <Search :size="15" />
                从这里追问
              </button>
            </div>

            <section v-if="sourceForSelectedNode" class="context-editor">
              <span>认知上下文</span>
              <label>
                <small>保存理由</small>
                <textarea v-model="editWhy" placeholder="这份材料当时为什么值得留下？" />
              </label>
              <label>
                <small>相关项目 / 问题</small>
                <input v-model="editProject" placeholder="例如：Thesis proposal" />
              </label>
              <label>
                <small>未闭环事项</small>
                <textarea v-model="editLoops" placeholder="每行一条" />
              </label>
              <button class="paper-button" :disabled="busy || !sourceForSelectedNode" @click="saveContext">
                更新上下文
              </button>
              <label>
                <small>移动到图谱</small>
                <select v-model="moveTarget">
                  <option v-for="item in routableSpaces" :key="item.id" :value="item.id">{{ displaySpaceName(item) }}</option>
                </select>
              </label>
              <button class="paper-button" :disabled="busy || !moveTarget || moveTarget === sourceForSelectedNode.graph_space_id" @click="routeSelected">
                移动材料
              </button>
            </section>
          </template>

          <div v-else class="graph-empty-inspector">
            <p>选择一个材料或节点，查看它为什么被保存、和哪些问题相连。</p>
          </div>

          <section v-if="sourceDetailOpen" class="source-markdown">
            <div>
              <span>来源内容</span>
              <button class="text-button" @click="sourceDetailOpen = false">收起</button>
            </div>
            <pre>{{ sourceDetail?.markdown }}</pre>
          </section>

          <p v-if="localError" class="local-error">{{ localError }}</p>
        </aside>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  ExternalLink,
  GitBranch,
  Hand,
  Layers,
  Map as MapIcon,
  Maximize2,
  Minimize2,
  Network,
  PencilLine,
  Route,
  Scissors,
  Search,
  X,
} from 'lucide-vue-next'
import type {
  ContextUpdatePayload,
  GraphEdge,
  GraphInteractionMode,
  GraphInsights,
  GraphLayoutPosition,
  GraphNode,
  GraphOpenLoopHotspot,
  GraphPayload,
  GraphProjectCluster,
  GraphReviewPath,
  GraphSpace,
  GraphTheme,
  GraphViewMode,
  SavedQuestion,
  SavedQuestionDetail,
  Source,
  SourceMapEntry,
  SourceMapPayload,
  SubgraphPayload,
  Suggestion,
  SyntheticEdge,
  PathResult,
} from '../types'
import GlobalSourceMap from './GlobalSourceMap.vue'
import SourceDrillDown from './SourceDrillDown.vue'

type GraphSurfaceMode = 'source-map' | 'overview' | 'workbench'
type OverviewOpenItem = {
  key: string
  title: string
  detail: string
  badge?: string
  tone?: string
}
type CloudItemKind = 'question' | 'future' | 'open' | 'source' | 'node'
type CloudEvidence = {
  id: string
  title: string
}
type CloudItem = {
  key: string
  kind: CloudItemKind
  kindLabel: string
  label: string
  detail: string
  weight: number
  tone: string
  nodeId?: string
  sourceId?: string
  questionId?: string
  question?: string
  evidenceTitles: CloudEvidence[]
}
type CloudDragState = {
  key: string
  pointerId: number
  startX: number
  startY: number
  originX: number
  originY: number
  active: boolean
  target: HTMLElement | null
}
type CloudDragFrame = {
  pointerId: number
  clientX: number
  clientY: number
}
type CloudGraphPoint = {
  x: number
  y: number
}
type CloudDragInfluence = {
  x: number
  y: number
  strength: number
}
type CloudGraphEdge = {
  id: string
  x1: number
  y1: number
  x2: number
  y2: number
  active: boolean
}

const CLOUD_DRAG_THRESHOLD = 4
const CLOUD_DRAG_INFLUENCE_PULL = 0.28
const CLOUD_SPRING_RESPONSE = 0.25
const CLOUD_SPRING_DAMPING = 0.6
const CLOUD_SPRING_SETTLE_MS = Math.round(CLOUD_SPRING_RESPONSE * 1000 + CLOUD_SPRING_DAMPING * 120 + 98)
const CLOUD_CLICK_SUPPRESSION_MS = CLOUD_SPRING_SETTLE_MS + 780

const props = defineProps<{
  busy: boolean
  space: GraphSpace | null
  spaces: GraphSpace[]
  sources: Source[]
  questions: SavedQuestion[]
  graph: GraphPayload
  suggestions: Suggestion[]
}>()

const emit = defineEmits<{
  updateSpace: [spaceId: string, payload: { name: string; purpose: string; description: string; color: string }]
  moveSource: [sourceId: string, spaceId: string]
  updateContext: [sourceId: string, payload: ContextUpdatePayload]
  acceptSuggestion: [suggestionId: string]
  rejectSuggestion: [suggestionId: string]
  graphChanged: []
  askFromGraph: [question: string]
}>()

const viewModes = [
  { id: 'memory' as const, label: '记忆脉络', icon: markRaw(MapIcon) },
  { id: 'evidence' as const, label: '证据路径', icon: markRaw(Route) },
  { id: 'action' as const, label: '下一步', icon: markRaw(Layers) },
]

const interactionModes = [
  { id: 'arrange' as const, label: '查看', icon: markRaw(Hand) },
  { id: 'connect' as const, label: '补连接', icon: markRaw(GitBranch) },
  { id: 'synthesize' as const, label: '归纳判断', icon: markRaw(PencilLine) },
  { id: 'prune' as const, label: '纠错', icon: markRaw(Scissors) },
]

const stageContainer = ref<HTMLDivElement | null>(null)
const cloudOrbitElement = ref<HTMLDivElement | null>(null)

const surfaceMode = ref<GraphSurfaceMode>('overview')
const viewMode = ref<GraphViewMode>('memory')
const interactionMode = ref<GraphInteractionMode>('arrange')
const layoutPositions = ref<GraphLayoutPosition[]>([])
const themes = ref<GraphTheme[]>([])
const selectedNodeIds = ref<string[]>([])
const selectedEdgeId = ref('')
const selectedThemeId = ref('')
const selectedCloudKey = ref('')
const selectedSource = ref<Source | null>(null)
const sourceDetail = ref<{ markdown: string; detail?: Source } | null>(null)
const sourceDetailOpen = ref(false)
const graphSearchQuery = ref('')
const selectedQuestionDetail = ref<SavedQuestionDetail | null>(null)
const questionDetailLoading = ref(false)
const questionDetailError = ref('')
const cloudDragOffsets = ref<Record<string, { x: number; y: number }>>({})
const cloudRecoilOffsets = ref<Record<string, CloudDragInfluence>>({})
const cloudRecoilKey = ref('')
const cloudReturnKey = ref('')
const draggingCloudKey = ref('')
const activeCloudDrag = ref<CloudDragState | null>(null)
const suppressedCloudClickKey = ref('')
const cloudOrbitSize = ref({ width: 560, height: 420 })
const sourceFilter = ref('')
const savingLayout = ref(false)
const graphExpanded = ref(false)
const localError = ref('')
const nodePositions = ref<Record<string, { x: number; y: number }>>({})
const draggingNodeId = ref('')
const pendingDragNodeId = ref('')
const pendingDragAddToSelection = ref(false)
const pendingDragStart = ref({ x: 0, y: 0 })
const graphFocusNodeId = ref('')
const nodeDragOffset = ref({ x: 0, y: 0 })
const graphZoom = ref(1)
const graphPan = ref({ x: 0, y: 0 })
const panningGraph = ref(false)
const lastPanPoint = ref({ x: 0, y: 0 })
let cloudResizeObserver: ResizeObserver | null = null
let cloudDragListenersAttached = false
let pendingCloudDragFrame: CloudDragFrame | null = null
let cloudDragAnimationFrame = 0
let cloudSpringAnimationFrame = 0
let cloudSpringStartedAt = 0
let cloudSpringEntries: [string, CloudDragInfluence][] = []
let suppressedCloudClickUntil = 0
const questionDetailCache = new Map<string, SavedQuestionDetail>()

const edgeRelation = ref('related_to')
const edgeReason = ref('')
const synthesisLabel = ref('')
const synthesisReason = ref('')
const themeDescription = ref('')
const pruneStatus = ref<'confirmed' | 'proposed' | 'rejected' | 'weakened' | 'hidden'>('weakened')
const pruneReason = ref('')

const moveTarget = ref('')
const editWhy = ref('')
const editProject = ref('')
const editLoops = ref('')
const editSpaceName = ref('')
const editSpacePurpose = ref('')
const editSpaceDescription = ref('')
const editSpaceColor = ref('#b0501e')

// Source-map state
type DrillDownState = {
  mode: 'expand' | 'thread'
  expandedSource: SourceMapEntry | null
  subgraphNodes: GraphNode[]
  subgraphEdges: GraphEdge[]
  threadNodes: GraphNode[]
  threadEdges: GraphEdge[]
  pathDescription: string
} | null
const sourceMapEntries = ref<SourceMapEntry[]>([])
const sourceMapSyntheticEdges = ref<SyntheticEdge[]>([])
const expandedSourceIds = ref<string[]>([])
const drillDownState = ref<DrillDownState | null>(null)

const graphSpaceId = computed(() => props.space?.id || 'all')
const spaceDisplayName = computed(() => props.space ? displaySpaceName(props.space) : '记忆空间')
const routableSpaces = computed(() => props.spaces.filter((space) => space.status === 'active' && space.id !== 'inbox'))
const insights = computed<GraphInsights>(() => props.graph.insights || {})
const projectClusters = computed<GraphProjectCluster[]>(() => insights.value.project_clusters || [])
const openLoopHotspots = computed<GraphOpenLoopHotspot[]>(() => insights.value.open_loop_hotspots || [])
const reviewPaths = computed<GraphReviewPath[]>(() => insights.value.high_value_review_paths || [])
const adjacencyCount = computed(() => {
  const counts = new Map<string, number>()
  for (const edge of props.graph.edges) {
    counts.set(edge.source, (counts.get(edge.source) || 0) + 1)
    counts.set(edge.target, (counts.get(edge.target) || 0) + 1)
  }
  return counts
})
const visibleSources = computed(() => {
  const query = sourceFilter.value.trim().toLowerCase()
  if (!query) return props.sources
  return props.sources.filter((source) => {
    return [source.title, source.why_saved, source.summary, source.related_project]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(query))
  })
})
const graphTransformStyle = computed(() => ({
  transform: `matrix(${graphZoom.value}, 0, 0, ${graphZoom.value}, ${graphPan.value.x}, ${graphPan.value.y})`,
}))
const anchorNodeId = computed(() => {
  if (graphFocusNodeId.value) return graphFocusNodeId.value
  const firstSource = props.sources[0]
  if (firstSource) return `source_${firstSource.id}`
  return props.graph.nodes.find((node) => node.type === 'source')?.id || props.graph.nodes[0]?.id || ''
})
const neighborhoodDistances = computed(() => {
  const anchor = anchorNodeId.value
  const distances = new Map<string, number>()
  if (!anchor) return distances
  distances.set(anchor, 0)
  const maxDepth = viewMode.value === 'action' ? 2 : 2
  const traversableEdges = props.graph.edges.filter((edge) => edge.status !== 'hidden')
  for (let depth = 0; depth < maxDepth; depth += 1) {
    const frontier = [...distances.entries()]
      .filter(([, distance]) => distance === depth)
      .map(([nodeId]) => nodeId)
    for (const nodeId of frontier) {
      for (const edge of traversableEdges) {
        if (edge.source === nodeId && !distances.has(edge.target)) distances.set(edge.target, depth + 1)
        if (edge.target === nodeId && !distances.has(edge.source)) distances.set(edge.source, depth + 1)
      }
    }
  }
  return distances
})
const visibleGraphNodes = computed(() => {
  const distances = neighborhoodDistances.value
  const maxNodes = viewMode.value === 'action' ? 18 : 14
  return props.graph.nodes
    .filter((node) => distances.has(node.id))
    .sort((a, b) => {
      const distanceDelta = (distances.get(a.id) || 0) - (distances.get(b.id) || 0)
      if (distanceDelta) return distanceDelta
      return nodeRank(a) - nodeRank(b)
    })
    .slice(0, maxNodes)
})
const visibleGraphNodeIds = computed(() => new Set(visibleGraphNodes.value.map((node) => node.id)))
const visibleGraphEdges = computed(() => {
  return props.graph.edges.filter((edge) => {
    if (edge.status === 'hidden' && interactionMode.value !== 'prune') return false
    return visibleGraphNodeIds.value.has(edge.source) && visibleGraphNodeIds.value.has(edge.target)
  })
})
const labeledGraphEdges = computed(() => {
  if (selectedEdge.value) return [selectedEdge.value]
  if (!graphExpanded.value) return []
  return visibleGraphEdges.value
    .filter((edge) => edge.origin === 'user' || edge.evidence_kind === 'user-stated')
    .slice(0, 2)
})
const selectedNode = computed(() => {
  const lastNodeId = selectedNodeIds.value[selectedNodeIds.value.length - 1]
  return props.graph.nodes.find((node) => node.id === lastNodeId) || null
})
const selectedEdge = computed(() => props.graph.edges.find((edge) => edge.id === selectedEdgeId.value) || null)
const selectedTheme = computed(() => themes.value.find((theme) => theme.id === selectedThemeId.value) || null)
const sourceIdForSelectedNode = computed(() => selectedNode.value ? sourceIdForNode(selectedNode.value) : '')
const sourceForSelectedNode = computed(() => {
  if (!sourceIdForSelectedNode.value) return null
  return props.sources.find((source) => source.id === sourceIdForSelectedNode.value) || null
})
const userStatedSourceCount = computed(() => {
  return props.sources.filter((source) => source.why_saved_status === 'user-stated').length
})
const aiInferredSourceCount = computed(() => {
  return props.sources.filter((source) => source.why_saved_status === 'AI-inferred').length
})
const missingReasonCount = computed(() => {
  return props.sources.filter((source) => !source.why_saved?.trim()).length
})
const reviewQueueCount = computed(() => {
  return props.suggestions.length + reviewPaths.value.length + aiInferredSourceCount.value + missingReasonCount.value
})
const latestActivityLabel = computed(() => {
  const sourceTime = [...props.sources]
    .map((source) => source.imported_at)
    .filter(Boolean)
    .sort((left, right) => Date.parse(right) - Date.parse(left))[0]
  const value = sourceTime || props.space?.updated_at || ''
  return value ? formatDate(value) : ''
})
const graphHeaderStats = computed(() => {
  const stats = [`${props.sources.length || props.space?.source_count || 0} 份材料`]
  if (userStatedSourceCount.value) stats.push(`${userStatedSourceCount.value} 条用户原话`)
  if (overviewOpenCount.value) stats.push(`${overviewOpenCount.value} 个待处理`)
  if (latestActivityLabel.value) stats.push(`最近 ${latestActivityLabel.value}`)
  return stats
})
const sourceIdsInSpace = computed(() => new Set(props.sources.map((source) => source.id)))
const questionsForSpace = computed(() => {
  if (!sourceIdsInSpace.value.size) return props.questions
  return props.questions.filter((question) => {
    if (!question.evidence_source_ids?.length) return true
    return question.evidence_source_ids.some((sourceId) => sourceIdsInSpace.value.has(sourceId))
  })
})
const cloudItems = computed<CloudItem[]>(() => {
  const items: CloudItem[] = []

  for (const question of questionsForSpace.value) {
    const evidenceTitles = evidenceForSourceIds(question.evidence_source_ids)
    pushCloudItem(items, {
      key: `question:${question.id}`,
      kind: 'question',
      kindLabel: '保存过的问题',
      label: question.question || '未命名问题',
      detail: evidenceTitles.length
        ? `这是一次真实追问历史，回答时引用了 ${evidenceTitles.length} 条证据。`
        : '这是一次真实追问历史，可以作为重新进入记忆的入口。',
      weight: 6 + evidenceTitles.length,
      tone: 'tone-graph',
      questionId: question.id,
      question: question.question,
      evidenceTitles,
    })
  }

  for (const source of props.sources) {
    for (const question of source.future_recall_questions || []) {
      pushCloudItem(items, {
        key: `future:${source.id}:${hashText(question)}`,
        kind: 'future',
        kindLabel: '材料暗示的问题',
        label: question,
        detail: `这条问题来自「${source.title}」的 future_recall_questions，用来提示以后怎么找回。`,
        weight: 5,
        tone: source.why_saved_status === 'user-stated' ? 'tone-user' : 'tone-ai',
        sourceId: source.id,
        question,
        evidenceTitles: [{ id: source.id, title: source.title }],
      })
    }

    for (const openLoop of source.open_loops || []) {
      pushCloudItem(items, {
        key: `open:${source.id}:${hashText(openLoop)}`,
        kind: 'open',
        kindLabel: '开放问题',
        label: openLoop,
        detail: `这是「${source.title}」留下的未闭环事项，适合继续追问或整理。`,
        weight: 5,
        tone: 'tone-ai',
        sourceId: source.id,
        question: openLoop,
        evidenceTitles: [{ id: source.id, title: source.title }],
      })
    }

    pushCloudItem(items, {
      key: `source:${source.id}`,
      kind: 'source',
      kindLabel: '材料',
      label: source.title,
      detail: sourcePreview(source),
      weight: 3 + (source.why_saved_status === 'user-stated' ? 1 : 0) + Math.min(2, source.open_loops?.length || 0),
      tone: sourceToneClass(source),
      sourceId: source.id,
      evidenceTitles: [{ id: source.id, title: source.title }],
    })
  }

  for (const node of overviewKeyNodes.value) {
    const sourceId = sourceIdForNode(node)
    const source = sourceId ? props.sources.find((item) => item.id === sourceId) : null
    pushCloudItem(items, {
      key: `node:${node.id}`,
      kind: 'node',
      kindLabel: nodeTypeLabel(node.type),
      label: node.label,
      detail: keyNodeSummary(node),
      weight: 3 + Math.min(4, adjacencyCount.value.get(node.id) || 0),
      tone: nodeToneClass(node),
      nodeId: node.id,
      sourceId,
      evidenceTitles: source ? [{ id: source.id, title: source.title }] : [],
    })
  }

  return items.sort((left, right) => right.weight - left.weight).slice(0, 36)
})
const visibleCloudItems = computed(() => {
  const query = normalizeSearchText(graphSearchQuery.value)
  return cloudItems.value
    .filter((item) => !query || cloudSearchText(item).includes(query))
    .sort((left, right) => {
      if (!query) return right.weight - left.weight
      return cloudMatchScore(right, query) - cloudMatchScore(left, query)
    })
    .slice(0, 18)
})
const cloudGraphPoints = computed<Record<string, CloudGraphPoint>>(() => {
  const next: Record<string, CloudGraphPoint> = {}
  visibleCloudItems.value.forEach((item, index) => {
    next[item.key] = cloudGraphPoint(item, index)
  })
  return next
})
const cloudDragInfluenceOffsets = computed<Record<string, CloudDragInfluence>>(() => {
  const activeOffsets = activeCloudDragInfluenceOffsets()
  if (Object.keys(activeOffsets).length) return activeOffsets
  return cloudRecoilOffsets.value
})
const selectedCloudItem = computed(() => {
  if (!selectedCloudKey.value) return null
  return visibleCloudItems.value.find((item) => item.key === selectedCloudKey.value) || null
})
const selectedCloudPoint = computed(() => {
  if (!selectedCloudKey.value) return null
  if (!selectedCloudItem.value) return null
  return cloudGraphPoints.value[selectedCloudItem.value.key] || null
})
const selectedQuestionAnswerBlocks = computed(() => splitHistoryAnswer(selectedQuestionDetail.value?.answer || ''))

function activeCloudDragInfluenceOffsets() {
  const drag = activeCloudDrag.value
  if (!drag?.active) return {}

  const anchorIndex = visibleCloudItems.value.findIndex((item) => item.key === drag.key)
  const anchor = visibleCloudItems.value[anchorIndex]
  if (!anchor) return {}

  const anchorOffset = cloudDragOffsets.value[drag.key] || { x: drag.originX, y: drag.originY }
  const deltaX = anchorOffset.x - drag.originX
  const deltaY = anchorOffset.y - drag.originY
  if (Math.hypot(deltaX, deltaY) < 1) return {}

  const query = normalizeSearchText(graphSearchQuery.value)
  const entries = visibleCloudItems.value.flatMap((item, index) => {
    if (item.key === drag.key) return []
    const strength = cloudElasticInfluence(anchor, item, query, anchorIndex, index)
    if (strength <= 0) return []
    return [[item.key, {
      x: roundCloudMotion(deltaX * strength * CLOUD_DRAG_INFLUENCE_PULL),
      y: roundCloudMotion(deltaY * strength * CLOUD_DRAG_INFLUENCE_PULL),
      strength,
    }] as const]
  })
  return Object.fromEntries(entries.sort(([, left], [, right]) => right.strength - left.strength).slice(0, 6))
}
const cloudFocusLabelStyle = computed(() => {
  const point = selectedCloudPoint.value
  if (!point) return {}
  return {
    left: `${point.x}px`,
    top: `${point.y}px`,
  }
})
const cloudConstellationEdges = computed<CloudGraphEdge[]>(() => {
  const activeDrag = activeCloudDrag.value?.active ? activeCloudDrag.value : null
  const anchor = activeDrag
    ? visibleCloudItems.value.find((item) => item.key === activeDrag.key) || selectedCloudItem.value
    : selectedCloudKey.value ? selectedCloudItem.value : null
  const anchorPoint = anchor ? cloudGraphPoints.value[anchor.key] : null
  if (!anchor || !anchorPoint) return []

  const query = normalizeSearchText(graphSearchQuery.value)
  return visibleCloudItems.value
    .filter((item) => item.key !== anchor.key)
    .map((item) => {
      const point = cloudGraphPoints.value[item.key]
      return {
        item,
        point,
        score: cloudAffinityScore(anchor, item, query),
      }
    })
    .filter((entry) => entry.point && entry.score > 0)
    .sort((left, right) => right.score - left.score)
    .slice(0, 7)
    .map(({ item, point }) => ({
      id: `${anchor.key}->${item.key}`,
      x1: anchorPoint.x,
      y1: anchorPoint.y,
      x2: point.x,
      y2: point.y,
      active: Boolean(activeDrag)
        ? item.key === activeDrag.key || Boolean(cloudDragInfluenceOffsets.value[item.key])
        : isCloudMatch(item) || isCloudMatch(anchor),
    }))
})
const overviewProjects = computed(() => projectClusters.value.slice(0, 3))
const overviewRecentSources = computed(() => {
  return [...props.sources]
    .sort((left, right) => Date.parse(right.imported_at || '') - Date.parse(left.imported_at || ''))
    .slice(0, 4)
})
const overviewKeyNodes = computed(() => {
  const preferredTypes = ['project', 'thought', 'task', 'question']
  const importantNodes = props.graph.nodes
    .filter((node) => preferredTypes.includes(node.type))
    .sort((left, right) => {
      const typeDelta = preferredTypes.indexOf(left.type) - preferredTypes.indexOf(right.type)
      if (typeDelta) return typeDelta
      return (adjacencyCount.value.get(right.id) || 0) - (adjacencyCount.value.get(left.id) || 0)
    })
  const fallbackNodes = props.graph.nodes
    .filter((node) => !importantNodes.find((item) => item.id === node.id))
    .sort((left, right) => (adjacencyCount.value.get(right.id) || 0) - (adjacencyCount.value.get(left.id) || 0))
  return [...importantNodes, ...fallbackNodes].slice(0, 5)
})
const overviewOpenItems = computed<OverviewOpenItem[]>(() => {
  const hotspotItems = openLoopHotspots.value.slice(0, 4).map((item) => ({
    key: `hotspot:${item.open_loop}`,
    title: item.open_loop,
    detail: item.count > 1 ? `来自 ${item.count} 条材料的开放问题。` : `来自 ${item.sources[0]?.title || '当前材料'} 的开放问题。`,
    badge: item.sources[0]?.status === 'user-stated' ? 'user-stated / 用户原话' : 'AI-inferred / AI 推断',
    tone: item.sources[0]?.status === 'user-stated' ? 'tone-user' : 'tone-ai',
  }))
  const suggestionItems = props.suggestions.slice(0, 3).map((suggestion) => ({
    key: `suggestion:${suggestion.id}`,
    title: routeSuggestionReasonText(suggestion),
    detail: `${Math.round(suggestion.confidence * 100)}% 置信度，等待你确认是否采纳。`,
    badge: 'graph-path / 图谱建议',
    tone: 'tone-graph',
  }))
  const pathItems = reviewPaths.value.slice(0, 2).map((item) => ({
    key: `path:${item.source_id}:${item.path}`,
    title: item.title,
    detail: item.why || '这条路径提示了一个值得继续追问的判断连接。',
    badge: item.status === 'user-stated' ? 'user-stated / 用户原话' : 'AI-inferred / AI 推断',
    tone: item.status === 'user-stated' ? 'tone-user' : 'tone-ai',
  }))
  return [...hotspotItems, ...suggestionItems, ...pathItems].slice(0, 6)
})
const overviewOpenCount = computed(() => {
  if (openLoopHotspots.value.length) return openLoopHotspots.value.length
  if (props.suggestions.length) return props.suggestions.length
  if (reviewPaths.value.length) return reviewPaths.value.length
  return props.sources.reduce((total, source) => total + (source.open_loops?.length || 0), 0)
})
const overviewOpenLabel = computed(() => {
  return props.suggestions.length ? '建议' : '开放问题'
})
const openLoopGuidance = computed(() => {
  if (openLoopHotspots.value.length) {
    const count = openLoopHotspots.value[0]?.count || 1
    return count > 1 ? `先看重复出现 ${count} 次的问题。` : '先处理最像下一步的开放问题。'
  }
  if (props.suggestions.length) return '先确认系统建议是否符合你的真实意图。'
  if (reviewPaths.value.length) return '先检查最有价值的证据路径。'
  if (missingReasonCount.value) return '先补上材料为什么值得保存。'
  return '继续保存材料后，这里会出现下一步。'
})
const spacePromptExamples = computed(() => {
  const prompts: string[] = []
  const leadProject = overviewProjects.value[0]?.project || overviewKeyNodes.value.find((node) => node.type === 'project')?.label
  const leadOpenLoop = overviewOpenItems.value[0]?.title
  const leadSource = overviewRecentSources.value[0]?.title
  if (leadProject) prompts.push(`我之前为什么关注「${promptSubject(leadProject)}」？`)
  if (leadOpenLoop) prompts.push(`这个未闭环问题下一步该怎么处理：「${promptSubject(leadOpenLoop)}」？`)
  if (leadSource) prompts.push(`「${promptSubject(leadSource)}」里哪些证据支持我当时的判断？`)
  prompts.push('这个空间里最重要的旧判断是什么？')
  prompts.push('哪些证据是用户原话，哪些是 AI 推断？')
  return [...new Set(prompts)].slice(0, 3)
})
const spaceDescription = computed(() => {
  if (props.space?.id === 'inbox') {
    return '新材料会先放在这里，等待确认和整理。'
  }
  if (props.space?.id === 'default') {
    return '默认记忆空间，保存当前 SnapGraph 工作流的主要材料、判断和开放问题。'
  }
  return props.space?.purpose || props.space?.description || '这个空间保存了相关材料、想法和连接，用来帮助之后找回判断。'
})
const overviewSummary = computed(() => {
  const projectList = overviewProjects.value.map((item) => item.project).filter(Boolean)
  if (projectList.length) {
    const lead = projectList.slice(0, 2).join('、')
    const openCount = overviewOpenCount.value
    if (openCount) {
      return `这个空间现在主要围绕 ${lead} 这些主题组织材料，并把 ${openCount} 个待继续处理的问题保留下来，方便之后找回判断。`
    }
    return `这个空间现在主要围绕 ${lead} 这些主题组织材料，把来源、想法和连接整理成可回看的判断脉络。`
  }
  if (props.sources.length || props.graph.nodes.length) {
    return '这个空间保存了相关材料、想法和连接，用来帮助之后找回判断。'
  }
  return '这个空间保存了相关材料、想法和连接，用来帮助之后找回判断。'
})
const pruneNeedsReason = computed(() => {
  return ['rejected', 'weakened', 'hidden'].includes(pruneStatus.value) && !pruneReason.value.trim()
})
const currentViewLabel = computed(() => viewModes.find((mode) => mode.id === viewMode.value)?.label || 'Memory Map')
const modeDescription = computed(() => {
  if (viewMode.value === 'evidence') return '查看某个回答或判断背后的证据路径。'
  if (viewMode.value === 'action') return '查看开放问题、下一步和待处理连接。'
  return '查看这个空间里材料、想法和项目之间的整体结构。'
})
const selectionSummary = computed(() => {
  const nodeCount = selectedNodeIds.value.length
  if (selectedEdge.value) return `已选择 1 条边：${selectedEdge.value.relation}`
  if (nodeCount) return `已选择 ${nodeCount} 个节点`
  return '点击节点或边查看细节；按 Shift 可多选节点。'
})
const interactionGuide = computed(() => {
  if (interactionMode.value === 'connect') {
    return '连续点两个节点，再写关系和原因。再次点击已选节点会取消选择。'
  }
  if (interactionMode.value === 'synthesize') {
    return '连续点多个节点，把它们归纳成一条用户判断，或者保存成一个主题分组。'
  }
  if (interactionMode.value === 'prune') {
    return '点击一条边，确认、削弱或拒绝它。削弱/拒绝/隐藏都必须写原因，方便以后追溯。'
  }
  return '默认只展示当前材料附近的证据路径。点圆点看细节，双击画布放大；想继续追问，点右侧“从这里追问”。'
})

watch(() => props.space, (space) => {
  editSpaceName.value = space?.name || ''
  editSpacePurpose.value = space?.purpose || ''
  editSpaceDescription.value = space?.description || ''
  editSpaceColor.value = space?.color || '#b0501e'
  surfaceMode.value = 'source-map'
  selectedSource.value = null
  selectedNodeIds.value = []
  selectedEdgeId.value = ''
  selectedThemeId.value = ''
  selectedCloudKey.value = ''
  graphSearchQuery.value = ''
  graphExpanded.value = false
  graphFocusNodeId.value = ''
  drillDownState.value = null
  expandedSourceIds.value = []
  resetGraphView()
  if (space) {
    loadLayout()
    loadThemes()
    loadSourceMap()
  }
}, { immediate: true })

watch(selectedSource, (source) => {
  moveTarget.value = source?.graph_space_id || props.space?.id || 'default'
  editWhy.value = source?.why_saved || ''
  editProject.value = source?.related_project || ''
  editLoops.value = source?.open_loops?.join('\n') || ''
})

watch(sourceForSelectedNode, (source) => {
  if (!source) return
  selectedSource.value = source
}, { immediate: true })

watch(() => props.sources, (sources) => {
  if (!sources.length) {
    selectedSource.value = null
    selectedNodeIds.value = []
    graphFocusNodeId.value = ''
    return
  }
  if (!selectedSource.value) {
    graphFocusNodeId.value = `source_${sources[0].id}`
    selectedNodeIds.value = []
    return
  }
  selectedSource.value = sources.find((source) => source.id === selectedSource.value?.id) || null
  if (!graphFocusNodeId.value) {
    graphFocusNodeId.value = `source_${selectedSource.value?.id || sources[0].id}`
  }
}, { immediate: true })

watch([() => props.graph.nodes, layoutPositions, viewMode, graphFocusNodeId], () => {
  syncNodePositions()
}, { deep: true, immediate: true })

watch(cloudOrbitElement, (element, previous) => {
  if (previous) cloudResizeObserver?.unobserve(previous)
  if (!element) return
  cloudResizeObserver?.observe(element)
  syncCloudOrbitSize()
}, { flush: 'post' })

watch(visibleCloudItems, (items) => {
  if (!items.length) {
    selectedCloudKey.value = ''
    return
  }
  if (!items.some((item) => item.key === selectedCloudKey.value)) {
    selectedCloudKey.value = ''
  }
}, { immediate: true })

onMounted(() => {
  cloudResizeObserver = new ResizeObserver(() => syncCloudOrbitSize())
  if (cloudOrbitElement.value) cloudResizeObserver.observe(cloudOrbitElement.value)
  nextTick(syncCloudOrbitSize)
})

onBeforeUnmount(() => {
  cloudResizeObserver?.disconnect()
  clearPendingCloudDragFrame()
  clearCloudRecoil()
  clearCloudReturn()
  cancelCloudDrag()
  stopNodeDrag()
  stopGraphPan()
})

async function loadLayout() {
  if (!props.space) return
  try {
    const payload = await api<{ positions: GraphLayoutPosition[] }>(`/api/graph/layout?view_id=${encodeURIComponent(viewId())}`)
    layoutPositions.value = payload.positions || []
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function loadThemes() {
  if (!props.space) return
  try {
    const payload = await api<{ themes: GraphTheme[] }>(`/api/graph/themes?space_id=${encodeURIComponent(props.space.id)}`)
    themes.value = payload.themes || []
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function loadSourceMap() {
  if (!props.space) return
  try {
    const payload = await api<SourceMapPayload>(
      `/api/spaces/${encodeURIComponent(props.space.id)}/source-map`
    )
    sourceMapEntries.value = payload.sources
    sourceMapSyntheticEdges.value = payload.synthetic_edges
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function handleExpandSource(nodeId: string) {
  const actualId = nodeId.startsWith('source_') ? nodeId.slice('source_'.length) : nodeId
  try {
    const focusGraph = await api<SubgraphPayload>(
      `/api/spaces/${encodeURIComponent(props.space?.id || 'all')}/sources/${encodeURIComponent(actualId)}/expand`
    )
    const source = sourceMapEntries.value.find((s) => s.node.id === nodeId)
    drillDownState.value = {
      mode: 'expand',
      expandedSource: source || null,
      subgraphNodes: focusGraph.nodes || [],
      subgraphEdges: focusGraph.edges || [],
      threadNodes: [],
      threadEdges: [],
      pathDescription: '',
    }
    if (!expandedSourceIds.value.includes(nodeId)) {
      expandedSourceIds.value.push(nodeId)
    }
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function handleTraceThread(sourceIds: string[]) {
  const actualIds = sourceIds.map((id) => id.startsWith('source_') ? id.slice('source_'.length) : id)
  try {
    const result = await api<PathResult>('/api/graph/path', {
      method: 'POST',
      body: JSON.stringify({
        source_ids: actualIds,
        space_id: props.space?.id || 'all',
      }),
    })
    drillDownState.value = {
      mode: 'thread',
      expandedSource: null,
      subgraphNodes: [],
      subgraphEdges: [],
      threadNodes: result.path_nodes,
      threadEdges: result.path_edges,
      pathDescription: result.path_description,
    }
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function openSourceDetail(sourceId: string) {
  try {
    const payload = await api<{ markdown: string }>(`/api/sources/${encodeURIComponent(sourceId)}`)
    sourceDetail.value = { markdown: payload.markdown }
    sourceDetailOpen.value = true
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

function syncNodePositions() {
  const saved = new Map(layoutPositions.value.map((position) => [position.node_id, position]))
  const next: Record<string, { x: number; y: number }> = {}
  const nodes = visibleGraphNodes.value
  nodes.forEach((node, index) => {
    const existing = nodePositions.value[node.id]
    const persisted = saved.get(node.id)
    if (persisted?.locked) {
      next[node.id] = { x: clampGraphX(persisted.x), y: clampGraphY(persisted.y) }
    } else if (existing) {
      next[node.id] = existing
    } else {
      next[node.id] = fallbackPosition(index, Math.max(nodes.length, 1), node)
    }
  })
  nodePositions.value = next
}

async function saveCurrentLayout() {
  if (!props.space) return
  savingLayout.value = true
  localError.value = ''
  try {
    const positions = visibleGraphNodes.value.map((node) => ({
      node_id: node.id,
      x: nodePositions.value[node.id]?.x ?? 500,
      y: nodePositions.value[node.id]?.y ?? 340,
      locked: true,
    }))
    await api('/api/graph/layout', {
      method: 'PATCH',
      body: JSON.stringify({
        view_id: viewId(),
        graph_space_id: props.space.id,
        positions,
      }),
    })
    layoutPositions.value = positions
  } catch (error) {
    localError.value = messageFromError(error)
  } finally {
    savingLayout.value = false
  }
}

function selectSource(source: Source) {
  selectedSource.value = source
  selectedThemeId.value = ''
  selectedEdgeId.value = ''
  const nodeId = `source_${source.id}`
  graphFocusNodeId.value = nodeId
  selectedNodeIds.value = [nodeId]
}

function selectTheme(themeId: string) {
  selectedThemeId.value = themeId
  selectedEdgeId.value = ''
  selectedNodeIds.value = themes.value.find((item) => item.id === themeId)?.member_node_ids || []
  selectedSource.value = null
}

function clearSelection() {
  selectedNodeIds.value = []
  selectedEdgeId.value = ''
  selectedThemeId.value = ''
  selectedSource.value = null
}

function setInteractionMode(mode: GraphInteractionMode) {
  interactionMode.value = mode
  clearSelection()
}

async function createEdge() {
  const [source, target] = selectedNodeIds.value
  if (!props.space || !source || !target) return
  localError.value = ''
  try {
    await api('/api/graph/edges', {
      method: 'POST',
      body: JSON.stringify({
        source,
        target,
        relation: edgeRelation.value.trim() || 'related_to',
        reason: edgeReason.value.trim(),
        graph_space_id: props.space.id,
      }),
    })
    edgeReason.value = ''
    emit('graphChanged')
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function createThought() {
  if (!props.space) return
  localError.value = ''
  try {
    await api('/api/graph/thoughts', {
      method: 'POST',
      body: JSON.stringify({
        graph_space_id: props.space.id,
        node_ids: selectedNodeIds.value,
        label: synthesisLabel.value.trim(),
        reason: synthesisReason.value.trim(),
      }),
    })
    synthesisLabel.value = ''
    synthesisReason.value = ''
    emit('graphChanged')
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function createTheme() {
  if (!props.space) return
  localError.value = ''
  try {
    await api('/api/graph/themes', {
      method: 'POST',
      body: JSON.stringify({
        graph_space_id: props.space.id,
        label: synthesisLabel.value.trim(),
        member_node_ids: selectedNodeIds.value,
        reason: synthesisReason.value.trim(),
        description: themeDescription.value.trim(),
      }),
    })
    synthesisLabel.value = ''
    synthesisReason.value = ''
    themeDescription.value = ''
    await loadThemes()
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function updateEdgeStatus() {
  if (!selectedEdge.value) return
  localError.value = ''
  try {
    await api(`/api/graph/edges/${encodeURIComponent(selectedEdge.value.id)}`, {
      method: 'PATCH',
      body: JSON.stringify({
        status: pruneStatus.value,
        reason: pruneReason.value.trim(),
      }),
    })
    pruneReason.value = ''
    emit('graphChanged')
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

async function openSource() {
  const sourceId = sourceIdForSelectedNode.value
  if (!sourceId) return
  localError.value = ''
  try {
    sourceDetail.value = await api<{ markdown: string; detail?: Source }>(`/api/sources/${encodeURIComponent(sourceId)}`)
    sourceDetailOpen.value = true
  } catch (error) {
    localError.value = messageFromError(error)
  }
}

function askFromHere() {
  const clue = selectedNode.value?.label || sourceForSelectedNode.value?.title
  if (!clue) return
  emit('askFromGraph', `我之前关于「${clue}」想过什么？`)
}

function routeSelected() {
  const source = sourceForSelectedNode.value
  if (source && moveTarget.value) {
    emit('moveSource', source.id, moveTarget.value)
  }
}

function saveContext() {
  const source = sourceForSelectedNode.value
  if (!source) return
  emit('updateContext', source.id, {
    why_saved: editWhy.value.trim(),
    related_project: editProject.value.trim(),
    open_loops: editLoops.value
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean),
    confirm: true,
  })
}

function saveSpace() {
  if (!props.space) return
  emit('updateSpace', props.space.id, {
    name: editSpaceName.value.trim(),
    purpose: editSpacePurpose.value.trim(),
    description: editSpaceDescription.value.trim(),
    color: editSpaceColor.value,
  })
}

function displaySpaceName(space: GraphSpace) {
  if (space.id === 'inbox') return '待整理'
  if (space.id === 'default') return '主记忆'
  return space.name
}

function routeSuggestionReasonText(suggestion: Suggestion) {
  return sanitizeBuiltInSpaceNames(suggestion.reason)
}

function sanitizeBuiltInSpaceNames(text = '') {
  return text
    .replace(/\bInbox\b/g, '待整理')
    .replace(/\binbox\b/g, '待整理')
    .replace(/\bDefault\b/g, '主记忆')
    .replace(/\bdefault\b/g, '主记忆')
}

function askFromSpace() {
  emit('askFromGraph', '帮我找回这个空间里最重要的旧判断和证据。')
}

function openActionWorkbench() {
  surfaceMode.value = 'workbench'
  viewMode.value = 'action'
  interactionMode.value = 'arrange'
  clearSelection()
}

function openAuditWorkbench() {
  surfaceMode.value = 'workbench'
  viewMode.value = 'evidence'
  interactionMode.value = 'arrange'
  clearSelection()
}

function askSuggestedPrompt(prompt: string) {
  emit('askFromGraph', prompt)
}

function askCloudSearch() {
  const query = graphSearchQuery.value.trim()
  if (!query) {
    askFromSpace()
    return
  }
  emit('askFromGraph', `帮我从这个空间的记忆星图里找「${query}」相关线索。`)
}

function askFromCloud(item: CloudItem) {
  const question = item.question || `我之前关于「${item.label}」想过什么？`
  emit('askFromGraph', question)
}

function continueFromCloud(item: CloudItem) {
  if (item.kind === 'question') {
    selectedCloudKey.value = item.key
    void openCloudQuestionHistory(item)
    return
  }
  askFromCloud(item)
}

async function openCloudQuestionHistory(item: CloudItem) {
  if (!item.questionId) return
  selectedCloudKey.value = item.key
  questionDetailError.value = ''
  const cached = questionDetailCache.get(item.questionId)
  if (cached) {
    selectedQuestionDetail.value = cached
    return
  }
  questionDetailLoading.value = true
  try {
    const detail = await api<SavedQuestionDetail>(`/api/questions/${encodeURIComponent(item.questionId)}`)
    questionDetailCache.set(item.questionId, detail)
    selectedQuestionDetail.value = detail
  } catch (error) {
    questionDetailError.value = `历史问答打开失败：${messageFromError(error)}`
  } finally {
    questionDetailLoading.value = false
  }
}

function closeQuestionHistory() {
  selectedQuestionDetail.value = null
  questionDetailLoading.value = false
  questionDetailError.value = ''
}

function continueFromQuestionHistory() {
  const question = selectedQuestionDetail.value?.question || selectedCloudItem.value?.question
  if (!question) return
  emit('askFromGraph', question)
}

function focusQuestionEvidence() {
  const detail = selectedQuestionDetail.value
  if (!detail?.evidence_source_ids.length) return
  const source = props.sources.find((item) => detail.evidence_source_ids.includes(item.id))
  if (source) {
    focusCloudItem({
      key: `source:${source.id}`,
      kind: 'source',
      kindLabel: '材料',
      label: source.title,
      detail: sourcePreview(source),
      weight: 4,
      tone: sourceToneClass(source),
      sourceId: source.id,
      evidenceTitles: [{ id: source.id, title: source.title }],
    })
  }
}

function focusCloudItem(item: CloudItem) {
  surfaceMode.value = 'workbench'
  viewMode.value = item.kind === 'open' ? 'action' : 'evidence'
  interactionMode.value = 'arrange'
  selectedCloudKey.value = item.key
  if (item.nodeId) {
    graphFocusNodeId.value = item.nodeId
    selectedNodeIds.value = [item.nodeId]
    selectedEdgeId.value = ''
    selectedThemeId.value = ''
    return
  }
  if (item.sourceId) {
    const source = props.sources.find((sourceItem) => sourceItem.id === item.sourceId)
    if (source) selectSource(source)
  }
}

function selectSourceById(sourceId: string) {
  const source = props.sources.find((item) => item.id === sourceId)
  if (source) selectSource(source)
}

function clearCloudSearch() {
  graphSearchQuery.value = ''
}

function syncCloudOrbitSize() {
  const element = cloudOrbitElement.value
  if (!element) return
  const rect = element.getBoundingClientRect()
  cloudOrbitSize.value = {
    width: Math.max(320, Math.round(element.clientWidth || rect.width)),
    height: Math.max(320, Math.round(element.clientHeight || rect.height)),
  }
}

function cloudGraphPoint(item: CloudItem, index: number) {
  const base = cloudNodeBasePosition(index)
  const dragOffset = cloudRenderOffset(item.key)
  const width = cloudOrbitSize.value.width
  const height = cloudOrbitSize.value.height
  return {
    x: roundCloudMotion((base.left / 100) * width + dragOffset.x),
    y: roundCloudMotion((base.top / 100) * height + dragOffset.y),
  }
}

function cloudRenderOffset(key: string) {
  const persisted = cloudDragOffsets.value[key] || { x: 0, y: 0 }
  const influence = cloudInfluenceOffset(key)
  const springOwnsOffset = Boolean(cloudReturnKey.value || cloudRecoilKey.value) && Boolean(cloudDragOffsets.value[key])
  return {
    x: roundCloudMotion(persisted.x + (springOwnsOffset ? 0 : influence.x)),
    y: roundCloudMotion(persisted.y + (springOwnsOffset ? 0 : influence.y)),
  }
}

function cloudInfluenceOffset(key: string) {
  return cloudDragInfluenceOffsets.value[key] || { x: 0, y: 0, strength: 0 }
}

function roundCloudMotion(value: number) {
  if (Math.abs(value) < 0.01) return 0
  return Number(value.toFixed(2))
}

function cloudNodeBasePosition(index: number) {
  const positions = [
    [50, 50],
    [43, 36],
    [58, 35],
    [39, 62],
    [61, 62],
    [33, 49],
    [69, 49],
    [50, 26],
    [50, 72],
    [28, 34],
    [72, 34],
    [30, 74],
    [72, 74],
    [41, 23],
    [59, 24],
    [42, 78],
    [61, 77],
    [24, 53],
  ]
  const [left, top] = positions[index % positions.length]
  return { left, top }
}

function isCloudMatch(item: CloudItem) {
  const query = normalizeSearchText(graphSearchQuery.value)
  return !query || cloudSearchText(item).includes(query)
}

function cloudAffinityScore(anchor: CloudItem, candidate: CloudItem, query: string) {
  let score = 0
  if (anchor.kind === candidate.kind) score += 2
  if (anchor.tone === candidate.tone) score += 1
  if (anchor.sourceId && anchor.sourceId === candidate.sourceId) score += 5
  if (anchor.nodeId && anchor.nodeId === candidate.nodeId) score += 4
  if (query && cloudSearchText(candidate).includes(query)) score += 6
  score += sharedCloudEvidenceCount(anchor, candidate) * 4
  score += Math.min(3, candidate.weight / 3)
  return score
}

function cloudElasticInfluence(
  anchor: CloudItem,
  candidate: CloudItem,
  query: string,
  anchorIndex: number,
  candidateIndex: number,
) {
  const anchorBase = cloudNodeBasePosition(anchorIndex)
  const candidateBase = cloudNodeBasePosition(candidateIndex)
  const distanceX = ((candidateBase.left - anchorBase.left) / 100) * cloudOrbitSize.value.width
  const distanceY = ((candidateBase.top - anchorBase.top) / 100) * cloudOrbitSize.value.height
  const distance = Math.hypot(distanceX, distanceY)
  const influenceRadius = Math.max(220, Math.min(cloudOrbitSize.value.width, cloudOrbitSize.value.height) * 0.72)
  const distancePull = Math.max(0, 1 - distance / influenceRadius)
  const affinity = cloudAffinityScore(anchor, candidate, query)
  const semanticPull = Math.min(0.22, Math.max(0, affinity - 2) / 32)
  const evidencePull = sharedCloudEvidenceCount(anchor, candidate) > 0 ? 0.1 : 0
  const sourcePull = anchor.sourceId && anchor.sourceId === candidate.sourceId ? 0.12 : 0
  const searchPull = query && cloudSearchText(candidate).includes(query) ? 0.08 : 0
  const kindPull = anchor.kind === candidate.kind ? 0.04 : 0
  const strength = Math.min(0.38, distancePull * 0.2 + semanticPull + evidencePull + sourcePull + searchPull + kindPull)
  return strength >= 0.12 ? Number(strength.toFixed(3)) : 0
}

function sharedCloudEvidenceCount(left: CloudItem, right: CloudItem) {
  const rightIds = new Set(right.evidenceTitles.map((item) => item.id))
  return left.evidenceTitles.filter((item) => rightIds.has(item.id)).length
}

async function selectCloudNode(event: MouseEvent, item: CloudItem) {
  if (shouldSuppressCloudClick(item)) {
    event.preventDefault()
    return
  }
  selectedCloudKey.value = item.key
  if (item.kind === 'question') {
    await openCloudQuestionHistory(item)
    return
  }
  closeQuestionHistory()
}

function shouldSuppressCloudClick(item: CloudItem) {
  const now = performanceNow()
  if (suppressedCloudClickKey.value && now >= suppressedCloudClickUntil) {
    suppressedCloudClickKey.value = ''
    suppressedCloudClickUntil = 0
  }
  return suppressedCloudClickKey.value === item.key && now < suppressedCloudClickUntil
}

function suppressCloudClick(key: string) {
  suppressedCloudClickKey.value = key
  suppressedCloudClickUntil = performanceNow() + CLOUD_CLICK_SUPPRESSION_MS
  window.setTimeout(() => {
    if (suppressedCloudClickKey.value === key && performanceNow() >= suppressedCloudClickUntil) {
      suppressedCloudClickKey.value = ''
      suppressedCloudClickUntil = 0
    }
  }, CLOUD_CLICK_SUPPRESSION_MS)
}

function performanceNow() {
  return window.performance?.now?.() ?? Date.now()
}

function startCloudDrag(event: PointerEvent, item: CloudItem) {
  if (event.button !== 0) return
  if ('isPrimary' in event && !event.isPrimary) return
  beginCloudDrag(event, item, event.pointerId)
  const drag = activeCloudDrag.value
  if (drag?.pointerId === event.pointerId) {
    drag.target?.setPointerCapture?.(event.pointerId)
  }
}

function beginCloudDrag(event: PointerEvent, item: CloudItem, pointerId: number) {
  clearCloudRecoil()
  clearPendingCloudDragFrame()
  clearCloudDragOffsets()
  const existing = cloudDragOffsets.value[item.key] || { x: 0, y: 0 }
  const target = event.currentTarget instanceof HTMLElement ? event.currentTarget : null
  selectedCloudKey.value = item.key
  activeCloudDrag.value = {
    key: item.key,
    pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: existing.x,
    originY: existing.y,
    active: false,
    target,
  }
  attachCloudDragListeners()
}

function moveCloudDrag(event: PointerEvent) {
  moveCloudDragFrame(event, event.pointerId)
}

function moveCloudDragFrame(event: PointerEvent, pointerId: number) {
  const drag = activeCloudDrag.value
  if (!drag || drag.pointerId !== pointerId) return
  event.preventDefault()
  pendingCloudDragFrame = {
    pointerId,
    clientX: event.clientX,
    clientY: event.clientY,
  }
  if (!cloudDragAnimationFrame) {
    cloudDragAnimationFrame = window.requestAnimationFrame(applyPendingCloudDragFrame)
  }
}

function applyPendingCloudDragFrame() {
  cloudDragAnimationFrame = 0
  const frame = pendingCloudDragFrame
  pendingCloudDragFrame = null
  if (!frame) return

  const drag = activeCloudDrag.value
  if (!drag || drag.pointerId !== frame.pointerId) return

  const deltaX = frame.clientX - drag.startX
  const deltaY = frame.clientY - drag.startY
  if (!drag.active && Math.hypot(deltaX, deltaY) >= CLOUD_DRAG_THRESHOLD) {
    drag.active = true
    draggingCloudKey.value = drag.key
  }

  if (!drag.active) return
  cloudDragOffsets.value = {
    [drag.key]: {
      x: roundCloudMotion(drag.originX + deltaX),
      y: roundCloudMotion(drag.originY + deltaY),
    },
  }
}

function endCloudDrag(event: PointerEvent) {
  finishCloudDrag(event, event.pointerId)
}

function finishCloudDrag(event: PointerEvent, pointerId: number) {
  const drag = activeCloudDrag.value
  if (!drag || drag.pointerId !== pointerId) return
  flushPendingCloudDragFrame()
  const releaseOffsets = drag.active ? captureCloudReleaseOffsets(drag.key) : {}
  detachCloudDragListeners()
  const wasActive = drag.active
  activeCloudDrag.value = null
  draggingCloudKey.value = ''
  releaseCloudPointer(drag, pointerId)
  if (wasActive) {
    startCloudSpringReturn(drag.key, releaseOffsets)
    suppressCloudClick(drag.key)
    return
  }
}

function cancelCloudDrag(event?: PointerEvent) {
  const drag = activeCloudDrag.value
  const releaseOffsets = drag?.active ? captureCloudReleaseOffsets(drag.key) : {}
  detachCloudDragListeners()
  clearPendingCloudDragFrame()
  activeCloudDrag.value = null
  draggingCloudKey.value = ''
  if (drag) releaseCloudPointer(drag, event?.pointerId ?? drag.pointerId)
  if (drag?.active) {
    startCloudSpringReturn(drag.key, releaseOffsets)
  }
}

function handleCloudLostPointerCapture(event: PointerEvent) {
  const drag = activeCloudDrag.value
  if (!drag || drag.pointerId !== event.pointerId) return
  cancelCloudDrag(event)
}

function attachCloudDragListeners() {
  if (cloudDragListenersAttached) return
  window.addEventListener('pointermove', moveCloudDrag)
  window.addEventListener('pointerup', endCloudDrag)
  window.addEventListener('pointercancel', cancelCloudDrag)
  cloudDragListenersAttached = true
}

function detachCloudDragListeners() {
  if (!cloudDragListenersAttached) return
  window.removeEventListener('pointermove', moveCloudDrag)
  window.removeEventListener('pointerup', endCloudDrag)
  window.removeEventListener('pointercancel', cancelCloudDrag)
  cloudDragListenersAttached = false
}

function releaseCloudPointer(drag: CloudDragState, pointerId: number) {
  if (!drag.target?.hasPointerCapture?.(pointerId)) return
  drag.target.releasePointerCapture(pointerId)
}

function flushPendingCloudDragFrame() {
  if (cloudDragAnimationFrame) {
    window.cancelAnimationFrame(cloudDragAnimationFrame)
    cloudDragAnimationFrame = 0
  }
  applyPendingCloudDragFrame()
}

function clearPendingCloudDragFrame() {
  if (cloudDragAnimationFrame) {
    window.cancelAnimationFrame(cloudDragAnimationFrame)
    cloudDragAnimationFrame = 0
  }
  pendingCloudDragFrame = null
}

function captureCloudReleaseOffsets(anchorKey: string) {
  const next: Record<string, CloudDragInfluence> = {}
  const activeOffsets = cloudDragInfluenceOffsets.value
  for (const item of visibleCloudItems.value) {
    const offset = cloudRenderOffset(item.key)
    if (Math.hypot(offset.x, offset.y) < 0.5) continue
    const influence = activeOffsets[item.key]
    const strength = item.key === anchorKey ? 1 : Math.max(0.08, influence?.strength || 0.12)
    next[item.key] = {
      x: offset.x,
      y: offset.y,
      strength,
    }
  }
  return next
}

function startCloudSpringReturn(key: string, offsets: Record<string, CloudDragInfluence>) {
  clearCloudRecoil()
  clearCloudReturn()
  const entries = Object.entries(offsets).filter(([, offset]) => Math.hypot(offset.x, offset.y) >= 0.5)
  if (!entries.length) {
    clearCloudDragOffsets()
    return
  }
  cloudRecoilKey.value = key
  cloudReturnKey.value = key
  cloudSpringEntries = entries
  cloudSpringStartedAt = performanceNow()
  cloudDragOffsets.value = Object.fromEntries(
    entries.map(([entryKey, offset]) => [entryKey, { x: offset.x, y: offset.y }]),
  )
  cloudRecoilOffsets.value = Object.fromEntries(entries)
  cloudSpringAnimationFrame = window.requestAnimationFrame(stepCloudSpringReturn)
}

function stepCloudSpringReturn(now = performanceNow()) {
  cloudSpringAnimationFrame = 0
  if (!cloudSpringEntries.length) {
    finishCloudSpringReturn()
    return
  }
  const elapsedSeconds = Math.max(0, (now - cloudSpringStartedAt) / 1000)
  const multiplier = cloudSpringReturnMultiplier(elapsedSeconds)
  const nextOffsets: Record<string, { x: number; y: number }> = {}
  const nextRecoil: Record<string, CloudDragInfluence> = {}
  let maxDistance = 0

  for (const [entryKey, offset] of cloudSpringEntries) {
    const x = roundCloudMotion(offset.x * multiplier)
    const y = roundCloudMotion(offset.y * multiplier)
    maxDistance = Math.max(maxDistance, Math.hypot(x, y))
    nextOffsets[entryKey] = { x, y }
    nextRecoil[entryKey] = { x, y, strength: offset.strength }
  }

  cloudDragOffsets.value = nextOffsets
  cloudRecoilOffsets.value = nextRecoil

  if (elapsedSeconds >= CLOUD_SPRING_SETTLE_MS / 1000 || maxDistance < 0.35) {
    finishCloudSpringReturn()
    return
  }
  cloudSpringAnimationFrame = window.requestAnimationFrame(stepCloudSpringReturn)
}

function cloudSpringReturnMultiplier(elapsedSeconds: number) {
  const decay = Math.exp(-7.4 * elapsedSeconds)
  return Number((decay * Math.cos(18 * elapsedSeconds)).toFixed(4))
}

function finishCloudSpringReturn() {
  if (cloudSpringAnimationFrame) {
    window.cancelAnimationFrame(cloudSpringAnimationFrame)
    cloudSpringAnimationFrame = 0
  }
  cloudSpringEntries = []
  cloudSpringStartedAt = 0
  clearCloudDragOffsets()
  cloudRecoilOffsets.value = {}
  cloudRecoilKey.value = ''
  cloudReturnKey.value = ''
}

function clearCloudReturn() {
  if (cloudSpringAnimationFrame) {
    window.cancelAnimationFrame(cloudSpringAnimationFrame)
    cloudSpringAnimationFrame = 0
  }
  cloudSpringEntries = []
  cloudSpringStartedAt = 0
  cloudReturnKey.value = ''
}

function clearCloudDragOffsets() {
  cloudDragOffsets.value = {}
}

function clearCloudRecoil() {
  clearCloudReturn()
  cloudRecoilOffsets.value = {}
  cloudRecoilKey.value = ''
}

function evidenceForSourceIds(sourceIds: string[]) {
  return sourceIds
    .map((sourceId) => props.sources.find((source) => source.id === sourceId))
    .filter((source): source is Source => Boolean(source))
    .map((source) => ({ id: source.id, title: source.title }))
}

function pushCloudItem(items: CloudItem[], item: CloudItem) {
  const normalized = normalizeSearchText(item.label)
  const existing = items.find((candidate) => normalizeSearchText(candidate.label) === normalized && candidate.kind === item.kind)
  if (!existing) {
    items.push(item)
    return
  }
  existing.weight = Math.max(existing.weight, item.weight)
  existing.evidenceTitles = mergeEvidence(existing.evidenceTitles, item.evidenceTitles)
  if (!existing.detail.includes(item.detail)) {
    existing.detail = `${existing.detail} ${item.detail}`
  }
}

function mergeEvidence(left: CloudEvidence[], right: CloudEvidence[]) {
  const byId = new Map(left.map((item) => [item.id, item]))
  for (const item of right) byId.set(item.id, item)
  return [...byId.values()].slice(0, 4)
}

function cloudSearchText(item: CloudItem) {
  return normalizeSearchText([
    item.label,
    item.detail,
    item.kindLabel,
    ...item.evidenceTitles.map((source) => source.title),
  ].join(' '))
}

function cloudMatchScore(item: CloudItem, query: string) {
  const label = normalizeSearchText(item.label)
  const detail = cloudSearchText(item)
  if (label === query) return item.weight + 40
  if (label.includes(query)) return item.weight + 24
  if (detail.includes(query)) return item.weight + 12
  return item.weight
}

function normalizeSearchText(value: string) {
  return value.toLowerCase().replace(/\s+/g, ' ').trim()
}

function hashText(value: string) {
  let hash = 0
  for (const char of value) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  }
  return hash.toString(36)
}

function cloudLabel(label: string) {
  const cleaned = label.replace(/\s+/g, ' ').trim()
  return cleaned.length > 36 ? `${cleaned.slice(0, 34)}...` : cleaned
}

function splitHistoryAnswer(answer: string) {
  const cleaned = answer
    .replace(/^#+\s*/gm, '')
    .replace(/```text/g, '')
    .replace(/```/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim()
  if (!cleaned) return ['这条历史问答暂时没有可展示的回答内容。']
  return cleaned
    .split(/(?<=。|！|？|\.|\!|\?)\s+|\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
    .slice(0, 6)
}

function promptSubject(label: string) {
  const cleaned = label.replace(/\s+/g, ' ').trim()
  return cleaned.length > 18 ? `${cleaned.slice(0, 16)}...` : cleaned
}

function cloudNodeClasses(item: CloudItem) {
  return [
    item.tone,
    `cloud-kind-${item.kind}`,
    {
      selected: selectedCloudKey.value === item.key,
      matched: isCloudMatch(item),
      dimmed: !isCloudMatch(item),
      'is-dragging': draggingCloudKey.value === item.key,
      'is-linked': Boolean(cloudDragInfluenceOffsets.value[item.key]),
      'is-recoiling': Boolean(cloudRecoilOffsets.value[item.key]),
      'is-returning': cloudReturnKey.value === item.key,
      'is-large': item.weight >= 6,
      'is-small': item.weight <= 3,
    },
  ]
}

function cloudNodeStyle(item: CloudItem, index: number) {
  const size = Math.max(22, Math.min(30, 17 + item.weight * 1.45))
  const influence = cloudInfluenceOffset(item.key)
  const point = cloudGraphPoint(item, index)
  return {
    '--cloud-x': `${point.x}px`,
    '--cloud-y': `${point.y}px`,
    '--cloud-size': `${size}px`,
    '--cloud-half-size': `${roundCloudMotion(size / 2)}px`,
    '--cloud-link-strength': `${influence.strength}`,
    '--cloud-linked-scale': `${roundCloudMotion(1.01 + influence.strength * 0.06)}`,
    '--cloud-orbit-delay': `${-0.2 * (index % 9)}s`,
  }
}

function sourceToneClass(source: Source) {
  if (source.why_saved_status === 'user-stated') return 'tone-user'
  if (source.why_saved_status === 'AI-inferred') return 'tone-ai'
  return 'tone-source'
}

function sourceBadgeLabel(source: Source) {
  if (source.why_saved_status === 'user-stated') return 'user-stated / 用户原话'
  if (source.why_saved_status === 'AI-inferred') return 'AI-inferred / AI 推断'
  return 'source / 材料'
}

function nodeToneClass(node: GraphNode) {
  if (node.type === 'task') return 'tone-ai'
  if (node.type === 'project' || node.type === 'question') return 'tone-graph'
  return 'tone-source'
}

function sourcePreview(source: Source) {
  const why = cleanOverviewText(source.why_saved)
  if (why) return why
  const summary = cleanOverviewText(source.summary)
  if (summary) return summary
  return '这条材料已经进入知识库，等待之后继续连接。'
}

function keyNodeSummary(node: GraphNode) {
  const source = props.sources.find((item) => item.id === sourceIdForNode(node))
  if (source) return sourcePreview(source)
  const connections = adjacencyCount.value.get(node.id) || 0
  if (node.type === 'task') return connections ? `目前连着 ${connections} 条路径，适合作为下一步整理入口。` : '这是一个待继续处理的开放问题。'
  if (node.type === 'project') return connections ? `目前与 ${connections} 条连接相关，帮助你理解这个空间在围绕什么生长。` : '这个项目节点正在等待更多材料连接过来。'
  if (node.type === 'thought') return connections ? `目前连着 ${connections} 条连接，用来承接已经形成的判断。` : '这个判断节点已经形成，但还需要更多连接支撑。'
  return connections ? `目前连着 ${connections} 条路径。` : '这个节点还在等待更多材料补全。'
}

function cleanOverviewText(text: string) {
  if (!text) return ''
  return text
    .replace(/^AI-inferred:\s*/i, '')
    .replace(/^user-stated:\s*/i, '')
    .replace(/^ai_inferred:\s*/i, '')
    .trim()
}

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function sourceIdForNode(node: GraphNode) {
  const sourceId = node.properties?.source_id
  if (typeof sourceId === 'string' && sourceId) return sourceId
  if (node.id.startsWith('source_')) return node.id.slice('source_'.length)
  return ''
}

function nodeSummary(node: GraphNode) {
  const source = props.sources.find((item) => item.id === sourceIdForNode(node))
  if (source) return source.summary || source.why_saved || '这份材料还没有摘要。'
  const reason = node.properties?.reason
  if (typeof reason === 'string' && reason) return reason
  return '这个节点来自图谱结构，可通过边和相邻材料理解它的位置。'
}

function labelFor(nodeId: string) {
  return props.graph.nodes.find((node) => node.id === nodeId)?.label || nodeId
}

function selectGraphNode(nodeId: string, addToSelection = false) {
  selectedThemeId.value = ''
  selectedEdgeId.value = ''
  if (interactionMode.value === 'connect') {
    if (selectedNodeIds.value.includes(nodeId)) {
      selectedNodeIds.value = selectedNodeIds.value.filter((id) => id !== nodeId)
    } else if (selectedNodeIds.value.length >= 2) {
      selectedNodeIds.value = [selectedNodeIds.value[0], nodeId]
    } else {
      selectedNodeIds.value = [...selectedNodeIds.value, nodeId]
    }
  } else if (interactionMode.value === 'synthesize' || addToSelection) {
    selectedNodeIds.value = selectedNodeIds.value.includes(nodeId)
      ? selectedNodeIds.value.filter((id) => id !== nodeId)
      : [...selectedNodeIds.value, nodeId]
  } else {
    selectedNodeIds.value = [nodeId]
  }
  const node = props.graph.nodes.find((item) => item.id === nodeId)
  const sourceId = node ? sourceIdForNode(node) : ''
  selectedSource.value = sourceId ? props.sources.find((source) => source.id === sourceId) || null : null
}

function selectGraphEdge(edgeId: string) {
  selectedThemeId.value = ''
  selectedNodeIds.value = []
  selectedEdgeId.value = edgeId
  selectedSource.value = null
}

function toggleGraphExpanded() {
  graphExpanded.value = !graphExpanded.value
}

function resetGraphView() {
  graphZoom.value = 1
  graphPan.value = { x: 0, y: 0 }
}

function resetAutoLayout() {
  const next: Record<string, { x: number; y: number }> = {}
  visibleGraphNodes.value.forEach((node, index) => {
    next[node.id] = fallbackPosition(index, Math.max(visibleGraphNodes.value.length, 1), node)
  })
  nodePositions.value = next
  layoutPositions.value = []
  resetGraphView()
}

function graphPointFromEvent(event: PointerEvent | WheelEvent) {
  if (!stageContainer.value) return { x: 500, y: 340 }
  const rect = stageContainer.value.getBoundingClientRect()
  return {
    x: (((event.clientX - rect.left - graphPan.value.x) / graphZoom.value) / Math.max(rect.width, 1)) * 1000,
    y: (((event.clientY - rect.top - graphPan.value.y) / graphZoom.value) / Math.max(rect.height, 1)) * 680,
  }
}

function nodePositionStyle(nodeId: string) {
  const position = nodePositions.value[nodeId] || { x: 500, y: 340 }
  return {
    left: `${(position.x / 1000) * 100}%`,
    top: `${(position.y / 680) * 100}%`,
  }
}

function edgePath(edge: GraphEdge) {
  const source = positionFor(edge.source)
  const target = positionFor(edge.target)
  const dx = target.x - source.x
  const dy = target.y - source.y
  const curve = Math.min(70, Math.max(24, Math.sqrt(dx * dx + dy * dy) * 0.16))
  const cx1 = source.x + dx * 0.34 - dy / curve
  const cy1 = source.y + dy * 0.34 + dx / curve
  const cx2 = source.x + dx * 0.66 - dy / curve
  const cy2 = source.y + dy * 0.66 + dx / curve
  return `M ${source.x} ${source.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${target.x} ${target.y}`
}

function edgeMidpoint(edge: GraphEdge) {
  const source = positionFor(edge.source)
  const target = positionFor(edge.target)
  return {
    x: source.x + (target.x - source.x) * 0.5,
    y: source.y + (target.y - source.y) * 0.5,
  }
}

function positionFor(nodeId: string) {
  return nodePositions.value[nodeId] || { x: 500, y: 340 }
}

function viewId() {
  return `space:${graphSpaceId.value}`
}

function fallbackPosition(index: number, total: number, node: GraphNode) {
  const distance = neighborhoodDistances.value.get(node.id) || 0
  if (distance === 0) {
    return { x: 500, y: 340 }
  }
  const sameDistance = visibleGraphNodes.value.filter((item) => (neighborhoodDistances.value.get(item.id) || 0) === distance)
  const localIndex = Math.max(0, sameDistance.findIndex((item) => item.id === node.id))
  const localTotal = Math.max(1, sameDistance.length)
  const angle = -Math.PI / 2 + (Math.PI * 2 * localIndex) / localTotal + distance * 0.22
  const radiusX = distance === 1 ? 285 : 410
  const radiusY = distance === 1 ? 190 : 270
  return {
    x: clampGraphX(500 + Math.cos(angle) * radiusX),
    y: clampGraphY(355 + Math.sin(angle) * radiusY),
  }
}

function nodeRank(node: GraphNode) {
  const rank: Record<string, number> = {
    source: 0,
    thought: 1,
    project: 2,
    task: 3,
  }
  return rank[node.type] ?? 9
}

function startNodeDrag(event: PointerEvent, nodeId: string) {
  if (interactionMode.value !== 'arrange') return
  pendingDragNodeId.value = nodeId
  pendingDragAddToSelection.value = event.shiftKey
  pendingDragStart.value = { x: event.clientX, y: event.clientY }
  const point = graphPointFromEvent(event)
  const current = nodePositions.value[nodeId] || { x: 500, y: 340 }
  nodeDragOffset.value = {
    x: current.x - point.x,
    y: current.y - point.y,
  }
  window.addEventListener('pointermove', dragNode)
  window.addEventListener('pointerup', stopNodeDrag, { once: true })
}

function dragNode(event: PointerEvent) {
  if (!draggingNodeId.value) {
    if (!pendingDragNodeId.value) return
    const moved = Math.hypot(event.clientX - pendingDragStart.value.x, event.clientY - pendingDragStart.value.y)
    if (moved < 5) return
    draggingNodeId.value = pendingDragNodeId.value
    selectGraphNode(draggingNodeId.value, pendingDragAddToSelection.value)
  }
  const point = graphPointFromEvent(event)
  nodePositions.value = {
    ...nodePositions.value,
    [draggingNodeId.value]: {
      x: clampGraphX(point.x + nodeDragOffset.value.x),
      y: clampGraphY(point.y + nodeDragOffset.value.y),
    },
  }
}

function stopNodeDrag() {
  draggingNodeId.value = ''
  pendingDragNodeId.value = ''
  pendingDragAddToSelection.value = false
  nodeDragOffset.value = { x: 0, y: 0 }
  window.removeEventListener('pointermove', dragNode)
}

function startGraphPan(event: PointerEvent) {
  const target = event.target as HTMLElement | null
  if (
    event.button !== 0 ||
    interactionMode.value !== 'arrange' ||
    target?.closest('.paper-graph-node, .graph-edge-hit, button, .graph-stage-caption')
  ) {
    return
  }
  panningGraph.value = true
  lastPanPoint.value = { x: event.clientX, y: event.clientY }
  window.addEventListener('pointermove', panGraph)
  window.addEventListener('pointerup', stopGraphPan, { once: true })
}

function panGraph(event: PointerEvent) {
  if (!panningGraph.value) return
  const dx = event.clientX - lastPanPoint.value.x
  const dy = event.clientY - lastPanPoint.value.y
  graphPan.value = {
    x: graphPan.value.x + dx,
    y: graphPan.value.y + dy,
  }
  lastPanPoint.value = { x: event.clientX, y: event.clientY }
}

function stopGraphPan() {
  panningGraph.value = false
  window.removeEventListener('pointermove', panGraph)
}

function zoomGraph(event: WheelEvent) {
  if (!stageContainer.value) return
  const rect = stageContainer.value.getBoundingClientRect()
  const oldZoom = graphZoom.value
  const nextZoom = Math.min(1.9, Math.max(0.68, oldZoom * (event.deltaY > 0 ? 0.9 : 1.1)))
  const pointerX = event.clientX - rect.left
  const pointerY = event.clientY - rect.top
  graphPan.value = {
    x: pointerX - ((pointerX - graphPan.value.x) * nextZoom) / oldZoom,
    y: pointerY - ((pointerY - graphPan.value.y) * nextZoom) / oldZoom,
  }
  graphZoom.value = nextZoom
}

function clampGraphX(value: number) {
  return Math.min(940, Math.max(60, Number.isFinite(value) ? value : 500))
}

function clampGraphY(value: number) {
  return Math.min(620, Math.max(58, Number.isFinite(value) ? value : 340))
}

function shortLabel(label: string) {
  const cleaned = label.replace(/\s+/g, ' ').trim()
  return cleaned.length > 52 ? `${cleaned.slice(0, 50)}...` : cleaned
}

function nodeMapLabel(node: GraphNode) {
  const source = node.type === 'source' ? props.sources.find((item) => item.id === sourceIdForNode(node)) : null
  const cleaned = (source?.title || node.label).replace(/\s+/g, ' ').trim()
  return cleaned.length > 30 ? `${cleaned.slice(0, 28)}...` : cleaned
}

function nodeTypeLabel(type: string) {
  const labels: Record<string, string> = {
    source: '材料',
    thought: '想法',
    project: '项目',
    task: '未闭环',
    question: '问题',
  }
  return labels[type] || type
}

function originLabel(origin: string) {
  const value = origin.toLowerCase()
  if (value.includes('user')) return '用户确认'
  if (value.includes('ai')) return 'AI 推断'
  if (value.includes('system')) return '系统生成'
  return origin || '未标注'
}

function graphStatusLabel(status: string) {
  const labels: Record<string, string> = {
    active: '有效',
    confirmed: '已确认',
    proposed: '待确认',
    rejected: '已拒绝',
    weakened: '已削弱',
    hidden: '已隐藏',
  }
  return labels[status] || status || '未标注'
}

function relationLabel(relation: string) {
  const labels: Record<string, string> = {
    related_to: '相关',
    evidence_for: '证明',
    triggered_thought: '触发想法',
    supports: '支持',
    follow_up: '后续问题',
    belongs_to: '属于',
  }
  return labels[relation] || relation
}

function confidenceLabel(confidence?: number) {
  if (typeof confidence !== 'number' || Number.isNaN(confidence)) return '未标注'
  return `${Math.round(confidence * 100)}%`
}

function sourceToneLabel(source: Source | null) {
  if (!source) return '未关联材料'
  if (source.why_saved_status === 'user-stated') return '用户原话'
  if (source.why_saved_status === 'AI-inferred') return 'AI 推断'
  return '材料线索'
}

function edgeClasses(edge: GraphEdge) {
  const classes = [`status-${edge.status || 'confirmed'}`]
  if (edge.origin === 'user') classes.push('origin-user')
  if (viewMode.value === 'evidence' && ['evidence_for', 'triggered_thought', 'supports'].includes(edge.relation)) {
    classes.push('mode-emphasis')
  }
  if (viewMode.value === 'action' && ['follow_up'].includes(edge.relation)) {
    classes.push('mode-emphasis')
  }
  return classes.join(' ')
}

function graphStyle() {
  return [
    {
      selector: 'node',
      style: {
        label: 'data(label)',
        'background-color': '#fffefd',
        'border-width': 1,
        'border-color': 'rgba(77, 61, 42, 0.22)',
        color: '#1c1b19',
        'font-size': 13,
        'font-family': 'Inter, -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif',
        'text-wrap': 'wrap',
        'text-max-width': 142,
        shape: 'round-rectangle',
        width: 136,
        height: 42,
        padding: '8px',
      },
    },
    { selector: '.node-source', style: { 'border-color': '#b0501e', color: '#b0501e' } },
    { selector: '.node-thought', style: { 'border-color': '#356f5c', color: '#356f5c' } },
    { selector: '.node-task', style: { 'border-color': '#8b5631', color: '#8b5631' } },
    {
      selector: 'edge',
      style: {
        label: 'data(label)',
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle',
        width: 1.25,
        'line-color': 'rgba(77, 61, 42, 0.28)',
        'target-arrow-color': 'rgba(77, 61, 42, 0.28)',
        color: '#85796d',
        'font-size': 10,
        'text-background-color': '#fbfaf7',
        'text-background-opacity': 0.82,
        'text-background-padding': '3px',
      },
    },
    { selector: '.origin-user', style: { 'line-color': '#356f5c', 'target-arrow-color': '#356f5c', width: 2 } },
    { selector: '.mode-emphasis', style: { 'line-color': '#b0501e', 'target-arrow-color': '#b0501e', width: 2.4 } },
    { selector: '.status-proposed', style: { 'line-style': 'dashed' } },
    { selector: '.status-weakened', style: { opacity: 0.56, 'line-style': 'dashed' } },
    { selector: '.status-rejected', style: { opacity: 0.32, 'line-style': 'dotted' } },
    { selector: ':selected', style: { 'border-width': 3, 'border-color': '#1c1816', 'line-color': '#1c1816', 'target-arrow-color': '#1c1816' } },
  ]
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(path, { ...options, headers })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = await response.json()
      detail = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail || payload)
    } catch {
      detail = await response.text()
    }
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return response.json()
}

function messageFromError(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}
</script>
