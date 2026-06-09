export type ReviewQueueItemKind = 'ai-inference' | 'weak-path' | 'route-suggestion' | 'open-loop'

export type ReviewQueueItem = {
  key: string
  kind: ReviewQueueItemKind
  title: string
  detail: string
  signalLabel: string
  stageLabel: string
  tone: string
  validationQuestion: string
  sourceId?: string
  confidenceLabel?: string
  reviewStatus?: string
  reviewNote?: string
  originalWhySaved?: string
}

export type ReviewDecisionPayload = {
  sourceId: string
  review_status: 'confirmed' | 'rewritten' | 'rejected' | 'deferred'
  review_note?: string
  why_saved?: string
}
