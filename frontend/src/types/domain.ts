/**
 * 领域模型类型定义
 * 
 * 与后端 core/enums.py 保持一致
 */

// ==================== MBTI 类型 ====================

export enum MBTIType {
  INTJ = 'INTJ',
  INTP = 'INTP',
  ENTJ = 'ENTJ',
  ENTP = 'ENTP',
  INFJ = 'INFJ',
  INFP = 'INFP',
  ENFJ = 'ENFJ',
  ENFP = 'ENFP',
  ISTJ = 'ISTJ',
  ISFJ = 'ISFJ',
  ESTJ = 'ESTJ',
  ESFJ = 'ESFJ',
  ISTP = 'ISTP',
  ISFP = 'ISFP',
  ESTP = 'ESTP',
  ESFP = 'ESFP',
}

// ==================== 场景类型 ====================

export enum ScenarioType {
  WORKPLACE = 'workplace',      // 职场
  INTIMATE = 'intimate',         // 亲密关系
  FAMILY = 'family',             // 家庭
  SOCIAL = 'social',             // 日常社交
}

// ==================== 意图类型 ====================

export enum IntentType {
  REFUSE = 'refuse',             // 拒绝
  APOLOGIZE = 'apologize',       // 道歉
  REQUEST = 'request',           // 提要求
  BOUNDARY = 'boundary',         // 设定边界
  COMFORT = 'comfort',           // 安抚情绪
  CLARIFY = 'clarify',           // 澄清事实
  NEGOTIATE = 'negotiate',       // 谈判
  COMPLIMENT = 'compliment',     // 赞美
  CRITICIZE = 'criticize',       // 提出批评（建设性）
}

// ==================== 回复风格类型 ====================

export enum ReplyStyle {
  MATURE = 'mature',             // 成熟
  GENTLE = 'gentle',             // 温和
  FIRM = 'firm',                 // 坚定
  EMPATHETIC = 'empathetic',     // 共情
  RATIONAL = 'rational',         // 理性
  WITTY = 'witty',               // 机智
  DIPLOMATIC = 'diplomatic',     // 圆滑
}

// ==================== 风险等级类型 ====================

export enum RiskLevel {
  SAFE = 'safe',                 // 🟢 安全
  LOW = 'low',                   // 🟢 低风险
  MEDIUM = 'medium',             // 🟡 中风险
  HIGH = 'high',                 // 🔴 高风险
}

// ==================== 中文标签映射 ====================

export const MBTILabels: Record<MBTIType, string> = {
  [MBTIType.INTJ]: 'INTJ - 建筑师',
  [MBTIType.INTP]: 'INTP - 逻辑学家',
  [MBTIType.ENTJ]: 'ENTJ - 指挥官',
  [MBTIType.ENTP]: 'ENTP - 辩论家',
  [MBTIType.INFJ]: 'INFJ - 提倡者',
  [MBTIType.INFP]: 'INFP - 调停者',
  [MBTIType.ENFJ]: 'ENFJ - 主人公',
  [MBTIType.ENFP]: 'ENFP - 竞选者',
  [MBTIType.ISTJ]: 'ISTJ - 物流师',
  [MBTIType.ISFJ]: 'ISFJ - 守卫者',
  [MBTIType.ESTJ]: 'ESTJ - 总经理',
  [MBTIType.ESFJ]: 'ESFJ - 执政官',
  [MBTIType.ISTP]: 'ISTP - 鉴赏家',
  [MBTIType.ISFP]: 'ISFP - 探险家',
  [MBTIType.ESTP]: 'ESTP - 企业家',
  [MBTIType.ESFP]: 'ESFP - 表演者',
}

export const ScenarioLabels: Record<ScenarioType, string> = {
  [ScenarioType.WORKPLACE]: '职场',
  [ScenarioType.INTIMATE]: '亲密关系',
  [ScenarioType.FAMILY]: '家庭',
  [ScenarioType.SOCIAL]: '日常社交',
}

export const IntentLabels: Record<IntentType, string> = {
  [IntentType.REFUSE]: '拒绝',
  [IntentType.APOLOGIZE]: '道歉',
  [IntentType.REQUEST]: '提要求',
  [IntentType.BOUNDARY]: '设定边界',
  [IntentType.COMFORT]: '安抚情绪',
  [IntentType.CLARIFY]: '澄清事实',
  [IntentType.NEGOTIATE]: '谈判',
  [IntentType.COMPLIMENT]: '赞美',
  [IntentType.CRITICIZE]: '建设性批评',
}

export const ReplyStyleLabels: Record<ReplyStyle, string> = {
  [ReplyStyle.MATURE]: '成熟',
  [ReplyStyle.GENTLE]: '温和',
  [ReplyStyle.FIRM]: '坚定',
  [ReplyStyle.EMPATHETIC]: '共情',
  [ReplyStyle.RATIONAL]: '理性',
  [ReplyStyle.WITTY]: '机智',
  [ReplyStyle.DIPLOMATIC]: '圆滑',
}

export const RiskLevelLabels: Record<RiskLevel, string> = {
  [RiskLevel.SAFE]: '🟢 安全',
  [RiskLevel.LOW]: '🟢 低风险',
  [RiskLevel.MEDIUM]: '🟡 中风险',
  [RiskLevel.HIGH]: '🔴 高风险',
}
