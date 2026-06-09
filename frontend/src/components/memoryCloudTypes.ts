export type CloudItemKind = 'question' | 'future' | 'open' | 'source' | 'node'

export type CloudEvidence = {
  id: string
  title: string
}

export type CloudItem = {
  key: string
  kind: CloudItemKind
  kindLabel: string
  label: string
  detail: string
  weight: number
  tone: string
  nodeId?: string
  sourceId?: string
  questionId?: string
  question?: string
  evidenceTitles: CloudEvidence[]
}
