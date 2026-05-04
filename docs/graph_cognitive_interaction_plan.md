# SnapGraph 图谱认知交互改造方案

## 目标
SnapGraph 图谱不应只是点线展示，而应成为“认知操作界面”：
- 看图：恢复判断；
- 点击：查看证据；
- 拖动：表达关系；
- 框选：生成归纳；
- 筛选：审计信任；
- 右键：发起下一步行动。

核心目标：让图谱交互写回为可审计、可追溯的认知信号。

## 当前问题
### 图谱不知道怎么读
- 用户不知道每个点是什么；
- 用户不知道区域代表项目、主题、证据链还是临时聚类；
- 用户不知道哪些内容是自己保存的；
- 用户不知道哪些内容是 AI 推断的；
- 用户看完图谱后不知道下一步该做什么。

### 拖动没有产品意义
- 当前拖动只改变位置；
- 拖近不代表建立关联；
- 拖远不代表弱化关系；
- 拖入区域不代表归类；
- 框选节点不会产生新的判断。

本质问题：交互动作没有进入 SnapGraph 的记忆系统。

## 设计原则
1. 图谱必须服务“恢复判断”，不是服务视觉炫技。
2. `user-stated`、`AI-inferred`、`proposed`、`confirmed` 必须清晰区分。
3. 坐标属于视图状态，不应污染核心 `graph.json` 事实层。
4. AI 建议默认是 proposed，用户确认后才变 confirmed。
5. 拖动必须有明确模式，避免隐式写回。

## 三种视图
### Memory Map
查看材料、项目、主题的整体分布。
- 展示 source、thought、project、theme、graph space；
- 区分 confirmed / proposed 关系；
- 帮用户发现 inbox、孤岛节点和主题分布。

### Evidence Path
解释一个回答或判断为什么可信。
- 展示命中的 source、thought、graph path；
- 展示 user-stated 与 AI-inferred 的比例；
- 暴露低置信度或证据不足的关系。

### Action Map
告诉用户下一步该做什么。
- 展示 task、question、open loop；
- 展示 low confidence、orphan node、pending suggestion。

## 节点与边
节点展示应从技术类型改为认知角色：
- `source`：原文；
- `thought`：判断；
- `task`：待办；
- `question`：问题；
- `project`：项目；
- `theme`：主题。

每个节点应说明：这是什么、来自用户还是 AI、属于哪个 space、摘要是什么、保存原因是什么、下一步可以做什么。

每条边应说明：关系类型、为什么存在、证据来源、置信度、当前状态。

建议边状态：
- confirmed；
- proposed；
- rejected；
- weakened；
- hidden。

## 关键交互
### Hover
悬浮节点或边时显示预览卡片：标题、类型、来源状态、摘要、why_saved、置信度、下一步动作。

### Click
点击节点后，右侧 inspector 展示详情，并允许打开 Markdown 原文。
点击边后，展示关系解释、证据来源、置信度，并允许确认、拒绝或弱化。

### Right Click
第一阶段只保留高价值动作：
- Ask from here；
- Open source；
- Connect to...；
- Hide from this view；
- Mark not related。

### Arrange
整理布局：
- 拖动节点后保存坐标；
- 不自动建立关系；
- 支持重置自动布局；
- 坐标写入 layout 数据，不写入节点事实。

### Connect
通过拖近表达关联：
- 用户把节点 A 拖近节点 B；
- 系统提示是否建立关系；
- 用户选择 relation；
- 用户输入原因；
- 系统写入 confirmed 边。

### Synthesize
框选多个节点生成新的判断：
- 用户框选节点；
- 输入“为什么把它们放在一起”；
- 系统创建新的 thought 节点；
- 被选节点连向该 thought；
- thought 标记为 user-stated。

### Prune
清理错误关系：
- 隐藏当前视图中的节点；
- 拒绝 proposed edge；
- 弱化 confirmed edge；
- 记录用户反馈原因。

## 数据层改造
新增 `graph_layouts`：
- 保存 `view_id`、`graph_space_id`、`node_id`、`x`、`y`、`locked`。

新增 `graph_feedback`：
- 保存 connect / reject / weaken / hide / categorize / synthesize 等用户反馈。

新增 `graph_themes`：
- 保存主题 label、成员节点、origin、status、confidence、reason。

节点和边可先通过 `properties` 扩展：
- 节点：trust_status、summary、confidence、origin；
- 边：evidence_kind、explanation、origin、rejected_reason、weakened_reason。

## API 改造
优先新增：
- `PATCH /api/graph/layout`：保存节点坐标；
- `GET /api/graph/layout`：读取节点坐标；
- `POST /api/graph/edges`：用户确认建立关系；
- `PATCH /api/graph/edges/{edge_id}`：确认、拒绝、弱化关系；
- `POST /api/graph/thoughts`：框选节点后生成 thought；
- `POST /api/graph/themes`：创建主题；
- `PATCH /api/graph/themes/{theme_id}`：确认、改名、拒绝主题。

## 前端改造
当前前端使用 Cytoscape，建议继续复用。
- 视图切换：Memory Map / Evidence Path / Action Map；
- 模式切换：Arrange / Connect / Synthesize / Prune；
- 信任筛选：User-stated / AI-inferred / Confirmed / Proposed / Low confidence；
- Hover 预览卡片；
- Inspector 详情解释；
- drag end 保存布局；
- Connect 模式下拖近建边；
- Synthesize 模式下框选生成 thought；
- 右键菜单。

## 实施顺序
### Phase 1：让图谱读得懂
- Hover 卡片；
- Click inspector；
- Markdown 原文入口；
- trust status 筛选器；
- 边的证据和置信度解释。

### Phase 2：让拖动有记忆
- 新增 layout 数据；
- drag end 保存坐标；
- 刷新后恢复布局；
- 支持 reset layout。

### Phase 3：拖近可建关系
- 新增手动建边 API；
- Connect 模式检测近邻节点；
- 用户确认 relation 和 reason；
- 新边写入 `graph.json` 和 SQLite。

### Phase 4：框选可生成判断
- Synthesize 模式；
- 框选多个节点；
- 输入归纳原因；
- 创建 user-stated thought；
- 被选节点连向新 thought。

### Phase 5：主题边界和 Action Map
- 支持 graph themes；
- 展示主题圈或 compound node；
- Action Map 展示 open loops、tasks、questions、pending suggestions；
- 支持确认、改名、拒绝主题。

## 最小可交付版本
- 节点看得懂；
- 边说得清；
- 拖动能保存；
- 拖近能建关系；
- 框选能生成判断；
- 点击能回到 Markdown 证据。

## 第一阶段不做
- 不做 3D 图谱；
- 不引入 Neo4j；
- 不做复杂 agent framework；
- 不自动把 AI 聚类写成 confirmed；
- 不让拖近自动建边；
- 不把 layout 坐标写进 `graph.json` 节点字段；
- 不直接修改向量相似度。

## 结论
SnapGraph 图谱改造的关键不是“更漂亮”，而是“更可解释、更可操作、更可写回”。
只有当点击、拖动、框选、筛选都能变成明确的认知动作时，图谱才真正成为 SnapGraph 的核心产品能力。
