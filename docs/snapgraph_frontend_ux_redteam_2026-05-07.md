# SnapGraph Frontend UX Red-Team Report

Last updated: 2026-05-07

Purpose: this is the durable frontend and interaction-design critique document for SnapGraph. Read it before redesigning the Vue frontend, producing new UI mockups, or re-running broad UX review in a new Codex window.

Depth update: after this checklist-style red-team report, read `docs/snapgraph_user_truth_frontend_v2_2026-05-07.md`. The V2 document goes deeper on target user choice, true competitors, bottom-layer needs, and one critical product correction: AI must not silently infer the user's saving reason.

Do not store real API keys in this document. Live provider checks should use `SNAPGRAPH_LLM_API_KEY` from the local shell or keychain only.

## Method

This review used multiple subagents plus direct source inspection.

Subagent roles:

- `Fermat`: simulated user research and demand mining across students, researchers, PMs, founders, designers, knowledge workers, teams, heavy collectors, AI-heavy users, privacy-sensitive users, and new users.
- `Einstein`: frontend and interaction red-team review against the current Vue production frontend and current visual direction.
- `Volta`: information architecture review focused on how backend graph data should be translated into user-facing evidence and action surfaces.

Local artifacts inspected:

- `AGENTS.md`
- `README.md`
- `docs/snapgraph_live_evaluation_progress.md`
- `docs/snapgraph_competition_design_brief.md`
- `docs/api_contract.md`
- `docs/workspace_schema.md`
- `demo/snapgraph-ui-concept/DESIGN_NOTES.md`
- `demo/snapgraph-ui-concept/screenshot-desktop.png`
- `demo/snapgraph-ui-concept/screenshot-mobile.png`
- `frontend/src/App.vue`
- `frontend/src/components/RecallHome.vue`
- `frontend/src/components/RecallResult.vue`
- `frontend/src/components/CollectView.vue`
- `frontend/src/components/SpacesView.vue`
- `frontend/src/components/GraphSpaceView.vue`
- `frontend/src/styles.css`

## One-Sentence Verdict

SnapGraph has a strong product soul, but the current frontend still exposes too much graph machinery; the interface must make the user feel, immediately and repeatedly, that it helps them recover a past judgment with trustworthy evidence, not manage nodes, edges, layouts, providers, or database objects.

## Product Principle

Users do not want to see a graph first. They want to ask, "What did I think, why did I think it, what evidence supported it, what is uncertain, and what should I do next?"

Every backend object should be translated:

- `source` becomes a material card with type, excerpt, import status, and original source.
- `why_saved` becomes the highest-trust memory clue.
- `AI-inferred` becomes a reviewable suggestion, never a hidden fact.
- `edge` becomes a natural-language relationship that can be confirmed, edited, weakened, rejected, or deferred.
- `graph_path` becomes an evidence path card with claim, steps, strongest evidence, weakest link, and source excerpts.
- `open_loop` becomes an actionable queue item with lifecycle.
- `space` becomes a project/question workspace, not a graph canvas.

## Core Mismatch

What users need:

- Recover a half-remembered judgment.
- See what they themselves wrote at save time.
- Check a small number of supporting sources.
- Know whether the system is guessing.
- Continue work from open loops and review queues.
- Trust that no private data or AI guess is being smuggled into certainty.

What the current UI still shows too early:

- 图谱, 节点, 边, 专业模式, Inspector, Confidence, Origin, Type, layout save, manual edge operations, raw route suggestions, provider/model pills, workspace path.

The product should keep graph power, but default to evidence-first memory.

## User Demand Inventory

The following needs are specific enough to become product requirements or interaction tests.

| ID | Demand | Trigger Scenario | Why It Matters | Current Gap / Verification Point |
|---|---|---|---|---|
| N01 | 保存时必须追问“为什么值得留下” | 用户拖入论文、截图、网页或 AI 对话 | 这是未来召回最可信的线索 | 需要验证用户不填时长期召回质量下降多少 |
| N02 | 允许跳过 why，但生成“待补理由”状态 | 快速收藏时来不及写 | 降低保存摩擦，同时不伪造动机 | 需要补写提醒和队列 |
| N03 | 用户保存理由必须原文保留，不被 AI 改写 | 用户写下主观判断 | 保护真实意图和审计性 | UI 需全程突出 `user-stated` |
| N04 | AI 推断理由必须默认标为 AI-inferred | 用户未写 why | 避免 AI 冒充用户记忆 | 标签需要贯穿 Collect、Recall、Space、Review |
| N05 | 每次保存后生成 Memory Receipt | Ingest 完成后 | 给用户保存闭环和信任反馈 | 当前有雏形，但字段和操作不足 |
| N06 | 批量上传显示每个文件独立状态 | 一次导入 30 到 100 个文件 | 避免长时间黑箱等待 | 当前真实 provider 批量慢，缺异步队列 |
| N07 | 批量导入允许失败文件重试 | PDF、图片、网页部分失败 | 不让整批任务报废 | 需要文件级失败原因和重试 |
| N08 | 导入后显示解析质量 | 扫描 PDF、截图、网页导出 | 用户要知道系统到底读懂了多少 | 缺 `text_extracted`、`visual_extracted`、`warnings` |
| N09 | 召回支持材料类型过滤 | 用户问“只看截图证据” | 避免文本材料污染视觉问题 | 需要 PDF、image、web、text filter |
| N10 | 无证据问题必须返回“没有可靠证据” | 用户问无关问题 | 防止假记忆和无关召回 | 当前 no-match retrieval 是高风险 |
| N11 | 召回答案先给直接结论，再给证据 | PM、研究者快速复盘 | 降低阅读成本 | 当前答案卡有基础，需优化首屏 |
| N12 | 证据卡必须显示来源摘录 | 用户核验答案 | 只给标题不够可信 | 需覆盖 PDF、图片 OCR、网页、Markdown |
| N13 | 证据卡区分用户原话、材料内容、AI 推断、图谱路径 | 所有召回 | 建立信任边界 | 当前分区存在，但排序和操作不够清楚 |
| N14 | 图谱路径要变成可读 evidence path cards | 非技术用户看 supports/triggered_thought | 降低理解门槛 | 当前仍有 raw path string |
| N15 | AI 推断默认折叠，但可审查 | 严谨或隐私敏感用户 | 不让推断压过事实 | 需要确认、修改、不相关操作 |
| N16 | 召回时显示“用了几条用户原话” | 用户判断可信度 | 用户原话越多越可信 | 当前 chip 可进一步产品化 |
| N17 | 低证据答案要给下一步建议 | 系统证据不足 | 用户需要知道如何修复记忆库 | 需要导入、补 why、换问法建议 |
| N18 | 允许把高价值回答保存回 wiki | 阶段性结论形成 | 回答本身成为未来材料 | UI 缺明显入口 |
| N19 | 召回问题不应默认保存为 source | 用户只是找记忆 | 避免污染知识库 | 需确认实现和 UI 语义 |
| N20 | 提供模糊回忆提问模板 | 新手不知道怎么问 | 降低启动成本 | 当前示例过窄，需跨场景 |
| N21 | 空间不应成为保存前负担 | 用户保存时还不知道分类 | 先收集，再显结构 | 当前 auto/inbox/manual 方向正确 |
| N22 | Inbox 要有集中整理队列 | 重度收藏者大量低置信材料 | 避免未分类沉没 | 需要更显著入口 |
| N23 | 空间首页显示“正在追踪什么问题” | 进入项目空间 | 空间是问题场，不是文件夹 | 当前 overviewSummary 方向对 |
| N24 | 空间按 open loop 聚合材料 | 科研、产品复盘 | 下一步行动比节点数更重要 | open_loop_hotspots 需产品化 |
| N25 | Open loop 需要生命周期 | 长期项目推进 | 避免问题永久堆积 | 缺 `new/confirmed/deferred/done` |
| N26 | 移动材料空间时记录用户原因 | 用户纠正 AI 路由 | 未来审计需要知道谁改的 | 当前 move reason 过泛 |
| N27 | AI 路由建议可接受、忽略并说明原因 | 系统建议放错空间 | 提高图谱质量 | 当前 accept/reject 缺用户理由 |
| N28 | 新建空间围绕“追什么问题” | 新项目建立 | 防止空间变成静态分类 | 当前字段存在，需强化文案 |
| N29 | 空间显示近期材料时间线 | 跨周回来继续工作 | 帮用户恢复上下文 | 当前最近材料需要更强摘要 |
| N30 | 空间显示低置信待审 | 严谨用户维护质量 | 把不确定变成工作流 | insights 有字段，UI 入口不足 |
| N31 | 学生需要“文献为何相关”卡片 | 写综述、开题、竞赛 | 文献管理器不保存判断来路 | 需验证 PDF 到论点链路 |
| N32 | 科研者需要方法、数据、结论维度抽取 | 读论文 | 便于比较和复用 | 当前摘要通用，缺结构化字段 |
| N33 | PM 需要“截图支持哪个需求判断” | 竞品截图复盘 | 图片 OCR 只是第一步 | 需把图像理解绑定 why 和 claim |
| N34 | 创业者/投资分析需要 thesis 变化记录 | 保存市场信号后观点变化 | 投资判断需要版本轨迹 | log 有基础，缺用户可读视图 |
| N35 | 设计师需要保存感觉和风格触发点 | 收藏视觉素材 | 灵感不是事实摘要 | why 和 AI 字段需支持主观语言 |
| N36 | 创作者需要从素材找回 mood/主题 | 准备文章或视频 | 关键词不稳定 | 需验证审美语言的模糊召回 |
| N37 | 知识工作者需要跨项目桥接提示 | 多项目共享旧材料 | 旧材料可能复用 | bridge_sources 需要谨慎提示 |
| N38 | 团队需要显示保存者和确认者 | 多人共享材料 | 区分个人判断和团队共识 | 当前模型偏个人 |
| N39 | 团队需要评论和确认 AI 推断 | 共享知识库 | 防止错误推断传播 | 需要权限和审计流 |
| N40 | 重度收藏者需要重复材料检测 | 多次保存同一链接或截图 | 减少噪声 | UI 需反馈重复和合并 |
| N41 | AI 深度用户需要导入 AI 对话并提取结论和 open loops | 大量 ChatGPT/Qwen 对话 | 对话更像思考现场 | 需解析对话结构 |
| N42 | AI 深度用户需要区分“AI 说的”和“我认同的” | 保存 AI 回答 | AI 输出不能自动成为用户判断 | 需要显式确认交互 |
| N43 | 自动生成 future recall questions | 用户不知道未来怎么搜 | 把材料变成可回忆线索 | 字段存在，UI 展示不足 |
| N44 | 一键从材料生成追问 | 看到证据卡后 | 顺着判断继续探索 | askFromGraph 应在更多位置出现 |
| N45 | “今天该继续处理什么”视图 | 项目恢复日 | open loop 变行动队列 | 当前还不够突出 |
| N46 | 按时间回到某天思考现场 | 竞赛、论文、产品周期 | 判断依赖当时上下文 | log 是技术资产，缺时间线体验 |
| N47 | 原始文件可信状态要简化展示 | 可信和审计用户 | 不暴露 hash，也要说明来源未改 | 需要“原始来源已保留”状态 |
| N48 | 用户要知道哪些内容会发给模型 | 隐私敏感场景 | 避免误传商业或个人资料 | 设置缺发送范围说明 |
| N49 | 本地模式和真实模型模式清楚切换 | 新手、隐私用户 | Mock 与 Qwen 行为差异大 | Provider 设置需产品化 |
| N50 | 明确 API key 不入库 | 配置 provider | 建立信任 | UI 可加强安全说明 |
| N51 | 新手默认从找回或收集开始，不从图谱开始 | 第一次打开 | 图谱门槛高 | 当前 Recall 默认对有数据用户好，空库需切换 |
| N52 | 示例数据一键体验完整流程 | 未导入材料时 | 先体验价值再配置 | 当前加载 demo 藏在设置 |
| N53 | 空状态必须告诉下一步 | 没材料、没结果 | 避免不知道做什么 | 空状态需带动作按钮 |
| N54 | 错误信息用用户语言 | 缺 key、不支持格式、解析失败 | 降低挫败 | CLI/UI 都需避免 traceback |
| N55 | 诊断报告需要产品化翻译 | lint/report/eval 结果 | 用户知道记忆库健康度 | diagnostics 偏工程 |
| N56 | 检索诊断解释为什么找这些材料 | 用户怀疑答案 | 帮助校准信任 | UI 需要解释理由 |
| N57 | 材料级隐私标记 | 日记、商业资料 | 控制是否参与 AI 或跨空间连接 | 当前未见显式控制 |
| N58 | 手动削弱/拒绝错误连接并记录原因 | 图谱连错边 | 长期信任取决于可纠错 | Prune 有雏形，门槛高 |
| N59 | 多材料归纳成用户判断必须由用户确认 | 观点形成 | 防止 AI 替用户下结论 | Synthesize 需 user-confirmed 状态 |
| N60 | 产品主叙事聚焦证据和判断，不主打节点边数量 | 所有目标用户 | 用户买的是找回判断 | UI 仍需降级 graph mechanics |

## Frontend And Interaction Problem Inventory

These problems are written from a user-friction perspective. They should be used as red-team acceptance criteria for redesign.

| ID | Problem | Why Users Fail Or Feel Friction | Impact | Recommended Direction |
|---|---|---|---|---|
| P01 | 首屏价值句仍偏抽象 | 用户不确定适合保存什么、问什么 | 上手犹豫 | 增加首个任务入口：上传材料或问旧判断 |
| P02 | 缺一级“审计/确认”入口 | AI 推断没有责任闭环 | 信任不足 | 待确认建议、低置信推断、开放问题做显著入口 |
| P03 | 空库默认仍是找回 | 新用户没有材料可找 | 第一次体验空转 | 空库默认引导收集或加载 demo |
| P04 | Provider pill 暴露 mock/Qwen/model | 普通用户不理解 | 像开发控制台 | 改为“本地模式/真实模型已连接” |
| P05 | 设置暴露 Workspace 路径 | 工程细节过多 | 产品完成度下降 | 默认隐藏，放高级诊断 |
| P06 | 加载演示数据藏在设置里 | 新用户找不到体验入口 | demo 启动失败 | 空状态直接提供“加载示例记忆” |
| P07 | 提示“按回车找回”但 textarea 回车换行 | 操作暗示不一致 | 用户困惑 | 支持 Enter 提交或改为 Cmd/Ctrl+Enter |
| P08 | 示例问题绑定 SnapGraph 自身 | 外部用户看不懂 | 迁移性差 | 提供论文、产品、会议、设计、投资等示例 |
| P09 | 找回页缺语料范围感 | 不知道查哪些材料 | 结果不可预期 | 显示空间、材料数、范围 filter |
| P10 | 从空间追问仍查 all | 空间上下文丢失 | 回答偏离当前项目 | 保留当前空间过滤器 |
| P11 | 全局 busy 锁住太多操作 | 上传时不能查看已有内容 | 体验笨重 | 改成任务级状态 |
| P12 | `/api/focus` 失败仍可能继续生成 | 用户可能收到无证据回答 | 信任边界受损 | 证据失败时明确降级或停止生成 |
| P13 | 流式 partial result 像完整结果 | 用户误以为证据已确认 | 阶段感混乱 | 流式区和最终答案视觉区分 |
| P14 | “这是我的回答”主体含混 | 不知道我的指用户还是 AI | 信任主体混乱 | 改为“基于你保存材料的回答” |
| P15 | 低证据时答案仍先于证据 | 用户先读结论 | 幻觉风险上升 | 低证据时证据摘要优先 |
| P16 | no-match 文案不够坚定 | 用户继续乱问 | 错误自信 | 显示“没有找到可靠本地证据” |
| P17 | 证据摘要只给数量 | 无法判断质量 | 信任校准不足 | 加“用户原话优先/AI 仅辅助/证据不足” |
| P18 | `why_saved_status !== user-stated` 都进 AI 推断 | unknown/source 被误标 | 标签误导 | 区分 user-stated、AI-inferred、source-only、unknown |
| P19 | 证据链和相关材料重复 | 读两遍相似内容 | 页面冗长 | 合并为统一证据卡列表 |
| P20 | 图谱路径 raw string 展示 | 用户看不懂路径含义 | 证据链价值打折 | 改成路径卡 |
| P21 | 展开材料没有完整原始来源入口 | 无法核验 raw source | traceability 不完整 | 提供打开原文、文件名、导入时间 |
| P22 | 材料卡缺 material type | 不知证据来自 PDF/图/网页 | 可信度难判断 | 每卡显示类型和提取方式 |
| P23 | 缺 extraction warnings | OCR/PDF 失败被静默吞掉 | 用户过度相信摘要 | 回执和证据卡显示解析警告 |
| P24 | 保存答案回 wiki 入口缺失 | 高价值回答无法沉淀 | 工作流断裂 | 给“保存这次回答为记忆” |
| P25 | Collect CTA 叫“放进图谱” | 用户以为管理结构 | 心智偏离 | 改为“保存为记忆”或“生成记忆回执” |
| P26 | why 可选但提示不够强 | 核心信息容易缺失 | 长期召回变差 | 空 why 时回执要求补一句 |
| P27 | why 输入缺具体例子 | 用户不知道写什么 | 理由质量差 | 提供模板式 placeholder |
| P28 | 上传进度是模拟步骤 | 真实 Qwen 慢时不可信 | 等待焦虑 | 绑定真实阶段和每文件状态 |
| P29 | 批量上传串行整体 busy | 100 文件像卡死 | 长任务失败 | 后台队列、并发限制、可离开页面 |
| P30 | 上传失败只 toast 一个错误 | 不知道哪份失败 | 无法修复 | 每文件结果显示成功/失败/原因 |
| P31 | 文件 pill 只显示文件名 | 看不到大小、类型、重复 | 容易误传 | 加大小、类型、单项移除、重复提示 |
| P32 | 拖拽区不像 dropzone | 用户不知道可拖文件 | 发现性弱 | 明确 dropzone 视觉和拖入状态 |
| P33 | 前端 accept 与文档支持不完全一致 | 用户预期和实际不一致 | 导入失败挫败 | 前后端格式列表统一 |
| P34 | 回执建议连接只是 chip | 无法接受/拒绝 | 审查断掉 | 每条连接带确认、忽略、稍后 |
| P35 | 系统理解不可编辑 | 摘要错了不能修 | 错误进入长期记忆 | 回执允许编辑标题、摘要、why、空间 |
| P36 | 继续收集后回执消失 | 不知道刚才保存到哪 | 闭环弱 | 保留最近回执列表 |
| P37 | “AI 自动放入”没说明低置信处理 | 担心被乱放 | 路由不可信 | 显示规则：低置信进 Inbox |
| P38 | 手动空间默认 default | 容易误归类 | 空间质量下降 | 默认“请选择”，展示空间用途 |
| P39 | Spaces 首页操作目标弱 | 不知道能做什么 | 信息架构含糊 | 顶部给查看开放问题、确认建议、浏览材料 |
| P40 | 空间卡显示节点数 | 用户不懂节点价值 | 指标机械 | 换成材料、用户原话、待确认、未闭环 |
| P41 | 新建空间表单常驻底部 | 干扰浏览 | 像后台管理 | 折叠或弹窗 |
| P42 | “专业模式”太早出现 | 诱导进入复杂界面 | 新手负担 | 改成“高级审计”并弱化 |
| P43 | “找回这个空间里的判断”固定问句 | 用户不知道会问什么 | 结果不符合意图 | 先填入问题，等待用户确认 |
| P44 | “整理开放问题”直接进 action map | 动作跨度过大 | 用户掉进复杂工具 | 独立开放问题队列 |
| P45 | Workbench 混用英文模式名 | 中文界面中断 | 认知成本增加 | 统一中文 |
| P46 | Inspector 用 Type/Status/Origin/Confidence | 内部对象感强 | 用户不愿碰 | 翻译成类型、状态、来源、可信度 |
| P47 | Confidence 显示百分比 | 伪精确导致过信 | 信任校准失败 | 用高/中/低加原因 |
| P48 | 边状态暴露 raw enum | 普通用户难懂 | 审查门槛高 | 翻译为确认有效、待确认、证据较弱、不成立、隐藏 |
| P49 | 手动连边要求写 relation 词 | 用户不会写 supports 等 | 创建失败 | 关系菜单加自然语言说明 |
| P50 | 削弱/拒绝边依赖点细线 | 很难选边 | 审查任务失败 | 给边列表审查视图 |
| P51 | 图谱节点标题难辨认 | 复杂材料看不清 | 图谱可读性差 | 默认用路径卡或泳道 |
| P52 | 画布只显示 anchor 附近 14 个节点 | 用户不知道有隐藏节点 | 误以为图不完整 | 显示当前 14/N 和扩大范围 |
| P53 | 平移缩放缺可见控件 | 触控板和移动端难用 | 探索受阻 | 加缩放按钮和重置视图 |
| P54 | 移动端底部导航可能遮内容 | 表单 CTA/toast 被挡 | 移动失败 | 加 safe area 和 sticky 避让 |
| P55 | 移动首屏过密 | 大标题、chips、卡片拥挤 | 高级感下降 | 移动端保留一个主任务 |
| P56 | 移动端 workbench 流程太长 | 画布、材料、Inspector 分散 | 无法操作 | 移动隐藏画布编辑，保留概览和审查队列 |
| P57 | focus 样式不足 | 键盘用户难定位 | 无障碍不足 | 给 `:focus-visible` |
| P58 | SVG 边不可键盘聚焦 | 读屏难发现边操作 | 无障碍不足 | 提供可聚焦边列表 |
| P59 | 状态语义过度依赖颜色 | 色弱用户难区分 | 信任标签失效 | 颜色加文字、图标、形状 |
| P60 | toast 不保证读屏通知 | 错误可能漏报 | 失败无反馈 | 使用 live region，就地错误 |
| P61 | 空状态缺下一步按钮 | 用户只知道为空 | 不知道做什么 | 每个空状态带动作 |
| P62 | 错误状态是原始 message | 英文/traceback 吓人 | 信任下降 | 用户语言、恢复动作、诊断折叠 |
| P63 | 生产版卡片堆叠过多 | 管理后台感 | 高级感下降 | 减少嵌套卡片，建立阅读节奏 |
| P64 | pill/chip 太多 | 视觉碎片化 | 关键标签不突出 | 限制 chip 数量，集中可信边界 |
| P65 | AI 不假装是你的伦理没有贯穿可编辑动作 | 从 AI 推断转确认不够显式 | 审计不清 | 所有转确认动作要显式文案和记录 |

## Recommended Information Architecture

### Collect: Memory Receipt First

Goal: do not ask the user to manage graph placement. Help them confirm how this material will be remembered.

Recommended default flow:

1. Upload or paste material.
2. Optionally write: "Why am I saving this now?"
3. Show a memory receipt after ingest:
   - title, type, import time
   - user-stated reason if present
   - AI-inferred understanding if no user reason, clearly marked
   - source excerpt and extraction quality
   - suggested space expressed as related project or question
   - suggested connections with reason and evidence
   - open loops created from this capture
4. Let the user confirm, edit, reject, defer, or leave unreviewed.
5. Batch ingest must be file-level and asynchronous.

### Recall: Answer Plus Trust Plus Evidence

Goal: make the user feel they are recovering a past judgment, not receiving a generic AI answer.

Recommended default structure:

1. Direct answer.
2. Trust summary:
   - source count
   - user-stated count
   - AI-inferred count
   - low/no evidence state
3. Evidence cards:
   - source title
   - material type
   - excerpt
   - why this is relevant
   - user-stated or AI-inferred status
   - actions: open source, ask from here, save answer, review link
4. AI-inferred content collapsed by default, with explicit review actions.
5. Graph path translated into evidence path card:
   - claim
   - path steps
   - strongest evidence
   - weakest link
   - review status

### Space: Question Workspace

Goal: the user enters a space to resume work on a project or question.

Default layout should show four lanes:

- Recent Captures: latest saved materials and parsing status.
- Remembered Judgments: stable user-confirmed or evidence-supported conclusions.
- Open Loops: unresolved questions and next actions.
- Needs Review: low-confidence AI inferences, route suggestions, weak paths, stale materials.

The default space card should show:

- what this space is tracking
- recent judgment
- open loop count
- needs review count
- recently saved material titles

Hide by default:

- node count
- edge count
- raw graph ids
- layout controls
- numeric confidence

### Evidence Review: Claim Review, Not Graph Editing

Goal: turn graph audit into a clear user decision.

Entry points:

- Recall evidence path.
- Space Needs Review queue.
- Collect suggested connection.
- Low-confidence AI inferred item.

Default review page:

1. System says: A supports or relates to B.
2. Supporting evidence:
   - user-stated why
   - source excerpt
   - related material
3. Path explanation:
   - natural-language steps
   - user-stated vs AI-inferred labels
4. Decision:
   - confirm
   - edit
   - weaken
   - reject
   - defer
5. Result writes back to graph edge, context status, review history, and future recall.

## Priority Roadmap

### P0: Must Fix Before Calling The Frontend Daily-Use Ready

- Default product surface must become evidence-first memory, not graph-first navigation.
- No-match retrieval must show "no reliable evidence found" instead of irrelevant evidence.
- Graph paths must become structured evidence path cards.
- Collect must show real file-level ingest status, especially for real providers.
- AI-inferred content must have explicit review actions.
- Space default must show judgments, open loops, and needs review, not node/edge metrics.
- Empty states must guide the first action: collect, load demo, ask from example, or review queue.

### P1: Should Drive The Next Redesign Phase

- Add Evidence Review as a first-class view or primary Space lane.
- Add open-loop lifecycle: `new`, `confirmed`, `deferred`, `done`, `merged`, `rejected`.
- Add editable Memory Receipt fields: title, why, summary, space, suggested connections.
- Add material type and extraction warning display everywhere evidence appears.
- Add type-aware recall filters.
- Add save-answer-back-to-wiki interaction.
- Replace raw provider/workspace details with user-facing trust and privacy settings.
- Add duplicate detection and merge suggestions to Collect.

### P2: Keep Powerful But Hide By Default

- Advanced Graph Audit can keep node layout, manual edge creation, prune, synthesize, and theme grouping.
- It should be named as an audit/debug surface, not the main product.
- Numeric confidence, raw ids, raw status enums, source/target ids, layout coordinates, and provider runtime details belong behind advanced diagnostics.

## Design Direction

The visual direction should stay high-trust and restrained, but less "poster" and less "backend".

Keep:

- warm paper background
- graphite text
- sage green for user-stated
- amber for AI-inferred and needs review
- blue-gray for graph/evidence path
- restrained 8px-ish radius
- clear typography and real controls

Reduce:

- giant decorative headings in workflow screens
- repeated chips
- nested cards
- raw graph vocabulary
- backend-style inspectors
- status numbers without user meaning

The interface should feel like a premium research desk: calm, readable, exact, and easy to trust.

## Next Validation Checklist

For the next frontend iteration, test against these scenarios:

1. Empty workspace first run.
2. Single PDF with user-stated why.
3. Screenshot with no user why, AI-inferred needs review.
4. Batch upload of 10 mixed files.
5. Batch upload with one broken PDF and one unsupported file.
6. Ask a no-match question.
7. Ask an image-only question.
8. Ask within one space only.
9. Confirm and reject suggested connections from a receipt.
10. Move an item from Inbox to a space with a user reason.
11. Turn an AI-inferred relation into a user-confirmed relation.
12. Complete or defer an open loop.
13. Save a good answer back to wiki.
14. Use keyboard only through Collect and Recall.
15. Use mobile layout for first-run Collect and Recall.

## Handoff Notes For Future Agents

Do not restart the UX critique from scratch. The next useful work is implementation or mockup refinement based on this report.

Suggested next work packages:

- Package A: redesign `CollectView.vue` around Memory Receipt and per-file status.
- Package B: redesign `RecallResult.vue` around trust summary and evidence cards.
- Package C: redesign `SpacesView.vue` and `GraphSpaceView.vue` into Space lanes plus hidden Advanced Audit.
- Package D: add an Evidence Review view backed by edge/context update APIs.
- Package E: add empty, error, privacy, and accessibility pass across the frontend.
