// API 类型定义（与 Backend Schemas 对应）

export type MBTIType = 
  | 'INTJ' | 'INTP' | 'ENTJ' | 'ENTP'
  | 'INFJ' | 'INFP' | 'ENFJ' | 'ENFP'
  | 'ISTJ' | 'ISFJ' | 'ESTJ' | 'ESFJ'
  | 'ISTP' | 'ISFP' | 'ESTP' | 'ESFP'

export type ScenarioType = 'workplace' | 'intimate' | 'family' | 'friendship' | 'social'

export type IntentType = 'refuse' | 'apologize' | 'request' | 'boundary' | 'comfort' | 'explain' | 'gratitude' | 'clarify'

export type ReplyStyle = 'mature' | 'gentle' | 'firm' | 'humorous' | 'rational' | 'empathetic'

export type RiskLevel = 'safe' | 'low' | 'medium' | 'high'

export type RiskType = 'pua' | 'scam' | 'emotional_blackmail' | 'gaslighting' | 'none'

export interface ReplyGenerateRequest {
  dialogue: string
  mbti: MBTIType
  scenario: ScenarioType
  intent: IntentType
  context?: string
}

export interface ReplyOption {
  content: string
  style: ReplyStyle
  confidence: number
}

export interface RiskWarning {
  level: RiskLevel
  type: RiskType
  reason: string
  keywords: string[]
  suggestion?: string
}

export interface ReplyGenerateResponse {
  replies: ReplyOption[]
  risk_warning?: RiskWarning
  request_id: string
}

export interface UserProfileRequest {
  user_id: string
  mbti: MBTIType
}

export interface UserProfileResponse {
  user_id: string
  mbti: MBTIType
  created_at?: string
  updated_at?: string
}

export interface HealthCheckResponse {
  status: string
  version: string
  timestamp: string
}
