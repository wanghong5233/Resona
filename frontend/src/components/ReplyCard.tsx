/**
 * ReplyCard - 回复卡片组件
 * 
 * 功能：展示生成的回复，包含风格标签、置信度、复制按钮
 */

import { Card, Space, Tag, Button, message } from 'antd'
import { CopyOutlined } from '@ant-design/icons'
import type { ReplyOption } from '../types/api'

interface ReplyCardProps {
  reply: ReplyOption
  index: number
  onCopy?: (content: string) => void
}

export function ReplyCard({ reply, index, onCopy }: ReplyCardProps) {
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(reply.content)
      message.success('已复制到剪贴板')
      onCopy?.(reply.content)
    } catch (error) {
      message.error('复制失败')
    }
  }

  return (
    <Card
      className="reply-card"
      style={{
        marginBottom: '16px',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 标签栏 */}
        <div>
          <Space wrap>
            <Tag color="blue">回复 {index + 1}</Tag>
            <Tag color="cyan">{reply.style}</Tag>
            <Tag color="green">置信度: {(reply.confidence * 100).toFixed(0)}%</Tag>
          </Space>
        </div>

        {/* 回复内容 */}
        <div
          style={{
            fontSize: '16px',
            lineHeight: '1.8',
            color: '#333',
            padding: '12px',
            backgroundColor: '#fafafa',
            borderRadius: '4px',
          }}
        >
          {reply.content}
        </div>

        {/* 操作按钮 */}
        <Button
          type="dashed"
          icon={<CopyOutlined />}
          block
          onClick={handleCopy}
        >
          复制
        </Button>
      </Space>
    </Card>
  )
}
