export type WorkspaceState = {
  sources: number
  saved_questions: number
  nodes: number
  edges: number
  lint_status: string
  workspace_path: string
}

export type ProviderConfig = {
  provider: string
  model?: string
  has_api_key?: boolean
  runtime?: {
    configured_provider?: string
    provider_used?: string
    model_used?: string
    api_key_env?: string
    has_api_key?: boolean
    provider_ready?: boolean
    fallback_used?: boolean
    provider_error?: string
  }
}

export type GraphSpace = {
  id: string
  name: string
  description: string
  purpose: string
  color: string
  status: string
  source_count: number
  node_count: number
  edge_count: number
  pending_suggestions: number
  created_at?: string
  updated_at?: string
}

export type Source = {
  id: string
  title: string
  type: string
  imported_at: string
  summary: string
  why_saved: string
  why_saved_status: string
  related_project: string
  open_loops: string[]
  future_recall_questions: string[]
  original_filename: string
  graph_space_id: string
  space_name: string
  confidence?: number
  review_status?: string
  review_note?: string
  reviewed_at?: string
  routing_status?: string
  routing_reason?: string
  path?: string
}

export type EvidenceCard = {
  source_id: string
  title: string
  space_name: string
  why_saved: string
  why_saved_status: string
  related_project: string
  open_loops: string[]
  future_recall_questions: string[]
  source_excerpt: string
  review_status?: string
  review_note?: string
  reviewed_at?: string
}

export type FocusGraph = {
  nodes: Array<{ id: string; type: string; label: string; graph_space_id?: string; status?: string }>
  edges: Array<{ id: string; source: string; target: string; relation: string; evidence_source_id?: string }>
  evidence_cards: EvidenceCard[]
  open_loops: string[]
  confidence_summary: {
    source_count: number
    user_stated: number
    ai_inferred: number
    confidence_label: string
  }
}

export type RecallEvidenceKind = 'user_anchor' | 'source' | 'ai_inference' | 'graph_path'

export type RecallEvidenceTone = 'trusted' | 'support' | 'review' | 'graph'

export type RecallEvidenceItem = {
  id: string
  kind: RecallEvidenceKind
  tone: RecallEvidenceTone
  title: string
  body: string
  source_id: string
  space_name: string
  review_status: string
  metadata?: {
    why_saved_status?: string
    related_project?: string
    open_loops?: string[]
    future_recall_questions?: string[]
    source_page?: string
    path?: string
  }
}

export type RecallTrustDebtItem = {
  id: string
  label: string
  detail: string
  severity: 'low' | 'medium' | 'high'
}

export type RecallActionKind = 'ask' | 'review' | 'save' | 'open_loop' | 'collect'

export type RecallActionCard = {
  id: string
  kind: RecallActionKind
  label: string
  detail: string
  question: string
  source_id: string
  space_id: string
}

export type RecallProjection = {
  judgment: {
    title: string
    summary: string
    confidence_label: 'strong' | 'mixed' | 'weak'
    source: string
    space_id: string
    space_name: string
  }
  evidence_ladder: RecallEvidenceItem[]
  trust_debt: {
    level: 'low' | 'medium' | 'high'
    items: RecallTrustDebtItem[]
    summary: string
  }
  actions: RecallActionCard[]
  write_back_preview: {
    judgment: string
    source_ids: string[]
    next_step: string
    graph_paths: string[]
    diagnostics?: Record<string, unknown>
  }
}

export type AskResponse = {
  question: string
  text: string
  provider?: { provider_used?: string; model_used?: string; fallback_used?: boolean; provider_error?: string }
  contexts: EvidenceCard[]
  graph_paths: string[]
  focus_graph: FocusGraph
  recall_projection?: RecallProjection
  topic?: Topic
  topic_state?: TopicState
  turns?: TopicTurn[]
}

export type RecallStage = {
  id: string
  label: string
  status: 'pending' | 'active' | 'done' | 'error'
  detail?: string
}

export type Suggestion = {
  id: string
  graph_space_id: string
  kind: string
  payload: {
    source_id?: string
    target_space_id?: string
    target_space_name?: string
    alternatives?: Array<{ space_id: string; space_name: string; score: number }>
  }
  reason: string
  confidence: number
  status: string
}

export type SavedQuestion = {
  id: string
  question: string
  path: string
  evidence_source_ids: string[]
}

export type SavedQuestionDetail = SavedQuestion & {
  answer: string
  answer_heading: string
  markdown: string
}

export type TopicEvidence = {
  source_id: string
  title: string
  summary: string
  why_saved: string
  why_saved_status: string
  related_project: string
  open_loops: string[]
  confidence: number
}

export type Topic = {
  id: string
  title: string
  summary: string
  space_id: string
  pinned_source_ids: string[]
  open_loops: string[]
  confirmed_judgments: string[]
  created_at: string
  updated_at: string
}

export type TopicTurn = {
  id: string
  topic_id: string
  question: string
  answer: string
  evidence_source_ids: string[]
  graph_paths: string[]
  created_at: string
}

export type TopicState = {
  topic_id: string
  title: string
  summary: string
  space_id: string
  pinned_source_ids: string[]
  evidence_source_ids: string[]
  open_loops: string[]
  confirmed_judgments: string[]
  evidence: TopicEvidence[]
  user_stated_count: number
  ai_inferred_count: number
  turn_count: number
}

export type TopicPayload = {
  topic: Topic
  turns: TopicTurn[]
  state: TopicState
}

export type IngestResponse = {
  source_id: string
  title: string
  type: string
  summary: string
  status: string
  graph_space_id: string
  space_name: string
  focus_graph: FocusGraph
  routing_suggestion?: Suggestion | null
  warnings?: string[]
  deduplicated?: boolean
  provider?: { provider_used?: string; fallback_used?: boolean }
}

export type GraphPayload = {
  nodes: Array<{
    id: string
    type: string
    label: string
    graph_space_id?: string
    status?: string
    properties?: Record<string, unknown>
  }>
  edges: Array<{
    id: string
    source: string
    target: string
    relation: string
    evidence_source_id?: string
    graph_space_id?: string
    status?: string
    confidence?: number
    evidence_kind?: string
    explanation?: string
    origin?: string
    rejected_reason?: string
    weakened_reason?: string
    hidden_reason?: string
  }>
  node_count?: number
  edge_count?: number
  insights?: GraphInsights
}

export type GraphProjectCluster = {
  project: string
  source_count: number
  user_stated: number
  ai_inferred: number
  average_confidence: number
  sources: Array<{
    source_id: string
    title: string
    status: string
    why_saved?: string
  }>
  open_loops: string[]
  future_questions: string[]
}

export type GraphOpenLoopHotspot = {
  open_loop: string
  count: number
  sources: Array<{
    source_id: string
    title: string
    status: string
  }>
}

export type GraphReviewPath = {
  source_id: string
  title: string
  path: string
  status: string
  confidence: number
  why?: string
}

export type GraphLowConfidenceContext = {
  source_id: string
  title: string
  status: string
  confidence: number
  why_saved: string
}

export type GraphInsights = {
  project_clusters?: GraphProjectCluster[]
  bridge_sources?: Array<Record<string, unknown>>
  open_loop_hotspots?: GraphOpenLoopHotspot[]
  low_confidence_contexts?: GraphLowConfidenceContext[]
  unassigned_sources?: Array<Record<string, unknown>>
  high_value_review_paths?: GraphReviewPath[]
}

export type GraphNode = GraphPayload['nodes'][number]

export type GraphEdge = GraphPayload['edges'][number]

export type GraphLayoutPosition = {
  node_id: string
  x: number
  y: number
  locked?: boolean
}

export type GraphTheme = {
  id: string
  graph_space_id: string
  label: string
  description: string
  member_node_ids: string[]
  origin: string
  status: string
  confidence: number
  reason: string
}

export type GraphInteractionMode = 'arrange' | 'connect' | 'synthesize' | 'prune'

export type GraphViewMode = 'memory' | 'evidence' | 'action'

export type RouteMode = 'auto' | 'manual' | 'inbox'

export type CollectPayload = {
  text: string
  files: File[]
  why: string
  routeMode: RouteMode
  spaceId: string
}

export type ContextUpdatePayload = {
  why_saved: string
  related_project: string
  open_loops: string[]
  confirm: boolean
}

export type SyntheticEdge = {
  id: string
  source: string
  target: string
  relation: string
  confidence: number
  reason: string
}

export type SourceMapEntry = {
  node: GraphNode
  source_detail: {
    id: string
    title: string
    summary: string
    why_saved: string
    why_saved_status: string
    confidence: number
    related_project: string
    open_loops: string[]
    space_name: string
  }
  thought_count: number
  task_count: number
  thought_label_snippet: string
  project_name: string | null
}

export type SourceMapPayload = {
  space_id: string
  sources: SourceMapEntry[]
  synthetic_edges: SyntheticEdge[]
  insights?: GraphInsights
}

export type PathResult = {
  path_nodes: GraphNode[]
  path_edges: GraphEdge[]
  path_description: string
}

export type SubgraphPayload = {
  nodes: GraphNode[]
  edges: GraphEdge[]
}
