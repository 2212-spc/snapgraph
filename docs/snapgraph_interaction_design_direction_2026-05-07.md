# SnapGraph Interaction Design Direction

Last updated: 2026-05-07

This document records the current product/interaction direction after deeper user-centered critique. It should be read before redesigning the frontend.

## Core Decision

SnapGraph should not look like a graph tool, a Notion database, or a generic chatbot.

It should feel like a quiet, premium memory instrument:

- first, it helps users recover past words, sources, and judgments;
- then, it lets users discuss their own material with AI;
- whenever AI says something non-obvious, it can unfold the evidence chain behind that statement.

The graph is not a screen users manage. The graph is the reasoning substrate that makes recall, conversation, and evidence expansion trustworthy.

## Design Philosophy

The visual style must come from the product ethics:

- AI does not pretend to be the user, so user words and AI words must look different.
- Retrieval beats generation, so evidence appears before interpretation.
- The original source is part of the answer, so "open original" is a primary action.
- Emergence is not a task notification. It is a natural line that appears during a high-quality conversation with the user's material.
- User sovereignty matters, so AI-suggested links stay reviewable and never silently become the user's intention.

This means the product should avoid:

- graph-first navigation;
- dashboard metrics such as nodes, edges, confidence percentages, and provider internals;
- sentimental memory-diary language;
- decorative AI-glow aesthetics;
- forcing users to choose technical modes before they ask a question.

## Recommended Surface

The best direction is a hybrid:

1. **A-style entry posture**: a calm, centered recall input, close to Google/Raycast in clarity.
2. **C-style depth**: when the user wants to discuss, the product becomes a conversation with embedded evidence, closer to Claude artifacts than plain chat.
3. **B-style structure only after need appears**: recent captures, spaces, and review states exist, but do not dominate the first screen.

Pure A is too empty and hides why SnapGraph is different. Pure B becomes another knowledge manager. Pure C looks like another ChatGPT and buries evidence in the transcript.

## Primary Interaction Loop

### 1. Ask

The first screen is a single strong input:

> 问问过去的你

The user should be able to type either:

- "我之前为什么不做协作编辑?"
- "那篇关于 memory layer 的论文在哪?"
- "基于我存的材料，SnapGraph 的核心卖点到底是什么?"

The system should infer whether the user is trying to find something or discuss something. The user can still switch manually, but the UI should not force a technical mode choice up front.

Useful visible affordances:

- local library status, e.g. `本地库 · 312 份材料 · 27 段用户原话`;
- privacy/model status, e.g. `默认先搜本地证据`;
- two soft intent chips: `找回` and `深聊`, not `原话优先 / 证据整理 / AI探索` as the main visual grammar.

### 2. Recover

If the query is a recall task, the result page should answer in this order:

1. found user words, exact and visually privileged;
2. source evidence cards;
3. why this matched;
4. one-click original source opening;
5. optional "continue discussing this" entry.

No-match is a valid answer. If reliable local evidence is missing, SnapGraph should say so and offer next actions instead of generating a plausible answer.

### 3. Discuss

If the query becomes a discussion, the conversation should not look like a normal chatbot.

Every substantial AI claim should be able to expose:

- which user words or sources it used;
- which parts are source-grounded;
- which parts are AI interpretation;
- which links are weak or need confirmation.

The conversation can produce emergent insight, but without theatrical UI. The line should feel natural:

> 我注意到你过去几份材料里反复回到一个点：你不是只想做搜索，而是在保护「当时为什么相信」这件事。要不要看我依据的是哪几段?

The magic is not the sentence itself. The magic is that the user can expand it and see the evidence.

### 4. Expand Evidence

The graph should appear only as "why did you say that?".

The visible form should be a simple evidence chain or side sheet:

- source or user quote;
- relation phrase in natural language;
- supporting or contradicting item;
- open original action;
- confirm/weaken/reject relation when useful.

Do not default to a force-directed graph canvas. Use chain, timeline, or grouped evidence packets first.

### 5. Capture

Capture should be a small, fast sheet or browser-extension popup.

Required behavior:

- show the detected source immediately;
- save even if the user writes no reason;
- ask for one optional user sentence;
- mark missing reason as empty or needs-reason;
- let the user set private status;
- never let AI fill in the user's reason.

Good microcopy:

> 写不出来也没关系，先保存。以后想起来可以补一句。

This lowers capture friction while preserving the product law that only the user can state why something mattered.

## Role Of Review

Review should exist, but it should not be the emotional center of the product.

Confirmed links are useful because they improve future recall and evidence chains. However, "待确认" should feel like maintenance that appears when useful, not a gamified chore and not the place where emergence is supposed to happen.

Best V0 placement:

- inline confirmation in evidence expansion;
- a subtle backlog accessible from the library or top-right status;
- no heavy "go review your graph" first-run experience.

## Visual Direction

Premium SnapGraph should feel modern, quiet, and exact, not nostalgic for its own sake.

Recommended qualities:

- high contrast ink-like typography;
- warm neutral background, but with enough cool gray/blue structure to avoid a beige diary feeling;
- one restrained accent for source/evidence actions;
- serif only for user quotes and original words;
- sans-serif for controls and AI/system text;
- monospace only for timestamps, file types, and anchors;
- 1px dividers, crisp spacing, low-radius panels;
- no decorative gradient blobs, no mystical graph glow.

The aesthetic target is closer to Linear/Raycast/Claude/Zotero with editorial quote treatment, not Notion dashboard, not cyber graph, not sentimental notebook.

## Screens To Prototype Next

Build the frontend prototype around six connected screens:

1. **Home Recall Input**: centered ask box with local library status and subtle recent items.
2. **Recall Result**: exact quote first, source cards, open original, why matched, no-match state.
3. **Evidence Conversation**: chat with embedded evidence cards and grounded/interpretive labels.
4. **Evidence Chain Sheet**: "why did you say that?" shown as a traceable chain, not a graph canvas.
5. **Capture Sheet**: fast save, optional user reason, privacy, source preview.
6. **Library/Space**: durable browsing, filters, ingestion state, missing-reason backlog.

Do not make "graph" one of the default six screens.

## Open Product Questions

- How aggressive should automatic intent detection be before offering "找回 / 深聊" switching?
- What is the exact threshold for saying "no reliable evidence found"?
- How should private materials behave in conversation mode if the user explicitly asks about them?
- How much inline review should be asked before users feel interrupted?
- How should Qwen/live-provider latency be hidden with local-first streaming results?
