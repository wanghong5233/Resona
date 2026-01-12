/**
 * ScenarioSelector - 场景和意图选择器
 * 
 * 功能：选择 MBTI、场景（职场/恋爱）、意图（拒绝/道歉/边界）
 */

import { Select, Space } from 'antd'
import { MBTIType, ScenarioType, IntentType, MBTILabels, ScenarioLabels, IntentLabels } from '../types/domain'

interface ScenarioSelectorProps {
  mbti: string
  scenario: string
  intent: string
  onMBTIChange: (mbti: string) => void
  onScenarioChange: (scenario: string) => void
  onIntentChange: (intent: string) => void
  disabled?: boolean
}

export function ScenarioSelector({
  mbti,
  scenario,
  intent,
  onMBTIChange,
  onScenarioChange,
  onIntentChange,
  disabled = false,
}: ScenarioSelectorProps) {
  // MBTI 选项
  const mbtiOptions = Object.values(MBTIType).map((type) => ({
    label: MBTILabels[type],
    value: type,
  }))

  // 场景选项
  const scenarioOptions = Object.values(ScenarioType).map((type) => ({
    label: ScenarioLabels[type],
    value: type,
  }))

  // 意图选项
  const intentOptions = Object.values(IntentType).map((type) => ({
    label: IntentLabels[type],
    value: type,
  }))

  return (
    <Space wrap size="middle">
      <Select
        style={{ width: 180 }}
        value={mbti}
        onChange={onMBTIChange}
        placeholder="选择MBTI"
        options={mbtiOptions}
        disabled={disabled}
        showSearch
        optionFilterProp="label"
      />

      <Select
        style={{ width: 150 }}
        value={scenario}
        onChange={onScenarioChange}
        placeholder="选择场景"
        options={scenarioOptions}
        disabled={disabled}
      />

      <Select
        style={{ width: 150 }}
        value={intent}
        onChange={onIntentChange}
        placeholder="选择意图"
        options={intentOptions}
        disabled={disabled}
      />
    </Space>
  )
}
