/**
 * MBTI 测试结果展示组件
 * 
 * 显示测试结果、详细描述和社交建议
 */

import React from 'react'
import { Card, Space, Typography, Tag, Progress, Button, Row, Col, Divider } from 'antd'
import { CheckCircleOutlined, TrophyOutlined, WarningOutlined, BulbOutlined } from '@ant-design/icons'
import type { MBTITestResult } from '../utils/mbtiCalculator'
import { getMBTIDescription } from '../data/mbtiDescriptions'
import { getDimensionDescription } from '../utils/mbtiCalculator'
import { MBTILabels } from '../types/domain'

const { Title, Text, Paragraph } = Typography

interface MbtiResultProps {
  result: MBTITestResult
  onRetake?: () => void
  onSave?: () => void
}

const MbtiResult: React.FC<MbtiResultProps> = ({ result, onRetake, onSave }) => {
  const description = getMBTIDescription(result.type)
  
  /**
   * 获取置信度颜色
   */
  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 70) return '#52c41a'  // 绿色 - 高置信度
    if (confidence >= 50) return '#faad14'  // 橙色 - 中等置信度
    return '#ff4d4f'  // 红色 - 低置信度
  }
  
  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* 结果概览 */}
      <Card style={{ textAlign: 'center', marginBottom: 20 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <TrophyOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          <div>
            <Title level={2} style={{ marginBottom: 8 }}>
              {MBTILabels[result.type]}
            </Title>
            <Title level={3} style={{ color: '#666', fontWeight: 'normal', marginTop: 0 }}>
              {description.nickname}
            </Title>
          </div>
          <Tag color="blue" style={{ fontSize: 16, padding: '8px 16px' }}>
            {result.type}
          </Tag>
          <Paragraph style={{ fontSize: 16, color: '#666', maxWidth: 600, margin: '0 auto' }}>
            {description.description}
          </Paragraph>
        </Space>
      </Card>
      
      {/* 维度分析 */}
      <Card title="维度分析" style={{ marginBottom: 20 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {Object.entries(result.scores).map(([dimension, score]) => {
            const confidence = result.confidence[dimension as keyof typeof result.confidence]
            const dimDescription = getDimensionDescription(dimension as keyof typeof result.scores, score)
            
            return (
              <div key={dimension}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text strong>{dimDescription}</Text>
                  <Text type="secondary">置信度: {confidence.toFixed(0)}%</Text>
                </div>
                <Progress
                  percent={confidence}
                  strokeColor={getConfidenceColor(confidence)}
                  showInfo={false}
                />
              </div>
            )
          })}
        </Space>
      </Card>
      
      {/* 详细描述 */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col span={12}>
          <Card
            title={
              <Space>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                <span>优势</span>
              </Space>
            }
          >
            <ul style={{ paddingLeft: 20 }}>
              {description.strengths.map((strength, index) => (
                <li key={index}>
                  <Text>{strength}</Text>
                </li>
              ))}
            </ul>
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title={
              <Space>
                <WarningOutlined style={{ color: '#faad14' }} />
                <span>待改进</span>
              </Space>
            }
          >
            <ul style={{ paddingLeft: 20 }}>
              {description.weaknesses.map((weakness, index) => (
                <li key={index}>
                  <Text>{weakness}</Text>
                </li>
              ))}
            </ul>
          </Card>
        </Col>
      </Row>
      
      {/* 社交建议 */}
      <Card
        title={
          <Space>
            <BulbOutlined style={{ color: '#1890ff' }} />
            <span>高情商社交建议</span>
          </Space>
        }
        style={{ marginBottom: 20 }}
      >
        <Paragraph>
          基于你的 {result.type} 人格特质，以下是提升社交表达的建议：
        </Paragraph>
        <ul style={{ paddingLeft: 20 }}>
          {description.communicationTips.map((tip, index) => (
            <li key={index}>
              <Text>{tip}</Text>
            </li>
          ))}
        </ul>
        <Divider />
        <Paragraph type="secondary">
          💡 <strong>提示：</strong>Resona 会根据你的 MBTI 类型，为你生成符合个性的高情商回复。
          你可以在主页面开始使用智能回复生成功能！
        </Paragraph>
      </Card>
      
      {/* 操作按钮 */}
      <Card>
        <Space style={{ width: '100%', justifyContent: 'center' }}>
          {onRetake && (
            <Button onClick={onRetake}>
              重新测试
            </Button>
          )}
          {onSave && (
            <Button type="primary" onClick={onSave}>
              保存结果并开始使用
            </Button>
          )}
        </Space>
      </Card>
    </div>
  )
}

export default MbtiResult
