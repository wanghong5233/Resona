/**
 * MBTI 快速测试题库（10 题）
 * 
 * 每个维度 2-3 题：
 * - E/I (外向/内向): 3 题
 * - N/S (直觉/感觉): 2 题
 * - F/T (情感/思考): 3 题
 * - J/P (判断/感知): 2 题
 */

export interface MBTIQuestion {
  id: number
  dimension: 'EI' | 'NS' | 'FT' | 'JP'
  question: string
  options: {
    text: string
    score: number  // E/N/F/J 为正分，I/S/T/P 为负分
  }[]
}

export const MBTI_QUESTIONS: MBTIQuestion[] = [
  // ==================== E/I 维度 (外向/内向) ====================
  {
    id: 1,
    dimension: 'EI',
    question: '在社交场合中，你更倾向于：',
    options: [
      { text: '主动与陌生人交谈，享受热闹氛围', score: 2 },  // E
      { text: '观察周围，只和熟悉的人交流', score: -2 },  // I
      { text: '看情况，有时主动有时被动', score: 0 }
    ]
  },
  {
    id: 2,
    dimension: 'EI',
    question: '工作或学习一段时间后，你更喜欢：',
    options: [
      { text: '和朋友出去放松，聊天聚餐', score: 2 },  // E
      { text: '独自待着，看书、听音乐或思考', score: -2 },  // I
      { text: '两者都可以，取决于心情', score: 0 }
    ]
  },
  {
    id: 3,
    dimension: 'EI',
    question: '面对新的项目或任务，你倾向于：',
    options: [
      { text: '立刻与团队讨论，集思广益', score: 2 },  // E
      { text: '先独自思考清楚再分享想法', score: -2 },  // I
      { text: '简单讨论后各自思考', score: 0 }
    ]
  },

  // ==================== N/S 维度 (直觉/感觉) ====================
  {
    id: 4,
    dimension: 'NS',
    question: '在解决问题时，你更关注：',
    options: [
      { text: '整体趋势、未来可能性和创新方案', score: 2 },  // N
      { text: '具体细节、现有事实和实际可行性', score: -2 },  // S
      { text: '两者结合，视情况而定', score: 0 }
    ]
  },
  {
    id: 5,
    dimension: 'NS',
    question: '你更喜欢的学习或工作方式是：',
    options: [
      { text: '探索新概念、理论和抽象想法', score: 2 },  // N
      { text: '掌握具体技能、流程和实操经验', score: -2 },  // S
      { text: '理论与实践并重', score: 0 }
    ]
  },

  // ==================== F/T 维度 (情感/思考) ====================
  {
    id: 6,
    dimension: 'FT',
    question: '做决策时，你更看重：',
    options: [
      { text: '对他人的影响、情感和人际和谐', score: 2 },  // F
      { text: '逻辑分析、客观标准和效率', score: -2 },  // T
      { text: '两者都考虑，力求平衡', score: 0 }
    ]
  },
  {
    id: 7,
    dimension: 'FT',
    question: '朋友向你倾诉烦恼时，你通常：',
    options: [
      { text: '给予情感支持和共鸣，让对方感到被理解', score: 2 },  // F
      { text: '分析问题原因，提供解决方案', score: -2 },  // T
      { text: '先倾听，再根据情况决定', score: 0 }
    ]
  },
  {
    id: 8,
    dimension: 'FT',
    question: '评价一个方案时，你更倾向于：',
    options: [
      { text: '考虑团队感受，避免伤害他人', score: 2 },  // F
      { text: '直接指出问题，即使可能显得不近人情', score: -2 },  // T
      { text: '客观评价，但注意表达方式', score: 0 }
    ]
  },

  // ==================== J/P 维度 (判断/感知) ====================
  {
    id: 9,
    dimension: 'JP',
    question: '对于日常生活和工作，你更喜欢：',
    options: [
      { text: '提前规划，按计划执行，喜欢确定性', score: 2 },  // J
      { text: '灵活应变，随机应变，保持开放性', score: -2 },  // P
      { text: '有大致计划，但允许调整', score: 0 }
    ]
  },
  {
    id: 10,
    dimension: 'JP',
    question: '面对截止日期，你通常：',
    options: [
      { text: '提前完成任务，留出检查时间', score: 2 },  // J
      { text: '在截止日期前完成，享受最后的压力', score: -2 },  // P
      { text: '根据任务重要性灵活安排', score: 0 }
    ]
  }
]

/**
 * 获取所有问题
 */
export function getAllQuestions(): MBTIQuestion[] {
  return MBTI_QUESTIONS
}

/**
 * 根据维度获取问题
 */
export function getQuestionsByDimension(dimension: 'EI' | 'NS' | 'FT' | 'JP'): MBTIQuestion[] {
  return MBTI_QUESTIONS.filter(q => q.dimension === dimension)
}
