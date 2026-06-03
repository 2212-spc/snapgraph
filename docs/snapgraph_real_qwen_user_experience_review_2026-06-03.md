# SnapGraph Real Qwen User Experience Review

Date: 2026-06-03

This review is based on actual local runtime usage at `http://127.0.0.1:8765`, with the Qwen provider configured and verified.

## Evidence Collected

- Runtime config: `/api/config` reported `provider=qwen`, `model=qwen3-vl-plus`, `has_api_key=true`, `provider_ready=true`.
- Real provider ask test returned `provider_used=qwen`, `fallback_used=false`.
- Uploaded three new test files through `/api/ingest` using real Qwen:
  - `real-qwen-capture-receipt.md`, marker `金针测试-20260603`, source `src_20260603T06495628656_ede39035`
  - `current-batch-retrieval-review.txt`, marker `银线测试-20260603`, source `src_20260603T06501427962_bbe5b67b`
  - `trust-layer-note.html`, marker `铜镜测试-20260603`, source `src_20260603T06502600506_983d19a9`
- Asked four real Qwen questions:
  - why the `金针` material mattered
  - what users expect after uploading three related materials
  - what answer layout `铜镜` proposes
  - what to prioritize after combining all three newly uploaded materials
- Ran diagnostics:
  - `snapgraph lint`: WARN
  - `snapgraph graph`: 128 nodes, 167 edges, no graph orphans
  - `snapgraph report`: generated `wiki/graph_report.md`

## What SnapGraph's Real Value Is

SnapGraph is not valuable because it is another chat interface or another file archive. Its core value is preserving a recoverable cognitive moment:

- the source text
- why the user saved it
- what open question or unfinished action was alive at that moment
- what graph space or project it belongs to
- what future question would help recover the thought
- what evidence path supports a later answer

The real Qwen upload test made this visible. Compared with MockLLM, Qwen produced much better summaries, more specific open loops, and future recall questions that actually sounded useful. For example, the `金针` material was summarized as a design memo about moving from silent upload to a visible, traceable capture receipt.

This means the strongest product promise is:

> SnapGraph lets users recover not only what they saved, but why it mattered and how it can be used next.

That is a sharper value proposition than "AI knowledge base", "GraphRAG", or "chat with files".

## What Worked

The ingestion pipeline is conceptually strong.

When I uploaded the three real Qwen materials, each source preserved the user-stated reason, extracted open loops, generated future recall questions, entered the graph, and exposed evidence cards through focus graph payloads. This proves the core architecture is pointing in the right direction.

The real provider status is now honest.

Earlier testing showed the UI could look like Qwen was configured while ingestion and ask fell back to mock. After configuration, `/api/config` and answer metadata now correctly show real Qwen readiness and `fallback_used=false`.

The system can recover explicit markers.

Queries for `金针测试-20260603`, `银线测试-20260603`, and `铜镜测试-20260603` all retrieved relevant materials and produced useful synthesis. This is important because users often remember fragments, not exact filenames.

The graph model creates real evidence objects.

For the `金针` material, `/api/focus` returned source, thought, open-loop task nodes, evidence edges, and evidence cards. That is the right foundation for a trustworthy recall product.

## What Still Feels Wrong As A User

The most important gap is current-batch memory.

After uploading three related files, the natural user question is: "combine the materials I just uploaded." SnapGraph still treats this as global retrieval. In the `combine_recent` test, it retrieved the three new files, but also mixed in older materials such as screenshots and earlier mock test files. The answer was smart enough to recover the intended conclusion, but the retrieval layer did not understand "刚才上传的三份材料" as a first-class context.

This makes the product feel forgetful even when retrieval is technically working.

The capture receipt is still not strong enough.

The backend knows the right things: source, summary, why, open loops, graph space, future questions. But the user needs an immediate first-screen receipt that says:

- saved source
- user-stated reason
- AI-inferred context
- graph placement
- evidence path
- one next action
- what is uncertain

Without that, upload feels like a normal file drop, not the distinct SnapGraph experience.

The answer layout is still too report-like.

Real Qwen answers are rich, but they often lead with `## 找回的原话` and material lists. For trust, that is good; for usability, it is backwards. The user usually wants the answer first, then evidence, then uncertainty. The `铜镜` material says exactly this: answer-first, evidence-second, uncertainty-third.

The UI should not make users read a retrieval report before receiving the useful conclusion.

The graph space state has a consistency problem.

API detail says the new sources are in `Default`, and focus graph nodes also use `graph_space_id=default`. But the generated wiki source frontmatter still says `graph_space_id: inbox`. That makes traceability feel fragile: one layer says "Default", another preserved artifact says "Inbox".

Pending suggestions accumulate without product meaning.

There are 9 pending route suggestions, mostly old items recommending `Default`. As a user, this becomes administrative noise unless suggestions are tied to an obvious review workflow or batched cleanup action.

Latency is noticeable.

Real ask calls took about 26-28 seconds each. That may be acceptable for deep recall, but the UI needs progress states that explain what is happening: retrieving sources, building evidence paths, calling provider, synthesizing answer. Otherwise users may interpret latency as failure.

## What Users Care About More Than We Currently Admit

Users care less about graph sophistication at first and more about proof.

They want to know:

- Did SnapGraph really save what I meant?
- Can I see my own reason again?
- Did it preserve source traceability?
- Can I ask "why did I save this?" later?
- Can it combine the things I just uploaded?
- Can I trust which parts are user-stated vs AI-inferred?

The graph is valuable only after those questions are answered. If the graph appears too early as a professional workbench, it can feel like complexity before value.

Users also care about recency and session context.

In normal human interaction, "刚才上传的三份材料" is not a search query; it is a conversation context. SnapGraph currently handles it as search. This is the biggest mismatch between product promise and lived UX.

## Priority Roadmap

### P0: Make The Core Promise Felt

1. Build a true capture receipt.

After ingest, show a receipt with source, user-stated reason, AI-inferred context, graph space, open loops, future question, evidence path, and provider status. This should be the main success state, not a secondary detail.

2. Add current-batch context.

Every upload session should create a temporary batch object. Ask should be able to resolve "刚才上传的", "这三份", "这批材料", and "刚才那几个文件" before global retrieval. This can be stored as local session state first, then later as graph nodes.

3. Change answer layout to answer-first.

Default response should be:

- direct conclusion
- evidence cards and user-stated quotes
- graph paths
- uncertainty / missing evidence
- next action

The evidence should remain inspectable, but it should not bury the answer.

4. Fix graph-space metadata consistency.

When routing moves a source from Inbox to Default, update or clearly annotate the wiki frontmatter. Raw source immutability must be preserved, but generated wiki metadata should not contradict the database.

### P1: Reduce Product Friction

5. Add provider truth UI.

Always show whether the answer used real Qwen, mock fallback, or no provider. This should appear near the answer and in settings. It matters for trust.

6. Turn pending suggestions into a review queue.

Group route suggestions by confidence and age. Let users accept all obvious Default suggestions, reject low-confidence ones, or defer. Do not leave stale suggestions as silent clutter.

7. Improve progress states.

Real Qwen is slow enough that the UI should show stages:

- extracting source
- generating cognitive context
- placing in graph
- retrieving evidence
- synthesizing answer

### P2: Make The Graph Powerful After Trust Exists

8. Add batch nodes and evidence paths.

Once current-batch context works in session memory, make it graph-visible:

- Batch: `20260603 real Qwen UX test`
- contains three sources
- has shared purpose
- has emergent open loop

9. Build a simplified graph overview before professional workbench.

Most users need "what is growing here?" before they need edge editing. Keep the graph workbench, but make the default view an evidence-oriented map of projects, open loops, and recent materials.

10. Add evaluation mode.

Because SnapGraph's promise is subtle, the product should include an evaluation/debug panel that shows:

- query terms
- selected sources
- why each source was retrieved
- graph expansion truncation
- user-stated vs AI-inferred ratio

This already exists in diagnostics; it needs a product surface.

## Design Direction

The product should feel like a quiet cognitive workspace, not a dashboard and not a chatbot clone.

The current StudyAgent-style frontend migration is directionally right: warm paper background, restrained sidebar, simple chat-first surface. But SnapGraph's unique layer should be the receipt and evidence design, not decorative graph visuals.

The first-run flow should be:

1. User drops or pastes material.
2. User writes why it mattered.
3. SnapGraph returns a memory receipt.
4. User can ask a natural follow-up immediately.
5. Answer leads with a conclusion, then shows evidence and uncertainty.

If that flow feels excellent, the graph becomes meaningful. If that flow is weak, the graph looks like extra complexity.

## Bottom Line

SnapGraph already has the right underlying architecture: immutable sources, generated wiki pages, cognitive context, graph edges, evidence cards, and provider abstraction. The real Qwen test proves that the model layer can make the experience much richer than MockLLM.

The product gap is not "more AI" or "more graph". The product gap is making the cognitive promise visible at the exact moments users need reassurance:

- right after saving
- right after asking
- right after uploading several related materials

The next best version should be built around three words: receipt, batch, evidence.
