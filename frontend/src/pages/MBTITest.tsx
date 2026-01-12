import React, { useState } from 'react'
import { Typography, Card, Button, message, Space } from 'antd'
import { useNavigate } from 'react-router-dom'
import MbtiQuiz from '../components/MbtiQuiz'
import MbtiResult from '../components/MbtiResult'
import { getAllQuestions } from '../data/mbtiQuestions'
import { calculateMBTIFromQuiz } from '../utils/mbtiCalculator'
import type { MBTITestResult } from '../utils/mbtiCalculator'
import { useSnapshot } from 'valtio'
import { userStore } from '../store/userStore'

const { Title, Paragraph } = Typography

type TestStage = 'intro' | 'quiz' | 'result'

const MBTITest: React.FC = () => {
  const navigate = useNavigate()
  const userSnap = useSnapshot(userStore)
  
  const [stage, setStage] = useState<TestStage>('intro')
  const [testResult, setTestResult] = useState<MBTITestResult | null>(null)

  /**
   * 开始测试
   */
  const handleStartTest = () => {
    setStage('quiz')
  }

  /**
   * 完成测试
   */
  const handleCompleteTest = (selectedOptions: number[]) => {
    const questions = getAllQuestions()
    const result = calculateMBTIFromQuiz(questions, selectedOptions)
    setTestResult(result)
    setStage('result')
    message.success('测试完成！')
  }

  /**
   * 重新测试
   */
  const handleRetake = () => {
    setTestResult(null)
    setStage('quiz')
  }

  /**
   * 保存结果
   */
  const handleSave = async () => {
    if (!testResult) return

    // 保存到用户 store
    userStore.mbti = testResult.type

    // 如果在 Electron 环境，保存到本地配置
    if (window.electron) {
      try {
        await window.electron.setConfig('mbti', testResult.type)
        message.success('MBTI 类型已保存！')
      } catch (error) {
        console.error('保存配置失败:', error)
        message.error('保存失败，请稍后再试')
      }
    } else {
      message.success('MBTI 类型已保存！')
    }

    // 跳转到主页
    setTimeout(() => {
      navigate('/')
    }, 1000)
  }

  /**
   * 取消测试
   */
  const handleCancel = () => {
    setStage('intro')
    setTestResult(null)
  }

  return (
    <div className="page-container">
      {stage === 'intro' && (
        <>
          <Title level={2}>MBTI 人格测试</Title>
          <Paragraph style={{ fontSize: 16 }}>
            通过 10 题快速测试，深入了解你的性格特质、沟通风格和潜在优势。
            测试结果将帮助 Resona 更精准地为你生成符合你真实人格的高情商回复。
          </Paragraph>

          <Card title="测试说明" style={{ marginBottom: 20 }}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Paragraph>
                ✅ <strong>快速：</strong>仅需 10 道题，3-5 分钟完成<br />
                ✅ <strong>准确：</strong>基于经典 MBTI 理论设计<br />
                ✅ <strong>实用：</strong>测试结果直接用于生成个性化回复<br />
                ✅ <strong>隐私：</strong>所有数据仅保存在本地，不上传服务器
              </Paragraph>
              <Paragraph type="secondary">
                💡 <strong>提示：</strong>请根据真实感受作答，没有对错之分。选择最符合你日常表现的选项，而非你期望成为的样子。
              </Paragraph>
              {userSnap.mbti && (
                <Paragraph>
                  当前 MBTI 类型：<strong>{userSnap.mbti}</strong>（可通过重新测试修改）
                </Paragraph>
              )}
              <Button type="primary" size="large" block onClick={handleStartTest}>
                开始测试
              </Button>
            </Space>
          </Card>

          <Card title="MBTI 是什么？">
            <Paragraph>
              MBTI (Myers-Briggs Type Indicator) 是一种基于荣格心理学理论的人格分类工具，
              通过 4 个维度（外向/内向、直觉/感觉、思考/情感、判断/感知）将人格分为 16 种类型。
            </Paragraph>
            <Paragraph>
              <strong>维度说明：</strong>
              <ul>
                <li><strong>E/I (外向/内向):</strong> 能量来源 - 外部世界 vs 内心世界</li>
                <li><strong>N/S (直觉/感觉):</strong> 信息获取 - 整体可能性 vs 具体事实</li>
                <li><strong>F/T (情感/思考):</strong> 决策方式 - 价值观情感 vs 逻辑分析</li>
                <li><strong>J/P (判断/感知):</strong> 生活方式 - 计划结构 vs 灵活自发</li>
              </ul>
            </Paragraph>
          </Card>
        </>
      )}

      {stage === 'quiz' && (
        <>
          <Title level={2}>MBTI 人格测试</Title>
          <Paragraph style={{ textAlign: 'center', fontSize: 16, marginBottom: 20 }}>
            请根据你的真实感受选择最符合的选项
          </Paragraph>
          <MbtiQuiz onComplete={handleCompleteTest} onCancel={handleCancel} />
        </>
      )}

      {stage === 'result' && testResult && (
        <>
          <Title level={2}>测试结果</Title>
          <Paragraph style={{ textAlign: 'center', fontSize: 16, marginBottom: 20 }}>
            恭喜完成测试！以下是你的 MBTI 人格分析
          </Paragraph>
          <MbtiResult result={testResult} onRetake={handleRetake} onSave={handleSave} />
        </>
      )}
    </div>
  )
}

export default MBTITest
