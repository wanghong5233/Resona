/**
 * MBTI 计算器
 * 
 * 根据问卷答题结果计算 MBTI 类型
 */

import { MBTIType } from '../types/domain'
import type { MBTIQuestion } from '../data/mbtiQuestions'

/**
 * 答题结果
 */
export interface MBTIAnswer {
  questionId: number
  selectedOptionIndex: number
  score: number
}

/**
 * 维度得分
 */
export interface DimensionScore {
  EI: number  // 正数为 E，负数为 I
  NS: number  // 正数为 N，负数为 S
  FT: number  // 正数为 F，负数为 T
  JP: number  // 正数为 J，负数为 P
}

/**
 * 测试结果
 */
export interface MBTITestResult {
  type: MBTIType
  scores: DimensionScore
  confidence: {
    EI: number  // 0-100，表示该维度的确定性
    NS: number
    FT: number
    JP: number
  }
}

/**
 * 计算 MBTI 类型
 * 
 * @param answers 答题结果数组
 * @returns MBTI 测试结果
 */
export function calculateMBTI(answers: MBTIAnswer[]): MBTITestResult {
  // 初始化维度得分
  const scores: DimensionScore = {
    EI: 0,
    NS: 0,
    FT: 0,
    JP: 0
  }
  
  // 统计每个维度的答题数（用于计算置信度）
  const dimensionCounts = {
    EI: 0,
    NS: 0,
    FT: 0,
    JP: 0
  }
  
  // 累加每个维度的得分
  answers.forEach(answer => {
    // 根据问题 ID 判断维度（这里简化处理，实际应该从题库获取）
    // 假设 1-3 题是 EI，4-5 题是 NS，6-8 题是 FT，9-10 题是 JP
    let dimension: keyof DimensionScore
    if (answer.questionId <= 3) {
      dimension = 'EI'
    } else if (answer.questionId <= 5) {
      dimension = 'NS'
    } else if (answer.questionId <= 8) {
      dimension = 'FT'
    } else {
      dimension = 'JP'
    }
    
    scores[dimension] += answer.score
    dimensionCounts[dimension]++
  })
  
  // 确定每个维度的类型
  const typeChars = {
    EI: scores.EI >= 0 ? 'E' : 'I',
    NS: scores.NS >= 0 ? 'N' : 'S',
    FT: scores.FT >= 0 ? 'F' : 'T',
    JP: scores.JP >= 0 ? 'J' : 'P'
  }
  
  // 组合成 MBTI 类型
  const mbtiTypeString = `${typeChars.EI}${typeChars.NS}${typeChars.FT}${typeChars.JP}` as MBTIType
  
  // 计算每个维度的置信度（0-100）
  // 置信度 = |得分| / (题目数 * 最大分值) * 100
  // 假设每题最大分值为 2
  const MAX_SCORE_PER_QUESTION = 2
  
  const confidence = {
    EI: Math.min(100, Math.abs(scores.EI) / (dimensionCounts.EI * MAX_SCORE_PER_QUESTION) * 100),
    NS: Math.min(100, Math.abs(scores.NS) / (dimensionCounts.NS * MAX_SCORE_PER_QUESTION) * 100),
    FT: Math.min(100, Math.abs(scores.FT) / (dimensionCounts.FT * MAX_SCORE_PER_QUESTION) * 100),
    JP: Math.min(100, Math.abs(scores.JP) / (dimensionCounts.JP * MAX_SCORE_PER_QUESTION) * 100)
  }
  
  return {
    type: mbtiTypeString,
    scores,
    confidence
  }
}

/**
 * 从问卷和答案计算 MBTI
 * 
 * @param questions 问卷题目
 * @param selectedOptions 用户选择的选项索引数组
 * @returns MBTI 测试结果
 */
export function calculateMBTIFromQuiz(
  questions: MBTIQuestion[],
  selectedOptions: number[]
): MBTITestResult {
  const answers: MBTIAnswer[] = questions.map((question, index) => {
    const selectedOptionIndex = selectedOptions[index]
    const score = question.options[selectedOptionIndex].score
    
    return {
      questionId: question.id,
      selectedOptionIndex,
      score
    }
  })
  
  return calculateMBTI(answers)
}

/**
 * 获取维度描述
 */
export function getDimensionDescription(dimension: keyof DimensionScore, score: number): string {
  const descriptions = {
    EI: {
      positive: 'E (外向): 你从外部世界获取能量，喜欢社交和表达',
      negative: 'I (内向): 你从内心世界获取能量，喜欢独处和思考'
    },
    NS: {
      positive: 'N (直觉): 你关注整体、未来和可能性，善于抽象思考',
      negative: 'S (感觉): 你关注细节、现在和事实，善于实际操作'
    },
    FT: {
      positive: 'F (情感): 你基于价值观和情感做决策，重视人际和谐',
      negative: 'T (思考): 你基于逻辑和客观标准做决策，重视公平效率'
    },
    JP: {
      positive: 'J (判断): 你喜欢计划和结构，追求确定性和秩序',
      negative: 'P (感知): 你喜欢灵活和自发，保持开放性和适应性'
    }
  }
  
  return score >= 0 ? descriptions[dimension].positive : descriptions[dimension].negative
}
