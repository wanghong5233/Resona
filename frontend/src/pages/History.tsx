import { Card, Typography, Empty, Button } from 'antd'

const { Title, Paragraph } = Typography

function History() {
  return (
    <div className="page-container">
      <Card>
        <Title level={3}>对话记录（计划中）</Title>
        <Paragraph>
          Phase 2 将引入 Redis / SQLite 作为轻量级存储，用于保留本地会话记录、标记收藏、导出反馈等功能。
        </Paragraph>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="当前版本暂不保存历史记录"
        >
          <Button type="primary" disabled>
            即将上线
          </Button>
        </Empty>
        <Paragraph type="secondary" style={{ marginTop: 16 }}>
          需求回顾：用户希望快速回看最近生成的高情商回复，并针对优秀结果追加批注 / 收藏。
        </Paragraph>
      </Card>
    </div>
  )
}

export default History

