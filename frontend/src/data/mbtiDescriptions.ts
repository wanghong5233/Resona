/**
 * MBTI 16 型人格简短描述
 * 
 * 用于测试结果展示
 */

import { MBTIType } from '../types/domain'

export interface MBTIDescription {
  type: MBTIType
  name: string
  nickname: string
  description: string
  strengths: string[]
  weaknesses: string[]
  communicationTips: string[]
}

export const MBTI_DESCRIPTIONS: Record<MBTIType, MBTIDescription> = {
  // ==================== NT 类型（理性者）====================
  [MBTIType.INTJ]: {
    type: MBTIType.INTJ,
    name: '建筑师',
    nickname: '独立思考者',
    description: '富有想象力和战略性的思想家，凡事都有计划。擅长长期规划，追求系统化和高效。',
    strengths: ['战略思维', '独立自主', '逻辑清晰', '追求完美'],
    weaknesses: ['过于理性', '不擅表达情感', '可能显得傲慢'],
    communicationTips: ['多表达感受，而非只讲道理', '倾听他人意见，避免一意孤行', '放慢节奏，给对方思考时间']
  },
  [MBTIType.INTP]: {
    type: MBTIType.INTP,
    name: '逻辑学家',
    nickname: '思想家',
    description: '创新的发明家，对知识有着止不住的渴望。喜欢探索理论，分析复杂问题。',
    strengths: ['分析能力强', '创新思维', '客观公正', '求知欲强'],
    weaknesses: ['社交疏离', '容易钻牛角尖', '执行力弱'],
    communicationTips: ['简化表达，避免过度复杂', '关注实际应用，而非纯理论', '主动参与社交，建立情感连接']
  },
  [MBTIType.ENTJ]: {
    type: MBTIType.ENTJ,
    name: '指挥官',
    nickname: '天生领导者',
    description: '大胆、富有想象力且意志强大的领导者，总能找到或创造解决办法。',
    strengths: ['领导力强', '决策果断', '执行力高', '目标导向'],
    weaknesses: ['过于强势', '不够耐心', '忽视他人感受'],
    communicationTips: ['放慢语速，给对方表达机会', '关注情感需求，而非只讲效率', '适当示弱，建立信任']
  },
  [MBTIType.ENTP]: {
    type: MBTIType.ENTP,
    name: '辩论家',
    nickname: '机智的挑战者',
    description: '聪明好奇的思想家，无法抗拒智力上的挑战。喜欢辩论和创新。',
    strengths: ['思维敏捷', '善于辩论', '创意无限', '适应力强'],
    weaknesses: ['容易争论', '注意力分散', '缺乏耐心'],
    communicationTips: ['控制辩论欲，避免过度挑战', '倾听他人观点，而非急于反驳', '关注执行，而非只出点子']
  },

  // ==================== NF 类型（理想者）====================
  [MBTIType.INFJ]: {
    type: MBTIType.INFJ,
    name: '提倡者',
    nickname: '理想主义者',
    description: '安静而神秘，鼓舞人心且不知疲倦的理想主义者。追求意义和深度。',
    strengths: ['洞察力强', '富有同理心', '理想主义', '坚定信念'],
    weaknesses: ['过度理想化', '容易受伤', '难以妥协'],
    communicationTips: ['接受现实，而非只追求完美', '表达需求，而非默默付出', '设立边界，避免过度共情']
  },
  [MBTIType.INFP]: {
    type: MBTIType.INFP,
    name: '调停者',
    nickname: '治愈者',
    description: '诗意、善良的利他主义者，总是热情地为正义事业而奋斗。内心柔软但坚定。',
    strengths: ['富有创意', '真诚善良', '价值观明确', '适应性强'],
    weaknesses: ['过于敏感', '逃避冲突', '不切实际'],
    communicationTips: ['直面冲突，而非逃避', '表达不满，而非压抑情绪', '关注现实，而非只活在理想中']
  },
  [MBTIType.ENFJ]: {
    type: MBTIType.ENFJ,
    name: '主人公',
    nickname: '教育者',
    description: '有魅力鼓舞人心的领袖，能够使听众着迷。天生的激励者和引导者。',
    strengths: ['感染力强', '善于激励', '组织能力强', '富有同理心'],
    weaknesses: ['过度付出', '难以说不', '忽视自身需求'],
    communicationTips: ['关注自己，而非只顾他人', '学会拒绝，设立边界', '接受不完美，放下控制欲']
  },
  [MBTIType.ENFP]: {
    type: MBTIType.ENFP,
    name: '竞选者',
    nickname: '激励者',
    description: '热情、有创造力和社交能力的自由精神，总能找到理由微笑。充满活力和可能性。',
    strengths: ['热情洋溢', '创意丰富', '社交能力强', '乐观积极'],
    weaknesses: ['注意力分散', '缺乏计划', '情绪波动大'],
    communicationTips: ['控制热情，避免过度承诺', '关注细节，提升执行力', '稳定情绪，避免忽冷忽热']
  },

  // ==================== SJ 类型（守护者）====================
  [MBTIType.ISTJ]: {
    type: MBTIType.ISTJ,
    name: '物流师',
    nickname: '检查员',
    description: '实际且注重事实的个人，可靠性不容怀疑。做事有条理，注重细节。',
    strengths: ['可靠负责', '做事有条理', '注重细节', '执行力强'],
    weaknesses: ['过于刚性', '不擅变通', '情感表达不足'],
    communicationTips: ['灵活应变，而非只按规矩', '表达情感，而非只讲事实', '接受新想法，而非一味拒绝']
  },
  [MBTIType.ISFJ]: {
    type: MBTIType.ISFJ,
    name: '守卫者',
    nickname: '保护者',
    description: '非常专注且温暖的守护者，时刻准备保护爱的人。忠诚可靠，默默付出。',
    strengths: ['细心体贴', '忠诚可靠', '务实稳重', '富有耐心'],
    weaknesses: ['过度付出', '难以拒绝', '抗拒变化'],
    communicationTips: ['表达不满，而非默默忍受', '学会拒绝，而非一味迎合', '接受变化，而非固守传统']
  },
  [MBTIType.ESTJ]: {
    type: MBTIType.ESTJ,
    name: '总经理',
    nickname: '管理者',
    description: '出色的管理者，在管理事情或人的方面无与伦比。做事高效，注重结果。',
    strengths: ['组织能力强', '执行力高', '责任感强', '果断决策'],
    weaknesses: ['过于强势', '不够灵活', '忽视情感'],
    communicationTips: ['放慢节奏，倾听他人意见', '关注情感，而非只讲效率', '适当妥协，而非一味坚持']
  },
  [MBTIType.ESFJ]: {
    type: MBTIType.ESFJ,
    name: '执政官',
    nickname: '照顾者',
    description: '极有同情心、受欢迎的人，总是热心为他人做出贡献。重视和谐，善于维护关系。',
    strengths: ['热心助人', '善于社交', '责任感强', '情感丰富'],
    weaknesses: ['过度在意他人看法', '难以接受批评', '忽视自身需求'],
    communicationTips: ['关注自己，而非只顾他人', '接受批评，而非过度防御', '表达真实想法，而非一味迎合']
  },

  // ==================== SP 类型（艺术家）====================
  [MBTIType.ISTP]: {
    type: MBTIType.ISTP,
    name: '鉴赏家',
    nickname: '手艺人',
    description: '大胆且实际的实验者，擅长使用各种工具。动手能力强，善于解决实际问题。',
    strengths: ['动手能力强', '冷静理性', '适应力强', '独立自主'],
    weaknesses: ['情感表达不足', '容易冲动', '不喜承诺'],
    communicationTips: ['表达情感，而非只讲逻辑', '提前规划，而非完全即兴', '考虑他人感受，而非只顾自己']
  },
  [MBTIType.ISFP]: {
    type: MBTIType.ISFP,
    name: '探险家',
    nickname: '艺术家',
    description: '灵活有魅力的艺术家，时刻准备探索和体验新事物。重视美感和体验。',
    strengths: ['富有创意', '温和友善', '审美能力强', '适应力强'],
    weaknesses: ['过于敏感', '缺乏计划', '难以拒绝'],
    communicationTips: ['表达不满，而非默默忍受', '制定计划，而非完全随性', '面对冲突,而非逃避']
  },
  [MBTIType.ESTP]: {
    type: MBTIType.ESTP,
    name: '企业家',
    nickname: '行动派',
    description: '精力充沛、善于察言观色的冒险者，永远不会拒绝一个挑战。善于抓住机会。',
    strengths: ['行动力强', '应变能力强', '善于观察', '富有魅力'],
    weaknesses: ['缺乏耐心', '容易冲动', '不喜长期规划'],
    communicationTips: ['控制冲动，三思而后行', '关注长远，而非只顾眼前', '倾听他人，而非急于行动']
  },
  [MBTIType.ESFP]: {
    type: MBTIType.ESFP,
    name: '表演者',
    nickname: '娱乐者',
    description: '自发的、充满活力和热情的表演者，周围永远不会无聊。享受当下，感染他人。',
    strengths: ['热情开朗', '善于社交', '乐观积极', '适应力强'],
    weaknesses: ['注意力分散', '缺乏计划', '过度寻求认可'],
    communicationTips: ['控制表现欲，给他人空间', '关注细节，提升执行力', '深入思考，而非浮于表面']
  }
}

/**
 * 获取 MBTI 类型描述
 */
export function getMBTIDescription(type: MBTIType): MBTIDescription {
  return MBTI_DESCRIPTIONS[type]
}

/**
 * 获取所有 MBTI 类型描述
 */
export function getAllMBTIDescriptions(): MBTIDescription[] {
  return Object.values(MBTI_DESCRIPTIONS)
}
