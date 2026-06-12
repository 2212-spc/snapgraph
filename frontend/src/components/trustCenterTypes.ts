import type { GraphSpace } from '../types'

export type TrustRiskLevel = 'critical' | 'high' | 'medium' | 'low'
export type TrustReviewStatus = 'unreviewed' | 'confirmed' | 'rewritten' | 'rejected' | 'deferred'
export type TrustOpenLoopState = 'active' | 'next' | 'resolved' | 'dismissed'
export type TrustReviewSessionMode = 'high-risk' | 'quick-clear' | 'open-loops' | 'all'

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

export type TrustDecisionOption = {
  action: Exclude<TrustReviewStatus, 'unreviewed'>
  label: string
  tone: 'positive' | 'constructive' | 'danger' | 'neutral'
  description: string
  requires_note: boolean
  requires_rewrite: boolean
}

export type TrustReviewFocus = {
  headline: string
  detail: string
  primary_action: string
  evidence_prompt: string
}

export type TrustSignals = {
  risk_level: TrustRiskLevel
  confidence: number
  confidence_percent: number
  boundary: string
  review_status: TrustReviewStatus
  evidence_count: number
  topic_count: number
  open_loop_count: number
  future_question_count: number
  has_open_loops: boolean
  has_review_note: boolean
  needs_user_decision: boolean
}

export type TrustRuleMatch = {
  rule_id: string
  dimension: string
  title: string
  severity: TrustRiskLevel
  weight: number
  match_key: string
  match_value: string
  plain_language: string
  user_question: string
  recommended_action: string
  evidence_prompt: string
  reduces_pressure: boolean
}

export type TrustScore = {
  score: number
  label: string
  drivers: string[]
  score_parts: {
    confidence: number
    evidence: number
    open_loops: number
    history: number
    boundary: string
    status: TrustReviewStatus
  }
}

export type TrustSignalProfile = {
  boundary: string
  status: TrustReviewStatus
  risk: TrustRiskLevel
  confidence: number
  confidence_band: string
  evidence_count: number
  evidence_band: string
  open_loop_count: number
  loop_band: string
  topic_count: number
  topic_band: string
  future_question_count: number
  future_band: string
  history_count: number
  history_band: string
  relation_counts: Record<string, number>
  has_review_note: boolean
  has_user_reason: boolean
  needs_user_decision: boolean
  is_reusable: boolean
  is_blocked: boolean
}

export type TrustEvidenceCompression = {
  summary: string
  supporting: string[]
  insufficient: string[]
  needs_confirmation: string[]
  supporting_count: number
  insufficient_count: number
  needs_confirmation_count: number
  path_count: number
  primary_relation: string
  pressure_level: 'low' | 'medium' | 'high'
  collapsed_copy: string
}

export type TrustDecisionPreview = {
  title: string
  tone: 'positive' | 'constructive' | 'danger' | 'neutral'
  summary: string
  recall_effect: string
  graph_effect: string
  open_loop_effect: string
  warnings: string[]
  confirmation_question: string
  next_step: string
  quiet_copy: string
}

export type TrustReviewPathStep = {
  stage: string
  label: string
  instruction: string
  evidence_hint: string
  complete: boolean
  current: boolean
  fallback_action: string
  quiet_copy: string
}

export type TrustReviewPath = {
  current_stage: string
  completion_percent: number
  steps: TrustReviewPathStep[]
  next_instruction: string
}

export type TrustSessionFit = {
  rank: number
  reason: string
  recommended_mode: string
  visible_by_default: boolean
  can_batch: boolean
}

export type TrustImpactMap = {
  future_recall: Array<{ question: string; impact: string }>
  topics: Array<{ topic_id: string; title: string; role: string; impact: string }>
  open_loops: Array<{ text: string; state: string; impact: string }>
  graph: { evidence_count: number; impact: string }
}

export type TrustConflictReview = {
  has_conflict: boolean
  conflicts: string[]
  cautions: string[]
  resolution_prompt: string
  quiet_copy: string
}

export type TrustContextCompleteness = {
  percent: number
  complete: string[]
  missing: string[]
  summary: string
  quiet_copy: string
}

export type TrustAttentionBudget = {
  max_visible_blocks: number
  hidden_blocks: number
  default_disclosure: string
  reason: string
  expand_when: string[]
}

export type TrustEngineAnalysis = {
  source_id: string
  trust_score: TrustScore
  signal_profile: TrustSignalProfile
  matched_rules: TrustRuleMatch[]
  evidence_compression: TrustEvidenceCompression
  decision_preview: Record<Exclude<TrustReviewStatus, 'unreviewed'>, TrustDecisionPreview>
  review_path: TrustReviewPath
  session_fit: TrustSessionFit
  impact_map: TrustImpactMap
  conflict_review: TrustConflictReview
  context_completeness: TrustContextCompleteness
  attention_budget: TrustAttentionBudget
  quiet_summary: string
  recommended_microcopy: {
    badge: string
    primary: string
    secondary: string
    empty: string
  }
  hidden_depth_count: number
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
  risk_reasons: string[]
  decision_options: TrustDecisionOption[]
  review_focus: TrustReviewFocus
  trust_signals: TrustSignals
  evidence_count: number
  topic_refs: TrustTopicRef[]
  has_open_loops: boolean
  needs_review: boolean
  analysis?: TrustEngineAnalysis
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
  session?: TrustSessionPayload
  report?: TrustReportPayload
}

export type TrustSessionPayload = {
  mode: string
  label: string
  intent: string
  filters: TrustReviewFilters
  recommended_source_ids: string[]
  visible_count: number
  total_count: number
  next_step: {
    source_id: string
    title: string
    label: string
    reason: string
    action: string
    risk_level?: TrustRiskLevel
    remaining_after_this?: number
  }
  metrics: Record<string, number>
  mode_options: Array<{
    mode: string
    label: string
    intent: string
    count: number
    quiet_rule: string
  }>
  guardrails: Array<{
    guardrail_id: string
    surface: string
    trigger: string
    max_items: number
    collapsed_label: string
    expansion_label: string
    reason: string
    fallback: string
  }>
  completion_copy: string
  quiet_summary: string
}

export type TrustReportPayload = {
  headline: string
  quiet_summary: string
  filters: TrustReviewFilters
  metrics: Record<string, number>
  risk_register: Record<string, number>
  sections: Array<{
    id: string
    title: string
    priority: number
    count: number
    summary: string
    detail_prompt: string
    quiet_copy: string
    action_label: string
  }>
  action_queue: Array<{
    source_id: string
    title: string
    risk_level: TrustRiskLevel
    review_status: TrustReviewStatus
    recommended_action: string
    summary: string
  }>
  display_policy: {
    default_collapsed: boolean
    max_visible_sections: number
    max_visible_actions: number
    reason: string
  }
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
  analysis?: TrustEngineAnalysis
  report_slice?: {
    source_id: string
    recommended_action: string
    score_label: string
    score: number
    evidence_summary: string
    quiet_summary: string
    primary_preview: string
    collapsed_by_default: boolean
  }
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
