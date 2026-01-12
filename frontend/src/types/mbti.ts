/**
 * MBTI 相关类型定义和工具函数
 */

import { MBTIType } from './domain'

// ==================== MBTI 人格描述 ====================

export interface MBTIProfile {
  type: MBTIType
  name: string
  description: string
  strengths: string[]
  weaknesses: string[]
  communicationStyle: string
  socialTips: string[]
}

// ==================== MBTI 详细资料 ====================

export const MBTIProfiles: Record<MBTIType, MBTIProfile> = {
  [MBTIType.INTJ]: {
    type: MBTIType.INTJ,
    name: '建筑师',
    description: '富有想象力和战略性的思想家，一切皆在计划之中。',
    strengths: ['战略思维', '独立自主', '高效执行', '追求完美'],
    weaknesses: ['过于理性', '不善表达情感', '完美主义', '社交疲惫'],
    communicationStyle: '直接、理性、目标导向',
    socialTips: ['多使用具体数据和逻辑', '给予独处空间', '尊重个人边界', '避免过度情绪化'],
  },
  [MBTIType.INTP]: {
    type: MBTIType.INTP,
    name: '逻辑学家',
    description: '具有创新思维的发明家，对知识有着难以止息的渴望。',
    strengths: ['逻辑分析', '创新能力', '开放思维', '好奇心强'],
    weaknesses: ['拖延倾向', '社交疲惫', '过于理论化', '忽视情感'],
    communicationStyle: '分析性、探索性、追求真理',
    socialTips: ['给予思考时间', '理性辩论', '尊重独特观点', '避免强迫社交'],
  },
  [MBTIType.ENTJ]: {
    type: MBTIType.ENTJ,
    name: '指挥官',
    description: '大胆、富有想象力且意志强大的领导者，总能找到或创造解决方法。',
    strengths: ['领导能力', '果断决策', '战略规划', '高效沟通'],
    weaknesses: ['过于强势', '缺乏耐心', '忽视他人感受', '工作狂倾向'],
    communicationStyle: '直接、自信、目标驱动',
    socialTips: ['直接表达诉求', '展示逻辑性', '尊重其时间', '提供具体方案'],
  },
  [MBTIType.ENTP]: {
    type: MBTIType.ENTP,
    name: '辩论家',
    description: '聪明好奇的思想家，能够挑战任何观点。',
    strengths: ['辩论能力', '创新思维', '适应能力', '幽默风趣'],
    weaknesses: ['好争论', '不够专注', '忽视细节', '挑战权威'],
    communicationStyle: '辩证性、创新性、挑战性',
    socialTips: ['准备好辩论', '保持开放心态', '提供新观点', '接受挑战'],
  },
  [MBTIType.INFJ]: {
    type: MBTIType.INFJ,
    name: '提倡者',
    description: '安静而神秘，却鼓舞人心且不知疲倦的理想主义者。',
    strengths: ['洞察力强', '同理心', '理想主义', '坚定信念'],
    weaknesses: ['过度敏感', '易疲惫', '完美主义', '难以拒绝'],
    communicationStyle: '深度交流、共情理解、价值导向',
    socialTips: ['真诚交流', '尊重其价值观', '给予情感支持', '避免肤浅社交'],
  },
  [MBTIType.INFP]: {
    type: MBTIType.INFP,
    name: '调停者',
    description: '诗意而善良的利他主义者，总是热切地帮助他人。',
    strengths: ['创造力', '同理心', '真诚善良', '理想主义'],
    weaknesses: ['过于敏感', '逃避冲突', '不切实际', '拖延倾向'],
    communicationStyle: '温和、真诚、情感丰富',
    socialTips: ['温柔表达', '理解其情感', '尊重其价值观', '避免批评'],
  },
  [MBTIType.ENFJ]: {
    type: MBTIType.ENFJ,
    name: '主人公',
    description: '有魅力且鼓舞人心的领袖，能够使听众着迷。',
    strengths: ['领导魅力', '共情能力', '沟通技巧', '鼓舞他人'],
    weaknesses: ['过度关注他人', '忽视自身需求', '过于理想化', '易疲惫'],
    communicationStyle: '热情、鼓舞性、以人为本',
    socialTips: ['表达感激', '展现真诚', '支持其理想', '给予肯定'],
  },
  [MBTIType.ENFP]: {
    type: MBTIType.ENFP,
    name: '竞选者',
    description: '热情、有创造力且社交能力强的自由精神，总能找到理由微笑。',
    strengths: ['热情活力', '创造力', '社交能力', '适应能力'],
    weaknesses: ['注意力分散', '缺乏纪律', '过于理想化', '情绪波动'],
    communicationStyle: '热情、创新、富有感染力',
    socialTips: ['保持活力', '鼓励创新', '给予自由空间', '避免过度约束'],
  },
  [MBTIType.ISTJ]: {
    type: MBTIType.ISTJ,
    name: '物流师',
    description: '务实且注重事实的个体，可靠性毋庸置疑。',
    strengths: ['责任心强', '注重细节', '遵守规则', '可靠稳定'],
    weaknesses: ['固执保守', '缺乏灵活性', '过于严肃', '忽视情感'],
    communicationStyle: '事实性、结构化、可靠性',
    socialTips: ['尊重规则', '提供具体信息', '守时守信', '避免突然变化'],
  },
  [MBTIType.ISFJ]: {
    type: MBTIType.ISFJ,
    name: '守卫者',
    description: '非常专注而温暖的守护者，时刻准备保护所爱之人。',
    strengths: ['细心体贴', '责任心强', '忠诚可靠', '实用主义'],
    weaknesses: ['过度付出', '不善拒绝', '抗拒变化', '忽视自身需求'],
    communicationStyle: '温暖、支持性、细致入微',
    socialTips: ['表达感激', '尊重其付出', '给予安全感', '避免批评'],
  },
  [MBTIType.ESTJ]: {
    type: MBTIType.ESTJ,
    name: '总经理',
    description: '出色的管理者，在管理事务或人员方面无人能及。',
    strengths: ['组织能力', '执行力强', '务实高效', '责任心强'],
    weaknesses: ['固执己见', '缺乏灵活性', '过于强势', '忽视情感'],
    communicationStyle: '直接、权威性、任务导向',
    socialTips: ['直接明确', '尊重其权威', '按时完成', '提供具体方案'],
  },
  [MBTIType.ESFJ]: {
    type: MBTIType.ESFJ,
    name: '执政官',
    description: '极度关心他人且善于社交的人，总是渴望提供帮助。',
    strengths: ['社交能力', '热情友好', '组织能力', '关注他人'],
    weaknesses: ['过度在意他人看法', '回避冲突', '缺乏灵活性', '易受伤害'],
    communicationStyle: '热情、支持性、以人为本',
    socialTips: ['表达感激', '给予肯定', '积极反馈', '参与社交'],
  },
  [MBTIType.ISTP]: {
    type: MBTIType.ISTP,
    name: '鉴赏家',
    description: '大胆而务实的实验者，擅长使用各种工具。',
    strengths: ['动手能力', '逻辑思维', '独立自主', '灵活应变'],
    weaknesses: ['冷漠疏离', '风险偏好', '不善表达', '缺乏规划'],
    communicationStyle: '简洁、务实、行动导向',
    socialTips: ['给予自由空间', '尊重独立性', '避免过度情感', '实际行动'],
  },
  [MBTIType.ISFP]: {
    type: MBTIType.ISFP,
    name: '探险家',
    description: '灵活而有魅力的艺术家，时刻准备探索和体验新事物。',
    strengths: ['艺术感知', '温和友善', '适应能力', '活在当下'],
    weaknesses: ['过于敏感', '逃避冲突', '缺乏规划', '易受影响'],
    communicationStyle: '温和、真实、感性',
    socialTips: ['给予自由', '尊重其感受', '避免批评', '欣赏其创造力'],
  },
  [MBTIType.ESTP]: {
    type: MBTIType.ESTP,
    name: '企业家',
    description: '聪明、充满活力且善于感知的人，真正享受生活在边缘。',
    strengths: ['行动力强', '社交能力', '适应能力', '务实高效'],
    weaknesses: ['冲动鲁莽', '不善规划', '忽视规则', '缺乏耐心'],
    communicationStyle: '直接、活力、行动导向',
    socialTips: ['快速响应', '直接明确', '给予挑战', '避免长篇大论'],
  },
  [MBTIType.ESFP]: {
    type: MBTIType.ESFP,
    name: '表演者',
    description: '自发的、充满活力的娱乐者，生活在他们周围从不无聊。',
    strengths: ['热情活力', '社交天赋', '乐观积极', '享受当下'],
    weaknesses: ['注意力分散', '缺乏规划', '易受影响', '逃避冲突'],
    communicationStyle: '热情、生动、富有感染力',
    socialTips: ['保持活力', '给予赞美', '参与娱乐', '避免严肃批评'],
  },
}

// ==================== MBTI 工具函数 ====================

/**
 * 获取 MBTI 详细资料
 */
export function getMBTIProfile(type: MBTIType): MBTIProfile {
  return MBTIProfiles[type]
}

/**
 * 获取所有 MBTI 类型列表
 */
export function getAllMBTITypes(): MBTIType[] {
  return Object.values(MBTIType)
}

/**
 * 验证 MBTI 类型是否有效
 */
export function isValidMBTI(type: string): type is MBTIType {
  return Object.values(MBTIType).includes(type as MBTIType)
}
