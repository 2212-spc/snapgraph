import type {
  TrustReviewSessionMode,
  TrustReviewStatus,
  TrustRiskLevel,
} from './trustCenterTypes'

export function riskToneLabel(level: TrustRiskLevel) {
  if (level === 'critical') return '必须先看'
  if (level === 'high') return '高优先级'
  if (level === 'medium') return '需要复核'
  return '低压力'
}

export function boundaryLabel(status: string) {
  if (status === 'user-stated') return '用户原话'
  if (status === 'AI-inferred') return 'AI 推断'
  return status || '边界未知'
}

export function reviewStatusLabel(status: TrustReviewStatus | string) {
  if (status === 'unreviewed') return '未审查'
  if (status === 'confirmed') return '已确认'
  if (status === 'rewritten') return '已改写'
  if (status === 'rejected') return '已拒绝'
  if (status === 'deferred') return '稍后处理'
  return status || '未审查'
}

export function decisionActionLabel(action: TrustReviewStatus | string) {
  if (action === 'confirmed') return '确认'
  if (action === 'rewritten') return '改写'
  if (action === 'rejected') return '拒绝'
  if (action === 'deferred') return '稍后'
  return reviewStatusLabel(action)
}

export function sessionModeLabel(mode: TrustReviewSessionMode) {
  if (mode === 'high-risk') return '高风险优先'
  if (mode === 'quick-clear') return '快速清理'
  if (mode === 'open-loops') return 'Open loop'
  return '全部'
}

export function sessionModeDescription(mode: TrustReviewSessionMode) {
  if (mode === 'high-risk') return '先处理最可能影响回答可信度的 AI 推断。'
  if (mode === 'quick-clear') return '优先扫掉低压力项目，减少队列噪音。'
  if (mode === 'open-loops') return '把悬而未决的问题整理成下一步。'
  return '保留完整队列，适合做系统性检查。'
}

export function confidenceLabel(confidence: number) {
  const value = Math.round((Number.isFinite(confidence) ? confidence : 0) * 100)
  if (value >= 80) return `${value}% 稳定`
  if (value >= 55) return `${value}% 需确认`
  return `${value}% 不稳`
}

export function shortTrustText(text: string, limit = 96) {
  const clean = (text || '').trim()
  if (!clean) return ''
  return clean.length > limit ? `${clean.slice(0, limit)}...` : clean
}
