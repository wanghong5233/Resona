import { useState } from 'react'
import { Card, Button, Space, Typography, Spin, message } from 'antd'
import { apiClient } from '../api/client'
import type { ReplyGenerateRequest, ReplyOption, RiskWarning } from '../types/api'
import { DialogueInput, ScenarioSelector, ReplyCard, RiskAlert } from '../components'
import './Home.css'

const { Title, Text } = Typography

function Home() {
  const [loading, setLoading] = useState(false)
  const [dialogue, setDialogue] = useState('')
  const [mbti, setMbti] = useState<string>('INTJ')
  const [scenario, setScenario] = useState<string>('workplace')
  const [intent, setIntent] = useState<string>('refuse')
  const [replies, setReplies] = useState<ReplyOption[]>([])
  const [riskWarning, setRiskWarning] = useState<RiskWarning | null>(null)

  const handleGenerate = async () => {
    if (!dialogue.trim()) {
      message.warning('请输入对话内容')
      return
    }

    setLoading(true)
    try {
      const request: ReplyGenerateRequest = {
        dialogue,
        mbti: mbti as any,
        scenario: scenario as any,
        intent: intent as any,
      }

      const response = await apiClient.generateReplies(request)
      setReplies(response.data.replies)
      setRiskWarning(response.data.risk_warning || null)
    } catch (error) {
      console.error('生成失败:', error)
      message.error('生成回复失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="home-container">
      <div className="home-header">
        <Title level={2}>Resona - 高情商社交助手</Title>
        <Text type="secondary">基于 MBTI 的智能回复生成</Text>
      </div>

      <div className="home-content">
        {/* 输入区域 */}
        <Card title="对话输入" className="input-card">
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <DialogueInput
              value={dialogue}
              onChange={setDialogue}
              placeholder="请输入对话内容..."
              rows={4}
              disabled={loading}
            />

            <ScenarioSelector
              mbti={mbti}
              scenario={scenario}
              intent={intent}
              onMBTIChange={setMbti}
              onScenarioChange={setScenario}
              onIntentChange={setIntent}
              disabled={loading}
            />

            <Button 
              type="primary" 
              size="large" 
              block 
              onClick={handleGenerate}
              loading={loading}
            >
              生成回复
            </Button>
          </Space>
        </Card>

        {/* 风险预警 */}
        {riskWarning && (
          <RiskAlert 
            warning={riskWarning} 
            onClose={() => setRiskWarning(null)} 
          />
        )}

        {/* 回复列表 */}
        {loading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" tip="正在生成回复..." />
          </div>
        )}

        {!loading && replies.length > 0 && (
          <div className="replies-container">
            {replies.map((reply, index) => (
              <ReplyCard
                key={index}
                reply={reply}
                index={index}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Home
