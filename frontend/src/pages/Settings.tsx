import { Card, Typography, List } from 'antd'

const { Title, Paragraph } = Typography

const settingsItems = [
  'LLM 后端切换（DashScope / GPT-4 / Mock / vLLM）',
  '风险提醒开关与强度调节',
  '界面语言与主题（浅色 / 深色）',
  '快捷键 & 桌面应用偏好（Phase 2 Electron）',
]

function Settings() {
  return (
    <div className="page-container">
      <Card>
        <Title level={3}>设置中心（待实现）</Title>
        <Paragraph>
          该页面将在 Phase 2 中用于管理 Resona 的全局偏好设置。当前版本仍以演示功能为主，设置项暂未开放。
        </Paragraph>
        <Paragraph>规划中的设置包括：</Paragraph>
        <List
          dataSource={settingsItems}
          renderItem={(item) => <List.Item>• {item}</List.Item>}
          size="small"
          bordered
        />
        <Paragraph type="secondary" style={{ marginTop: 16 }}>
          提示：目前可以直接在 `.env` / 界面下方选择器中调整 LLM 后端与 MBTI 类型。
        </Paragraph>
      </Card>
    </div>
  )
}

export default Settings

