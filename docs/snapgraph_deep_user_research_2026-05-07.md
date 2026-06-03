# SnapGraph Deep User Research

Last updated: 2026-05-07

This document is the deeper user-research and product-definition layer for SnapGraph. It should be read before designing screens, changing information architecture, writing demo stories, or deciding what V0 should include.

It is not a generic persona list. The method is:

1. Become a real user with a real deadline, fear, workflow, and substitute.
2. Ask why they open SnapGraph at that exact moment.
3. Identify what would make them trust it within 30 to 60 seconds.
4. Identify what would make them leave for Notion, ChatGPT, Finder, Zotero, paper, Figma, or "I will just rethink it."
5. Convert only the repeated and high-stakes moments into product requirements.

Do not store API keys in this document. Use `SNAPGRAPH_LLM_API_KEY` from the local shell/keychain for live provider tests.

## Executive Decision

SnapGraph V0 should not be "a graph knowledge base".

SnapGraph V0 should be:

> a local, source-faithful memory desk for people whose work depends on recovering old judgments with evidence.

The strongest initial target is not one demographic. It is a work situation:

> I have to produce a decision, memo, plan, ADR, report, or argument soon, and I know I had evidence and a thought before, but I cannot find the exact words or sources.

The V0 wedge should target:

- deadline-driven judgment workers: students, PMs, founders, AI-heavy knowledge workers
- technical decision makers: AI/RAG/agent/backend engineers who need ADR/PR/benchmark evidence
- thesis maintainers: founders, investors, analysts tracking why a view changed

These are the users most likely to feel the "aha":

> It did not give me a new AI answer. It gave me my old reason, the source, and something I can cite or paste.

V0 should use deep researchers, evidence workers, quiet writers, and team knowledge leads as **trust constraints**, not as the full first product surface.

V0 should not primarily target pure visual inspiration workers or diary-like writers, but it must satisfy their baseline constraints where they overlap with evidence: images cannot be invisible, and exact user words must never be rewritten.

## The Research Map

Nine user situations were explored through first-person subagent reviews and direct source inspection:

| Segment | Representative User | Open SnapGraph To | Real Substitute | V0 Role |
|---|---|---|---|---|
| Deadline student / young knowledge worker | 小林 | find an old thought for a competition or paper | Notion, ChatGPT, rethinking | Core |
| Product manager | 阿洁 | recover why a feature decision was made | Notion, Feishu/Slack search, ChatGPT | Core |
| Technical decision maker | 周航 | recover why an architecture choice or rejection happened | ADRs, GitHub, logs, PR search | Core early adopter |
| Founder / investment analyst | 赵岚 | maintain and revisit a market thesis | Notion, Zotero, Sheets, ChatGPT | Strong V1 direction |
| Deep researcher | 陈博士 | find old paper notes, PDF page, citation | Zotero, DEVONthink, Obsidian | Trust constraint |
| Evidence worker | 许弋 | assemble defensible evidence packets | DEVONthink, manual folders, docs | Trust constraint / V1 |
| Team knowledge steward | 孟然 | preserve team decisions and evidence | Notion, Confluence, Feishu, Slack | Future team direction |
| Visual inspiration worker | 阿凯 | recover images by mood and visual memory | Mymind, Are.na, Pinterest, Figma | Not V0, image evidence constraint |
| Quiet writer | 王老师 | recover exact personal wording | Apple Notes, paper notebook | Exact-word constraint |

## The Core Human Truth

Users are not mainly asking:

- "What does this topic mean?"
- "Summarize my knowledge base."
- "Show my graph."
- "Give me an AI answer."

They are asking:

- "What did I write then?"
- "What source made me believe it?"
- "Can I trust this enough to cite, copy, or decide from it?"
- "Has newer evidence weakened it?"
- "Did the system guess, or did I actually say this?"

The product must therefore privilege:

1. User's exact words.
2. Original source access.
3. Evidence and counter-evidence.
4. Honest no-match.
5. Clear AI boundaries.
6. Copy/export into real work.

Anything else is secondary.

## Non-Negotiable Product Laws

These laws emerged across nearly every user type.

### Law 1: Only The User Can Say Why They Saved Something

The old pattern of `AI-inferred why_saved` is not safe enough for the product SnapGraph wants to be.

New rule:

- `保存理由` is user-stated or empty.
- If empty, show `待补理由` or `未填写保存理由`.
- AI may provide `系统读到`, `可能相关`, `建议标签`, `待确认连接`, or `保存理由草稿`.
- A draft becomes a user reason only after explicit user confirmation.

Why this matters:

- 小林 fears AI will contaminate his old thought.
- 阿洁 will not trust PM decision memory if AI writes her motivation.
- 陈博士 sees it as academically unsafe.
- 王老师 sees it as an emotional violation.
- 许弋 cannot use inferred motivation in evidence work.

Immediate code/UI implications:

- Rename ingest progress step `识别保存理由` to `读取材料内容` or `生成系统摘要`.
- Do not fall back from empty user why to `currentEvidenceCard.why_saved` as a displayed "保存理由".
- Separate `user_reason` from `system_summary` in API and UI.
- Treat `AI-inferred` as relation/summary/tag/relevance status, not as a saved reason status.

### Law 2: Results Must Show Found Evidence Before Generated Meaning

The first result should not be "这是我的回答".

The first result should be one of:

- "找到 2 段你写过的原话。"
- "找到 3 条原文证据，但没有用户原话。"
- "没有找到可靠的本地证据。"

Then, and only then:

- AI整理
- 证据路径
- 下一步建议

Why this matters:

- ChatGPT is already better at producing fluent new answers.
- SnapGraph wins only when it returns old evidence faster and more faithfully than the user can reconstruct it.

### Law 3: Every Evidence Card Needs A Source Action

Users leave if they cannot open the original.

Minimum V0 source actions:

- Open generated source page.
- Open local raw copy or containing folder.
- Show original filename and local saved path.
- For PDF: page if available, otherwise "page unavailable".
- For image: thumbnail/full preview.
- For web: saved snapshot if available, otherwise original URL plus warning.

V1 source actions:

- PDF page anchor.
- text span / OCR bounding box.
- GitHub PR/issue/comment anchor.
- Zotero/DEVONthink deep link.
- Slack/Feishu/Notion original link or imported snapshot.

### Law 4: No-Match Must Be A Successful Honest State

No-match is not failure. False evidence is failure.

Bad:

- returning eight weakly related materials
- generating a plausible answer without evidence
- hiding the searched scope

Good:

- "没有找到可靠的本地证据。"
- "已搜索：42 条材料，其中 7 条有用户原话，12 条 PDF，5 张图片。"
- Actions:
  - broaden scope
  - include source text
  - include AI suggestions
  - import more materials
  - write a new note

### Law 5: Pure Retrieval Mode Is Required

AI can be powerful, but it must not be mandatory.

Recall modes:

- `原话优先`: no LLM, exact/semantic local retrieval of user text and source excerpts.
- `证据整理`: local retrieval first, optional model to organize evidence.
- `AI 探索`: model may propose weak links, always labeled.

This mode is required by:

- privacy-sensitive PMs
- researchers
- writers
- consultants
- engineers with sensitive logs/code
- team knowledge owners with permission boundaries

### Law 6: Evidence Must Be Exportable

Users are not staying inside SnapGraph for pleasure. They need to ship:

- competition deck
- PRD
- quarterly roadmap
- ADR
- investment memo
- consulting report
- research chapter
- team handoff

Therefore every serious result needs:

- copy quote
- copy with source
- copy evidence card
- copy evidence packet
- save answer back to wiki
- export selected evidence bundle

## Segment Deep Dives

### 1. 小林: Deadline Student / Young Knowledge Worker

Moment:

> "I have 48 hours. I remember I wrote a sentence about why SnapGraph is not just an AI knowledge base. If I cannot find it, I will ask ChatGPT to write a plausible version."

What makes him trust SnapGraph:

- exact old sentence appears first
- source PDF/screenshot/chat/Markdown appears beside it
- it says whether AI was called
- no-match is honest
- copy quote/source is one click

What makes him leave:

- first screen gives AI prose
- graph terminology appears before evidence
- no original source
- AI-inferred why looks like his own reason
- batch upload looks stuck

Product demand:

- "救 deadline 的记忆工具", not "认知图谱系统".
- First screen after recall: found user words, not generated answer.
- Evidence cards: open source, copy, material type, extraction quality.

### 2. 阿洁: Product Manager

Moment:

> "Tomorrow my boss will ask why we decided not to build X three months ago. I need the old decision evidence, not a new argument."

What makes her trust SnapGraph:

- old note: "不做 X，因为 6/8 个用户只需要导出，不需要协作编辑。"
- source dates, interview excerpts, screenshots
- copy-to-PRD evidence packet
- AI permission clarity
- stale/contradictory newer material warning

What makes her leave:

- no source opening
- cannot copy citation
- AI rewrites old decision
- privacy unclear
- batch imports block

Product demand:

- decision evidence packet
- copy with source
- privacy before AI
- "still valid / outdated / uncertain" status

### 3. 周航: Technical Decision Maker

Moment:

> "Why did we reject Neo4j / LangGraph / this embedding approach six weeks ago?"

What makes him trust SnapGraph:

- ADR, PR comment, issue, benchmark, log evidence
- repo/project/service filters
- commit/PR/issue locators
- copy into ADR format
- rejected alternatives preserved

What makes him leave:

- generic AI architecture explanation
- no PR/commit/source locator
- graph internals instead of engineering evidence path
- no CLI/batch flow

Product demand:

- This user is a strong early adopter.
- Killer demo: ingest ADR + PR comments + benchmark + LLM chat log, ask "为什么 reject Neo4j?", return old rationale, benchmark, PR link, and copyable ADR section.

### 4. 赵岚: Founder / Investment Analyst

Moment:

> "Why did I first believe this market thesis, what weakened it later, and what changed in the last 90 days?"

What makes her trust SnapGraph:

- thesis timeline
- supporting evidence and counter-evidence
- source credibility and bias labels
- outdated/stale indicators
- evidence packet for memo

What makes her leave:

- only support evidence, no反证
- no source snapshots
- no thesis state
- no privacy for interviews

Product demand:

- Strong V1 expansion: "判断会变化" is bigger than "找回旧判断".
- Add concepts: thesis state, counter-evidence, contradiction, freshness, source credibility.

### 5. 陈博士: Deep Researcher

Moment:

> "I need the PDF page and my old skeptical note from two years ago."

What makes him trust SnapGraph:

- raw source immutable
- PDF saved locally
- page number and citation
- exact quote
- no cloud AI by default
- exportable Markdown/SQLite/JSON

What makes him leave:

- no page locator
- AI summary before original
- inferred reason
- no DOI/citation fields
- no reliable no-match

Product demand:

- Not V0 main story, but a hard trust constraint.
- Researcher can tolerate plain UI; cannot tolerate soft evidence.

### 6. 许弋: Consultant / Investigation / Evidence Worker

Moment:

> "I need to deliver a defensible evidence packet without leaking sources or relying on unverifiable AI prose."

What makes them trust SnapGraph:

- immutable source or snapshot
- source locator
- timestamps
- privacy scope
- evidence/counter-evidence packet
- operation log
- AI metadata

What makes them leave:

- no source locator
- no privacy redline
- no evidence packet export
- weak no-match
- graph path string instead of evidence chain

Product demand:

- V1/V2 high-value direction.
- V0 must at least support evidence packet foundations and source locators.

### 7. 孟然: Team Knowledge Steward

Moment:

> "The team needs to remember who said what, who confirmed it, whether it is still valid, and what can be shared."

What makes her trust SnapGraph:

- speaker/importer/confirmer
- decision state
- audit log
- evidence packet share
- permission-respecting recall

What makes her leave:

- no identity/permission model
- AI summary becomes team consensus
- no share preview/redaction
- graph editing instead of review queue

Product demand:

- Team version should exist later.
- V0 should not build full collaboration.
- But V0 must add future-compatible fields:
  - `author/speaker/importer/confirmer`
  - audit event model
  - evidence packet export/share

### 8. 阿凯: Visual Inspiration Worker

Moment:

> "Find the quiet, paper-like, not cheap visual references I saved before, and show them beside this project."

What makes him trust SnapGraph:

- image thumbnails first
- visual mood recall
- OCR
- color/material/font tags
- moodboard and Figma drag

What makes him leave:

- text-only evidence cards
- no thumbnails
- no visual search
- graph terms

Product demand:

- Not V0 target.
- But image evidence must not be invisible.
- V0 should at least show thumbnails, OCR/visual extraction status, and image filters.

### 9. 王老师: Quiet Writer

Moment:

> "I need that exact sentence from the train six months ago. One word changed means it is not the same."

What makes her trust SnapGraph:

- exact quote mode
- no AI suggestions
- timeline
- plain text export
- original photo/note preserved
- local/offline clarity

What makes her leave:

- "这是我的回答"
- AI suggestions about personal writing
- graph language
- similar sentence presented as original

Product demand:

- Not V0 target.
- But exact-word retrieval is a universal bottom line.

## What Actually Defines The V0 User

The V0 user is not defined by job title. They are defined by a pattern:

1. They produce work from judgments.
2. They save materials across tools.
3. Their old reasons matter later.
4. They cannot rely on memory or keyword search.
5. A plausible new AI answer is dangerous but tempting.
6. They need output they can cite, paste, or defend.

Best V0 beachhead:

- 小林 / 阿洁 / 周航 composite:
  - deadline-driven
  - AI-heavy
  - evidence-sensitive
  - tolerant of local tools
  - willing to try new workflows
  - able to understand why "AI does not pretend to be you" matters

## V0 Scope Decision

### Must Be In V0

- Recall modes: `原话优先`, `证据整理`, `AI 探索`.
- Results start with found user words or source excerpts.
- No-match as a first-class honest result.
- Open original source or local saved source from every evidence card.
- Copy quote / copy with source / copy evidence packet lite.
- Collect wording changed from graph-first to memory-first.
- User reason separate from system summary.
- Missing user reason shown as `待补理由`.
- AI suggestions and relations always reviewable.
- Material type filters: text, PDF, image, web, AI chat/note if detectable.
- Extraction status/warnings visible.
- Pure local mode.
- Basic source locator fields even if incomplete.
- Space default as work resumption: recent captures, remembered judgments, open loops, needs review.
- Advanced graph audit hidden by default.

### Should Be Designed In Data Now, But UI Can Be Light

- source locator: path, URL, page, span, bounding box, commit/PR anchor, transcript timestamp
- source date vs import date
- author/speaker/importer/confirmer
- review status and audit events
- privacy scope
- evidence packet structure
- counter-evidence / contradicts relation
- staleness status
- extraction quality fields

### Should Wait Until V1/V2

- full team accounts and permissions
- Zotero/DEVONthink deep integrations
- GitHub native sync
- Slack/Feishu/Notion live connectors
- visual moodboard product
- Figma drag workflow
- full citation manager
- robust redaction pipeline
- source-bias analysis

## Current Frontend Failures Reframed

These are not cosmetic. They conflict with user trust.

### "把材料放进图谱"

User hears:

> I now have to manage your internal system.

Replace with:

> 保存为可找回的记忆

### "识别保存理由"

User hears:

> The AI will infer my intention.

Replace with:

> 读取材料内容
> 生成系统摘要
> 建议可能关联

### "这是我的回答"

User hears:

> The AI is answering instead of finding my old evidence.

Replace with:

> 找到的原话
> 找到的证据
> 基于证据整理

### "节点 / 边 / Inspector / Confidence"

User hears:

> This is a backend debugger.

Replace default UI with:

> 判断 / 证据 / 反证 / 待确认 / 已过期 / 可引用

Keep graph terms only in advanced audit.

## Required UI Architecture

### Main Navigation

Recommended:

- 找回
- 保存
- 空间
- 待确认

Optional later:

- 证据包
- 时间线

Avoid:

- 图谱 as primary nav
- 专业模式 as user-facing name

### Recall Screen

Top controls:

- query box
- mode: 原话优先 / 证据整理 / AI 探索
- scope: 全部 / 当前空间 / 用户原话 / PDF / 图片 / 网页 / AI 对话 / 私密排除
- AI status: 本地检索 / 将调用 Qwen / 不发送私密空间

Result order:

1. Found user words.
2. Found source excerpts.
3. Evidence cards.
4. Counter-evidence / freshness warnings.
5. AI organized answer.
6. Review / export / save actions.

### Collect Screen

Default copy:

- "先保存下来"
- "以后能找回原话、来源和判断来路"

Receipt sections:

- local source saved
- user reason or `待补`
- system read
- extraction quality
- possible connections
- future recall hooks
- actions: open source, add reason, move space, review, copy, continue

### Space Screen

Default lanes:

- Recent Captures
- Remembered Judgments
- Evidence / Counter-evidence
- Open Loops
- Needs Review

Metrics to show:

- user quotes
- evidence count
- needs review
- stale judgments
- recent captures

Metrics to hide by default:

- node count
- edge count
- confidence %

### Review Screen

Each review card asks:

> 系统认为 A 和 B 有关系。你认可吗？

Actions:

- confirm
- edit
- weaken
- reject
- defer
- mark outdated

Review result must affect future recall.

### Evidence Packet

V0-lite packet:

- selected conclusion
- user quote
- source excerpts
- material titles/types/dates
- original source links/paths
- AI/generated labels
- review status
- open questions

Copy/export formats:

- Markdown
- plain text
- PRD/ADR-style block

## Data Model Additions

Current fields are directionally useful but insufficient.

Add or plan:

```text
user_reason_text
user_reason_status: empty | user-stated | draft-confirmed
system_summary
system_summary_origin: parser | llm | manual
material_type
source_locator: path/url/page/span/bbox/comment_url/commit/timestamp
source_date
imported_at
original_filename
raw_source_preserved: boolean
extraction_status: queued | extracting | success | partial | failed | unsupported
extraction_warnings[]
ocr_status
visual_summary_status
privacy_scope: normal | private | local-only | sensitive
ai_allowed: none | metadata-only | excerpts | full
author
speaker
importer
confirmer
review_status: unreviewed | confirmed | edited | weakened | rejected | deferred | outdated
evidence_role: supports | contradicts | supersedes | rejected_by | caused_by | fixed_by
staleness_status: fresh | old | possibly_outdated | contradicted
source_credibility
source_bias_note
audit_events[]
evidence_packet_id
```

## Backend/API Implications

Needed endpoint or payload changes:

- recall mode param: `quote_first | evidence_answer | ai_explore`
- source type filters
- local-only flag
- AI permission metadata
- no-match result object
- result card type:
  - exact_user_quote
  - semantic_user_quote
  - source_excerpt
  - system_summary
  - ai_relation
  - counter_evidence
- evidence packet export endpoint
- extraction status endpoint for batch ingest
- source open/locator payload
- relation review endpoint that affects future retrieval
- privacy-scope enforcement before provider calls

## Product Positioning

Bad positioning:

> AI cognitive graph knowledge base.

Better positioning:

> Find your old judgment, source, and evidence before AI invents a new one.

Chinese options:

- 找回你当时为什么这样想。
- 先找回原话，再整理证据。
- 不让 AI 冒充你的记忆。
- 让每个判断都有来路。

Do not overuse sentimental "past self" copy in workflow UI. It is useful for story, not for every screen.

## Practical Next Design Task

Before another visual mockup, design one complete flow:

### Killer Flow A: Deadline Judgment Recall

1. User asks: "我之前为什么不做 X?"
2. UI says: local-only or model mode.
3. UI returns found user quote.
4. Evidence cards show screenshot/interview/PDF.
5. One card has extraction warning.
6. One newer source contradicts old judgment.
7. User opens original source.
8. User copies evidence packet into a doc.
9. User marks old judgment: still valid / outdated / uncertain.

### Killer Flow B: Technical Decision Recall

1. Ingest ADR + PR comment + benchmark + LLM chat.
2. Ask: "为什么 reject Neo4j?"
3. UI returns old ADR/PR quote first.
4. Shows benchmark evidence.
5. Shows rejected alternative.
6. Exports ADR block.

If these flows feel excellent, SnapGraph has a product.

If these flows still feel like graph management, redesign again.

## Final Verdict

The deep research expanded the target, but narrowed the product truth.

SnapGraph should not be designed around one fictional user. It should be designed around one repeated human situation:

> A person made or saved a judgment under context. Later, the context is gone, the deadline is real, and a plausible AI answer is tempting. SnapGraph must recover the user's old words, source evidence, uncertainty, and next action without pretending.

That is the product.

The graph is infrastructure.

The frontend must feel like retrieval of truth, not management of structure.
