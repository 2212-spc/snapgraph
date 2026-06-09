# SnapGraph User Truth And Frontend Redesign V2

Last updated: 2026-05-07

This document supersedes broad checklist-style UX critique for product definition work. It exists to answer one harder question:

Who is SnapGraph really for first, what painful moment brings them here, what would they use instead, and what must the frontend do so they feel helped within the first minute?

Follow-up depth note: `docs/snapgraph_deep_user_research_2026-05-07.md` extends this beyond the initial example personas. It covers additional users such as technical decision makers, thesis maintainers, evidence workers, and team knowledge stewards, and should be read before finalizing V0 scope.

Do not store API keys in this file. Real-provider tests must use `SNAPGRAPH_LLM_API_KEY` from the local shell or keychain only.

## Brutal Product Decision

SnapGraph should first conquer **deadline-driven judgment workers**:

- students or young researchers doing competitions, papers, or technical projects
- product managers or founders reconstructing old decisions
- AI-heavy knowledge workers who save AI chats, screenshots, papers, notes, and links

This is the "小林 + 阿洁" segment.

Secondary long-term constraint: deep researchers like "陈博士". Their expectations force SnapGraph to be durable, local, source-faithful, and citation-aware.

Do not initially optimize for diary-like writers like "王老师" or pure visual inspiration users like "阿凯". They are valuable later, but if they define V0, the product will become too quiet for PMs, too visual for researchers, too anti-AI for AI-heavy users, and too emotionally ambiguous for a competition demo.

## The First User To Conquer

### Primary Persona: 小林洁

This is a composite of 小林 and 阿洁.

I am 23 to 32. I am a student, PM, founder, researcher, or AI-heavy builder. I have a deadline. I produce arguments, docs, proposals, product decisions, and research summaries. My output depends less on "remembering facts" and more on **recovering why I once believed something**.

I use too many tools:

- Notion, Obsidian, Apple Notes, WeChat Favorites
- ChatGPT/Qwen/Claude chat history
- PDFs, screenshots, browser tabs, Slack/Feishu messages
- local folders with terrible names

I open SnapGraph when I have this feeling:

> I know I thought about this before. I know there was a sentence, screenshot, paper, or data point that made me decide. I cannot remember the exact keyword, file, or date. If I cannot find it soon, I will either make up a new argument or ask AI to produce a plausible one.

The danger is not just lost information. The danger is replacing my real past judgment with a fresh, plausible, fake-current answer.

### Primary Moment

The primary product moment is not:

- "I want to manage my graph."
- "I want to organize my knowledge base."
- "I want an AI answer."
- "I want a beautiful memory dashboard."

The primary moment is:

> I need the sentence, screenshot, source, and reasoning chain that made past-me believe this.

SnapGraph must return that before it shows graph abstractions.

## True Competitors

SnapGraph does not compete with one product. It competes with fallback behavior.

| User State | Real Competitor | Why The Competitor Wins Today | How SnapGraph Must Beat It |
|---|---|---|---|
| "I roughly remember the words." | Spotlight / Finder / browser history | Fast, local, no setup | Semantic recall must be almost as fast and find meaning, not only exact terms |
| "I put it in Notion/Obsidian." | Notion / Obsidian search | Existing habit and workspace | SnapGraph must retrieve the exact old thought faster, with source attached |
| "I need an argument now." | ChatGPT/Qwen | Produces a plausible answer instantly | SnapGraph must show "your old evidence" before "a new AI opinion" |
| "I do research seriously." | Zotero + DEVONthink + rereading | Slow but trustworthy | SnapGraph must preserve source, page, quote, and local durability |
| "I saved visual references." | Mymind / Are.na / Pinterest | Visual recall feels natural | SnapGraph should not chase this first, but must later support image evidence |
| "I write and need my exact words." | Apple Notes / paper notebook | Quiet, durable, no AI contamination | SnapGraph must have pure retrieval mode and exact quotes |
| "This is too much effort." | Not finding it, rethinking it | Zero tool friction | SnapGraph must reduce capture and recall friction below the cost of giving up |

The harshest competitor is **not looking**. If SnapGraph cannot help within 30 to 60 seconds, the user will reconstruct a weaker version of the judgment and move on.

## Bottom-Layer Needs

These are not feature requests. They are load-bearing product truths.

### 1. Users Are Not Looking For Information; They Are Looking For Past Self-Evidence

When users say "find that thing", they often mean:

- the exact sentence I wrote
- the hesitation I had
- the screenshot that convinced me
- the evidence that made a decision feel true
- the source I can cite or reopen

UI implication: the first result should often be **"你当时写过这句话"**, not an AI summary.

Data implication: SnapGraph needs quote-level spans, source excerpt anchors, user-note preservation, and retrieval result types.

Bad UI:

- "Here is an AI answer about your topic."
- "3 graph nodes match your query."
- "Confidence 82%."

Good UI:

- "找到 1 段你写过的原话。"
- "这句话来自 2026-04-18 保存的 `aigc-memory-notes.md`。"
- "旁边这张截图是你当时一起保存的证据。"

### 2. Opening The Original Is Not Optional

After finding the memory, most users immediately want the original:

- PDF page
- screenshot or image
- webpage snapshot
- AI chat transcript
- local file
- note page
- citation source

If the product cannot open the original smoothly, it feels like a teaser, not a tool.

UI implication: every evidence card needs a primary "打开原文" action.

Data implication:

- original file path
- source URI
- page number
- text span
- OCR bounding box if image/PDF
- imported snapshot path
- external app deep link where possible

V0 may not support every integration, but the product promise must be honest:

- "Open local copy"
- "Open in Finder"
- "Open PDF page if page anchor exists"
- "Original webpage snapshot saved"
- "External Zotero jump not supported yet"

### 3. AI Must Be Optional, Bounded, And Clearly Subordinate To User Words

The earlier design treated `AI-inferred why` as useful. This is dangerous.

New rule:

**Only the user can state why they saved something.**

AI may infer:

- what the source appears to discuss
- possible topics
- possible links
- possible future recall questions
- possible relevance to a current query

AI must not silently produce:

- the user's motivation
- the user's judgment
- the user's certainty
- a replacement for the user's old words

Rename product concepts:

- `保存理由`: only user-stated, or empty.
- `系统理解`: AI summary of source content.
- `可能相关`: AI-suggested link.
- `待确认判断`: AI-proposed claim awaiting user action.

UI implication: if no user why exists, show:

> 你当时没有写保存理由。可以现在补一句，让以后更容易找回。

Do not show:

> AI 推断你保存它是因为...

Instead show:

> 系统读到：这份材料主要讨论...

### 4. Capture Must Be Opportunity-Based, Not Guilt-Based

The old "思考回执" can become a trap if it makes users feel they must explain every save.

Users save in different modes:

- emergency save: less than 5 seconds
- quick note: 10 to 20 seconds
- serious research capture: 1 to 3 minutes
- batch import: background task

SnapGraph should support all four.

UI implication:

- The why field is valuable but not morally mandatory.
- Missing why becomes a quality state, not a blocking error.
- Prompt gently after save, not before every save.
- Offer one-tap suggested templates, but never fake the user reason.

Microcopy:

- "现在不写也可以，之后会进入待补理由。"
- "补一句你自己的话，未来找回会准很多。"
- "系统可以帮你总结材料，但不会替你写保存理由。"

### 5. The Product Needs A Pure Retrieval Mode

Some users want no LLM involvement for a query:

- privacy-sensitive PM
- researcher
- writer
- offline/local user
- user seeking exact words

SnapGraph should support at least three recall modes:

1. **原话优先**: search user-written notes, why fields, excerpts, OCR, source text. No answer synthesis unless asked.
2. **证据整理**: retrieve sources and assemble a concise answer with citations.
3. **AI 探索**: use LLM to connect weak clues, propose links, and explain uncertainty.

Default for primary users should be 原话优先 or 证据整理, not unconstrained AI.

### 6. The Interface Must Show "What Was Found" Before "What It Means"

Current AI products often jump to interpretation. SnapGraph should reverse this:

1. Exact or closest user words.
2. Source and excerpt.
3. Why this matched.
4. Optional AI summary.
5. Optional related graph/evidence path.

This is the difference between a memory tool and a chatbot.

### 7. The Product Must Be Calm, But Not Sentimental

The UI should not become "早安小林" or a memory diary unless targeting writers.

Primary users need a tool that feels:

- calm
- fast
- precise
- local
- serious
- elegant

They do not need:

- emotional greetings
- mystical graph language
- "today's memory" sentimentality
- decorative warmth
- productivity dashboard noise

## Segment Analysis

### Segment A: Deadline Judgment Worker

Includes:

- AIGC competition student
- PM preparing roadmap review
- founder writing investor memo
- AI-heavy engineer writing design docs

They open SnapGraph because:

- "I remember I had a thought."
- "I need evidence for a decision."
- "I need to paste a trustworthy paragraph into a doc."
- "I need to not ask ChatGPT to invent a fresh argument."

Must-have:

- semantic recall of old user words
- original source opening
- copy with citation/source
- fast response
- local/privacy clarity
- no-match honesty
- optional AI synthesis

This should be the V0 target.

### Segment B: Deep Researcher

Includes:

- doctoral students
- professors
- independent researchers
- serious nonfiction writers

They open SnapGraph because:

- "I need a note I made two years ago."
- "I need to jump to the PDF page."
- "I need citation and source durability."

Must-have:

- source durability
- exact quotes
- page-level anchors
- citation metadata
- local/offline mode
- no cloud AI by default
- exportable Markdown/SQLite

This should shape architecture, not dominate V0 UI.

### Segment C: Visual Inspiration Worker

Includes:

- designer
- photographer
- creative director
- brand strategist

They open SnapGraph because:

- "I remember the feeling of an image."
- "I need visual similarity and mood."
- "I need to see images side by side."

Must-have:

- image thumbnails
- visual search
- mood tags
- drag to Figma
- low-friction capture

Do not let this define V0 unless the project chooses to compete directly with Mymind/Are.na.

### Segment D: Quiet Personal Writer

Includes:

- teacher-writer
- diary keeper
- essayist
- personal knowledge user

They open SnapGraph because:

- "I need exact words."
- "I do not want suggestions."
- "I want it to feel like paper and last forever."

Must-have:

- exact quote retrieval
- timeline browsing
- pure local mode
- no AI suggestions by default
- plain text export

This is emotionally powerful but not the initial contest/product wedge.

## V0 Product Promise

SnapGraph V0 should promise:

> Ask in your own words. SnapGraph finds what you wrote, shows the source that made it matter, and helps you decide whether the old judgment still holds.

It should not promise:

- automatic second brain
- total knowledge graph
- AI research assistant that understands everything
- graph visualization
- emotional memory companion

## Frontend Redesign: The Four Real Screens

### 1. Find: "找我写过的话"

This should be the default screen when the workspace has data.

Primary input:

- placeholder: "例如：我之前为什么觉得不该做 X？"
- scope selector: 全部 / 当前空间 / 只搜用户原话 / 只搜图片 / 只搜 PDF
- mode switch: 原话优先 / 证据整理 / AI 探索

Before submit, the UI should show:

- local-only or model mode
- number of searchable materials
- whether AI will be called

Result hierarchy:

1. "找到的原话"
   - exact user note or closest semantic match
   - unchanged text, with quote styling
   - source, date, material type
   - action: copy quote, open source
2. "相关证据"
   - source cards with excerpts
   - image thumbnails or PDF page snippets if available
   - why this matched
3. "AI 整理"
   - collapsed or secondary unless user chose AI mode
   - clearly marked as generated now
4. "继续处理"
   - save answer to wiki
   - create review item
   - ask from this source
   - mark old judgment as still valid / outdated / uncertain

No-match state:

- "没有找到你写过的可靠原话。"
- show searched scope
- offer actions:
  - broaden scope
  - include AI-inferred material
  - search raw source text
  - import more material
  - write a new note

Never invent a memory in no-match state.

### 2. Save: "先保存下来"

This should be optimized for less than 5 seconds.

Default capture flow:

1. Drop file, paste text, paste URL, or save screenshot.
2. Optional input: "如果愿意，补一句为什么保存。"
3. Click "保存".
4. Show receipt.

Receipt sections:

- Saved: title, type, time, local source stored.
- Your reason: user-stated text, or empty with "待补".
- What the system read: AI or parser summary of source content.
- Search hooks: generated future recall questions, not framed as user intention.
- Possible links: reviewable suggestions.
- Source quality: extracted text, OCR, warnings, unsupported parts.
- Actions: open source, add reason, move to space, review links, continue saving.

Critical rule:

- A missing why is not filled by AI.
- AI can help write a draft only if the user explicitly clicks "帮我起草一句，我来确认", and the result remains draft until confirmed.

Batch flow:

- each file has status
- statuses: queued, extracting, OCR, summarized, saved, needs review, failed, duplicate
- user can leave page
- user can retry failed file
- user can add one shared batch note, but it must be labeled as batch-level, not per-file why

### 3. Workspaces: "我现在在追什么问题"

Rename default mental model:

- Avoid "图谱" as primary navigation.
- Use "空间" or "项目" or "问题".
- Keep graph as advanced audit.

Workspace card should show:

- question or project this space tracks
- last useful user quote
- recent materials
- open loops
- needs review
- source freshness

Workspace detail should have lanes:

1. Recent Captures
2. Remembered Judgments
3. Evidence
4. Open Loops
5. Needs Review

Only an advanced button should open graph audit:

- "查看连接审计"
- not "专业模式"
- not default

### 4. Review: "这条连接靠谱吗"

Review is the missing trust loop.

A review item asks one question:

> 系统认为 A 和 B 有关系。你认可吗？

Review card:

- proposed relation in natural language
- source excerpt
- user-stated note if any
- AI reason if any, clearly marked
- affected future recall results

Actions:

- confirm
- edit relation
- weaken
- reject
- defer
- mark source outdated

This is where graph edges become product value.

## Detailed UI Requirements

### Global Navigation

Recommended labels:

- 找回
- 保存
- 空间
- 待确认

Avoid default labels:

- 图谱
- 专业模式
- Inspector
- 节点
- 边

Advanced areas may still use graph vocabulary, but only after the user chooses audit/debug.

### First Run

If there are zero materials:

- Do not show "找回一个过去的判断" as the only primary action.
- Show:
  - "保存一条以后可能找不到的材料"
  - "加载示例记忆"
  - "导入文件夹"
  - "粘贴一段 AI 对话"

The first-run success moment should be:

1. user saves one material
2. sees original preserved
3. optionally adds a reason
4. asks a fuzzy question
5. sees their saved text/source return

### Recall Result Card

Must distinguish result types:

- Exact user quote
- Semantic match from user words
- Source excerpt only
- AI summary generated now
- AI-suggested relation

Each type should have its own label and visual treatment.

Do not put unknown/source-only content under AI-inferred.

### Evidence Card

Every evidence card should contain:

- title
- type: PDF / image / webpage / Markdown / AI chat / note
- source date or import date
- excerpt or thumbnail
- why it matched
- user-stated note if available
- extraction quality
- open source action
- copy action
- ask from here action

### Source Opening

Minimum V0:

- open local saved source
- open containing folder
- show stored Markdown/source page

Better V1:

- PDF page anchor
- browser snapshot and original URL
- image preview with OCR overlay
- AI chat transcript position
- Zotero or DEVONthink integration

### Privacy And AI Mode

Before AI is called, UI should be able to answer:

- Is this local-only?
- Which model will be used?
- What content will be sent?
- Can I run this without AI?

Settings should not show raw workspace path by default. It should show user-facing trust controls:

- Local-only mode
- Allow AI for summaries
- Allow AI for image OCR/vision
- Allow AI for answer synthesis
- Never send sources from private spaces

### Copy / Export

Primary users often need to paste into a doc.

Every result should support:

- copy quote
- copy with source
- copy as Markdown citation
- save answer back to wiki
- export selected evidence bundle

### Time And Freshness

PMs and researchers need to know whether old judgment still holds.

UI should show:

- imported date
- source date if known
- last reviewed date
- stale indicator if old
- "newer material may contradict this" if detected

Do not overdo this for V0, but design data model now.

## Data Model Implications

Current fields are useful but not enough for the deeper product promise.

Need fields or derived structures:

- `user_note_raw`: exact user-written reason or note.
- `user_note_created_at`.
- `user_note_confirmed`: true only when user explicitly wrote or accepted.
- `system_summary`: what parser/AI read from source.
- `system_summary_provider`.
- `source_locator`: file path, URL, page, span, bounding box, transcript position.
- `source_open_method`: local file, local snapshot, external URL, app deep link.
- `material_type`: PDF, image, webpage, markdown, chat, note.
- `extraction_status`: success, partial, failed, unsupported.
- `extraction_warnings`.
- `ocr_text_available`.
- `visual_understanding_available`.
- `privacy_scope`: normal, private, local-only.
- `llm_allowed`: true/false or per-capability flags.
- `recall_result_type`: exact_user_quote, semantic_user_quote, source_excerpt, ai_summary, ai_relation.
- `review_status`: unreviewed, confirmed, edited, weakened, rejected, deferred.
- `staleness_status`: fresh, old, possibly_outdated, contradicted.

Important rename:

- Avoid treating AI-inferred as a kind of saved reason.
- Use AI-inferred for relations, summaries, topics, or draft suggestions.
- Save reason should be user-stated or empty unless the user confirms a draft.

## API And Backend Implications

To support the frontend promise, backend needs:

- a recall endpoint with modes: `quote_first`, `evidence_answer`, `ai_explore`
- result typing for each card
- no-match thresholds that can produce a successful empty result
- material type filters
- source locator fields in evidence cards
- extraction warning fields
- file-level ingest job states
- review endpoints for proposed relations and generated summaries
- privacy flags respected before provider calls
- copy/export formatting endpoint or frontend utility

For speed:

- local full-text search / FTS should answer exact and fuzzy user-note queries before LLM
- embeddings or semantic retrieval can supplement
- LLM should be called only after local recall has found candidate evidence, unless user selects AI Explore

## What Current Frontend Gets Right

- Recall as default direction is closer to product truth than graph-first.
- User-stated and AI-inferred labels are conceptually important.
- Collect already has a receipt-like surface.
- Spaces already attempt to summarize what a workspace tracks.
- Graph workbench has useful audit primitives, but they are too exposed.
- Local provider config and API key environment-name policy support trust.

## What Current Frontend Must Reverse

### Reverse 1: "放进图谱" -> "保存为可找回的记忆"

"Graph" is backend value. The user action is saving something future-me can find.

### Reverse 2: "AI-inferred why" -> "No user reason yet"

Do not let AI invent saving motivation. This is foundational.

### Reverse 3: "Answer first" -> "Found words/source first"

When the query asks for remembered judgment, show old quote first. AI answer is optional.

### Reverse 4: "Space metrics" -> "Work resumption"

Node and edge count are not meaningful. Show what changed, what matters, what needs review.

### Reverse 5: "Professional mode" -> "Advanced audit"

Professional mode sounds like users should become graph operators. Advanced audit admits this is optional.

## Pixel-Level And Interaction Details

These details matter because they determine whether the product feels trustworthy.

### Buttons

Primary CTA on Save:

- "保存"
- "保存并生成回执"

Avoid:

- "放进图谱"

Primary CTA on Recall:

- "找回"

Secondary:

- "只搜原话"
- "整理成答案"
- "打开原文"

### Labels

Use:

- 用户原话
- 原文摘录
- 系统读到
- 可能相关
- 待确认
- 证据不足
- 本地保存

Avoid in default UI:

- node
- edge
- graph path raw
- origin
- confidence %
- source_id
- graph_space_id
- provider runtime

### Empty States

Bad:

- "还没有材料。"

Good:

- "还没有可找回的材料。先保存一条你以后可能会忘记出处的内容。"
- Button: "保存第一条材料"
- Button: "加载示例记忆"

### No-Match State

Bad:

- showing weak irrelevant evidence
- AI answer without evidence

Good:

- "没有找到可靠的本地证据。"
- "已搜索：全部空间，42 条材料，用户原话 + 原文。"
- Actions: broaden scope, include AI suggestions, import material, write new note.

### Progress

Bad:

- simulated steps that finish before real provider completes

Good:

- file-level queue
- actual state
- elapsed time
- retry
- "可以离开，完成后会进入待确认"

### Visual Hierarchy

The most visually privileged object should be:

- exact user quote or source excerpt

Not:

- hero headline
- graph canvas
- provider status
- decorative receipt

### Mobile

Mobile should not expose graph editing.

Mobile priorities:

1. quick capture
2. quick recall
3. open source
4. add reason later

Hide:

- graph canvas editing
- edge operations
- layout tools

## Hard Product Constraints

These are non-negotiable if SnapGraph wants trust.

1. Never present AI-generated text as user memory.
2. Never answer a no-evidence memory question as if evidence exists.
3. Never hide source access behind graph interactions.
4. Never require graph organization before saving.
5. Never make the user write why before allowing capture.
6. Never show raw graph internals in the default user flow.
7. Never call cloud AI without clear mode/config awareness.
8. Never let missing extraction quality look like successful understanding.

## V0 Acceptance Tests

The next frontend is not good enough until these pass.

### Test 1: Deadline Student

User imports:

- one AI chat Markdown
- one paper PDF
- one screenshot

User asks:

> 我之前为什么觉得 memory 三层结构重要？

Pass condition:

- top result includes user's saved sentence if present
- source cards show PDF/screenshot/chat
- AI summary is secondary
- user can open source and copy quote with source

### Test 2: PM Decision

User saved a screenshot and note:

> 不做 X，因为访谈里 6/8 个用户其实只需要导出，不需要协作。

Three months later user asks:

> 当时为什么不做 X？

Pass condition:

- answer starts with the old note
- screenshot appears as evidence
- newer contradictory material, if any, appears as warning
- copy-to-doc is one click

### Test 3: Missing Why

User saves image without why.

Pass condition:

- receipt says no user reason yet
- AI summary is separate as "系统读到"
- user can add reason later
- product never says "你保存它是因为..."

### Test 4: No Match

User asks an unrelated question.

Pass condition:

- no reliable evidence state
- no irrelevant evidence cards
- no AI answer masquerading as memory

### Test 5: Pure Retrieval

User turns off AI mode.

Pass condition:

- recall still works over local text/OCR/index
- UI says no model was called
- results are quote/source based

### Test 6: Batch Import

User imports 50 mixed files.

Pass condition:

- per-file status
- failures isolated
- user can leave page
- warnings visible
- duplicates detected

### Test 7: Review Relation

AI suggests a source relates to a project.

Pass condition:

- user sees natural-language relation
- supporting evidence visible
- user can confirm/edit/weaken/reject/defer
- future recall respects the decision

## Priority Implementation Plan

### Phase 1: Product Language And Recall Result Rewrite

Files likely touched:

- `frontend/src/components/RecallHome.vue`
- `frontend/src/components/RecallResult.vue`
- `frontend/src/styles.css`

Goals:

- introduce recall modes
- result types
- no-match state
- source-first evidence cards
- remove misleading "这是我的回答"
- reduce raw graph path display

### Phase 2: Collect Receipt Rewrite

Files likely touched:

- `frontend/src/components/CollectView.vue`
- API response shape for ingest

Goals:

- rename "放进图谱"
- make why optional but valuable
- separate user reason from system summary
- show source quality
- show per-file status foundation
- make suggested links reviewable

### Phase 3: Space As Work Resumption

Files likely touched:

- `frontend/src/components/SpacesView.vue`
- `frontend/src/components/GraphSpaceView.vue`

Goals:

- replace node/edge metrics with judgments/open loops/review
- add lanes
- hide graph audit by default
- rename Professional Mode to Advanced Audit

### Phase 4: Evidence Review

New or refactored component:

- `frontend/src/components/EvidenceReviewView.vue`

Goals:

- turn proposed graph relations into review cards
- write decisions back
- make AI-inferred useful without being untrusted sludge

### Phase 5: Backend/Data Corrections

Goals:

- no-match thresholds
- result typing
- source locators
- extraction warnings
- privacy/AI mode flags
- open source actions

## Final Design North Star

SnapGraph is not "AI cognitive graph software".

SnapGraph is:

> a local, source-faithful memory desk for people whose work depends on recovering their own past judgments.

The graph is the engine.

The user-facing product is:

- exact old words
- source evidence
- honest uncertainty
- optional AI help
- reviewable connections
- fast work resumption

If a screen does not help with one of those, it is probably decoration, backend leakage, or design ego.
