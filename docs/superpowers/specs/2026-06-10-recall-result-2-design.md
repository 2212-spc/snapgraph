# Recall Result 2.0 Design

## Goal

Recall Result 2.0 upgrades the existing chat answer surface into an evidence-first recovery desk. It does not add a new top-level module. It makes the current Recall result help users answer five design-thinking questions:

- What old judgment did SnapGraph recover?
- Which evidence is strongest?
- What is still AI-inferred or risky?
- What can I do next from this answer?
- What should be saved back into the wiki?

## User Problem

The current result already shows an answer, evidence chain, materials, reflection panel, and next step. The user still has to mentally connect these pieces. From the user's point of view, the missing layer is an explicit decision workflow: understand, verify, act, and preserve.

## Recommended Approach

Add a structured recall projection to the existing ask response and render it in `RecallResult.vue`.

This approach is better than a new dashboard because it appears exactly when the user is evaluating an answer. It is also better than pure frontend parsing because backend projection can use retrieval diagnostics, context status, graph paths, review state, and focus graph data consistently for API, stream, tests, and saved answers.

## Product Behavior

The result page will gain these sections inside the existing Recall view:

1. Judgment brief
   - Short recovered judgment.
   - Evidence confidence label.
   - Counts for user-stated evidence, AI-inferred evidence, graph paths, and open loops.

2. Evidence ladder
   - Primary user-stated anchors first.
   - Supporting sources second.
   - AI-inferred contexts shown as reviewable, not as facts.
   - Graph paths summarized into human-readable evidence steps.

3. Uncertainty and trust debt
   - Shows why the answer may be incomplete.
   - Highlights missing user-stated context, unreviewed AI inference, weak evidence paths, or provider fallback.

4. Action rail
   - Continue asking from the strongest evidence.
   - Review AI-inferred contexts.
   - Close or continue an open loop.
   - Save this answer as a wiki memory.

5. Write-back preview
   - Shows what would be worth saving: judgment, evidence source ids, next step, and review notes.
   - This phase does not add a new save endpoint; it uses the existing `save` ask behavior and UI cues.

## Backend Design

Create `snapgraph/recall_projection.py` with pure functions:

- `build_recall_result_projection(result, provider_metadata, space_id) -> dict`
- `judgment_from_answer_text(text, question) -> dict`
- `evidence_ladder_from_retrieval(retrieval) -> list[dict]`
- `trust_debt_from_retrieval(retrieval, metadata) -> dict`
- `action_cards_from_retrieval(retrieval, question) -> list[dict]`

The projection is deterministic and uses only existing data:

- `AnswerResult.text`
- `RetrievalResult.contexts`
- `RetrievalResult.graph_paths`
- `RetrievalResult.diagnostics`
- provider metadata from ask

No new database table is required.

## API Contract

`POST /api/ask` and `POST /api/ask/stream` final payloads add:

```json
{
  "recall_projection": {
    "judgment": {
      "title": "Recovered judgment",
      "summary": "...",
      "confidence_label": "strong | mixed | weak",
      "source": "answer | fallback"
    },
    "evidence_ladder": [
      {
        "id": "source:<source_id>",
        "kind": "user_anchor | source | ai_inference | graph_path",
        "title": "...",
        "body": "...",
        "source_id": "...",
        "tone": "trusted | support | review | graph"
      }
    ],
    "trust_debt": {
      "level": "low | medium | high",
      "items": [
        {
          "id": "ai-inferred",
          "label": "Unreviewed AI inference",
          "detail": "..."
        }
      ]
    },
    "actions": [
      {
        "id": "ask-primary",
        "kind": "ask | review | save | open_loop",
        "label": "...",
        "question": "...",
        "source_id": "..."
      }
    ],
    "write_back_preview": {
      "judgment": "...",
      "source_ids": ["..."],
      "next_step": "..."
    }
  }
}
```

## Frontend Design

Keep `RecallResult.vue` as the container but split the new result desk into focused child components:

- `RecallJudgmentBrief.vue`
- `RecallEvidenceLadder.vue`
- `RecallTrustDebtPanel.vue`
- `RecallActionRail.vue`
- `RecallWriteBackPreview.vue`

`RecallResult.vue` passes `result.recall_projection` down and keeps existing answer thread, reflection panel, evidence chain, and materials toggles. This limits risk while giving the result page a clearer hierarchy.

## Interaction Rules

- User-stated evidence is visually first and labeled as the strongest anchor.
- AI-inferred evidence is never presented as the user's real intention.
- Risk text must explain what the user can do, not expose internal diagnostics first.
- Actions reuse existing events where possible:
  - follow-up questions emit `askFollowUp`
  - review actions can link the user toward the Trust view later, but this phase does not add routing
  - save action is a UI affordance and can be wired to existing ask save behavior in a later phase if needed

## Error Handling

- If projection is missing, the existing result still renders.
- If no contexts exist, projection shows weak confidence, empty evidence ladder, and a collect-more-materials action.
- If provider fallback happened, trust debt includes a provider fallback item while keeping local evidence visible.

## Testing

Backend:

- Projection produces judgment, evidence ladder, trust debt, actions, and write-back preview for demo data.
- Projection marks AI-inferred contexts as review tone.
- API ask includes `recall_projection`.
- Stream final event includes `recall_projection`.
- Low-confidence/no-context answer returns weak projection.

Frontend:

- Types include `RecallProjection`.
- `RecallResult.vue` renders the new child components.
- Components expose judgment brief, evidence ladder, trust debt, action rail, and write-back preview.
- Styles include stable class names and responsive layout.

## Non-Goals

- No new top-level module.
- No new timeline dashboard.
- No new 3D graph.
- No new provider dependency.
- No new database workflow table.

