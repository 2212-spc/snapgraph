import type { GraphSpace } from '../types'

export type TrustRiskLevel = 'critical' | 'high' | 'medium' | 'low'
export type TrustReviewStatus = 'unreviewed' | 'confirmed' | 'rewritten' | 'rejected' | 'deferred'
export type TrustOpenLoopState = 'active' | 'next' | 'resolved' | 'dismissed'

export type TrustReviewFilters = {
  status?: string
  risk?: string
  space_id?: string
  q?: string
  inferred?: string
  has_open_loops?: boolean | null
}

export type TrustTopicRef = {
  topic_id: string
  title: string
  space_id: string
  role: string
}

export type TrustReviewItem = {
  source_id: string
  title: string
  type: string
  imported_at: string
  summary: string
  graph_space_id: string
  space_name: string
  why_saved: string
  why_saved_status: string
  related_project: string
  open_loops: string[]
  future_recall_questions: string[]
  importance: string
  confidence: number
  review_status: TrustReviewStatus
  review_note: string
  reviewed_at: string
  risk_level: TrustRiskLevel
  recommended_action: string
  evidence_count: number
  topic_refs: TrustTopicRef[]
  has_open_loops: boolean
  needs_review: boolean
}

export type TrustSummary = {
  total: number
  critical: number
  high: number
  medium: number
  low: number
  unreviewed: number
  confirmed: number
  rewritten: number
  rejected: number
  deferred: number
  ai_inferred: number
  user_stated: number
  open_loop_items: number
}

export type TrustReviewPayload = {
  items: TrustReviewItem[]
  summary: TrustSummary
  filters: TrustReviewFilters
}

export type TrustEvidencePath = {
  edge_id: string
  source_node_id: string
  source_label: string
  target_node_id: string
  target_label: string
  relation: string
  confidence: number
  status: string
  path: string
}

export type TrustReviewHistoryItem = {
  id: string
  source_id: string
  action: TrustReviewStatus
  previous_status: string
  next_status: string
  note: string
  previous_why_saved: string
  next_why_saved: string
  created_at: string
}

export type TrustSourceMapSummary = {
  source_node_present: boolean
  connected_edges: number
}

export type TrustReviewDetailPayload = {
  item: TrustReviewItem
  evidence_paths: TrustEvidencePath[]
  history: TrustReviewHistoryItem[]
  open_loops: TrustOpenLoopItem[]
  source_map: TrustSourceMapSummary
}

export type TrustOpenLoopItem = {
  loop_id: string
  origin: string
  text: string
  state: TrustOpenLoopState
  note: string
  updated_at: string
  source_ids: string[]
  source_titles: string[]
  risk_level: TrustRiskLevel
  review_status_summary: Record<string, number>
  evidence_count: number
  topic_ids: string[]
  topic_title?: string
}

export type TrustOpenLoopPayload = {
  items: TrustOpenLoopItem[]
  summary: {
    total: number
    by_state: Record<TrustOpenLoopState, number>
    by_risk: Record<TrustRiskLevel, number>
  }
}

export type TrustDiagnostics = {
  queue_total: number
  ai_inferred_unreviewed: number
  critical_count: number
  high_count: number
  deferred_count: number
  rejected_count: number
  history_count: number
  open_loop_total: number
  open_loop_states: Record<string, number>
  orphan_lifecycle_ids: string[]
  warnings: string[]
}

export type TrustBatchPayload = {
  source_ids: string[]
  action: Exclude<TrustReviewStatus, 'unreviewed'>
  note?: string
  rewrites?: Record<string, string>
}

export type TrustOpenLoopUpdatePayload = {
  state: TrustOpenLoopState
  note?: string
}

export type TrustCenterProps = {
  review: TrustReviewPayload
  detail: TrustReviewDetailPayload | null
  openLoops: TrustOpenLoopPayload
  diagnostics: TrustDiagnostics | null
  spaces: GraphSpace[]
  selectedSourceIds: string[]
  filters: TrustReviewFilters
  busy: boolean
}
