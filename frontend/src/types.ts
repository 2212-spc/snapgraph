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
  runtime?: { model_used?: string }
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
  routing_status?: string
  routing_reason?: string
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

export type AskResponse = {
  question: string
  text: string
  contexts: EvidenceCard[]
  graph_paths: string[]
  focus_graph: FocusGraph
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
  provider?: { provider_used?: string; fallback_used?: boolean }
}

export type GraphPayload = {
  nodes: Array<{ id: string; type: string; label: string; graph_space_id?: string; status?: string }>
  edges: Array<{ id: string; source: string; target: string; relation: string; evidence_source_id?: string }>
  node_count?: number
  edge_count?: number
  insights?: Record<string, unknown>
}

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
