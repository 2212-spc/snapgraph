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
  if (status === 'AI-inferred') return 'AI 猜测'
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

export function decisionActionDescription(action: TrustReviewStatus | string) {
  if (action === 'confirmed') return '这条保存理由是对的，可以继续用于以后找回。'
  if (action === 'rewritten') return '系统猜得不准，我要改成自己的真实理由。'
  if (action === 'rejected') return '这条推断不可靠，以后不要当成我的想法。'
  if (action === 'deferred') return '现在证据不够，先留在队列里以后再判断。'
  return '给这条材料留下一个可追溯的判断。'
}

export function sessionModeLabel(mode: TrustReviewSessionMode) {
  if (mode === 'high-risk') return '先看重点'
  if (mode === 'quick-clear') return '快速清理'
  if (mode === 'open-loops') return '未闭环问题'
  return '全部'
}

export function sessionModeDescription(mode: TrustReviewSessionMode) {
  if (mode === 'high-risk') return '先处理最可能影响回答可信度的 AI 猜测。'
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

export function cleanTrustText(text: string) {
  return (text || '')
    .replace(/^AI-inferred\s*[:：]\s*/i, 'AI 猜测：')
    .replace(/\bAI-inferred\b/g, 'AI 猜测')
    .replace(/\bopen loops?\b/gi, '未闭环问题')
    .replace(/\bDefault\b/g, '主记忆')
    .replace(/\bdefault\b/g, '主记忆')
}

export function trustSpaceLabel(name: string) {
  if (!name) return '未分配空间'
  if (name.toLowerCase() === 'default') return '主记忆'
  if (name.toLowerCase() === 'inbox') return '待整理'
  return name
}
