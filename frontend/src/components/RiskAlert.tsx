/**
 * RiskAlert - 风险预警组件
 * 
 * 功能：显示对话风险等级和警告信息（红/黄/绿）
 */

import { Alert } from 'antd'
import type { RiskWarning } from '../types/api'

interface RiskAlertProps {
  warning: RiskWarning
  onClose?: () => void
}

export function RiskAlert({ warning, onClose }: RiskAlertProps) {
  // 根据风险等级映射 Alert 类型
  const getAlertType = (level: string): 'success' | 'warning' | 'error' | 'info' => {
    switch (level) {
      case 'high':
        return 'error'
      case 'medium':
        return 'warning'
      case 'low':
        return 'info'
      case 'safe':
      default:
        return 'success'
    }
  }

  // 根据风险等级生成标题
  const getAlertTitle = (level: string): string => {
    switch (level) {
      case 'high':
        return '🔴 高风险警告'
      case 'medium':
        return '🟡 中等风险提示'
      case 'low':
        return '🟢 低风险提示'
      case 'safe':
      default:
        return '🟢 对话安全'
    }
  }

  // 如果风险等级是 safe，不显示警告
  if (warning.level === 'safe') {
    return null
  }

  // 构建描述信息
  const description = (
    <div>
      <p><strong>风险类型：</strong>{warning.type?.join('、') || '未知'}</p>
      <p><strong>风险原因：</strong>{warning.reason}</p>
      {warning.keywords && warning.keywords.length > 0 && (
        <p><strong>检测到的关键词：</strong>{warning.keywords.join('、')}</p>
      )}
      {warning.suggestion && (
        <p><strong>建议：</strong>{warning.suggestion}</p>
      )}
    </div>
  )

  return (
    <Alert
      type={getAlertType(warning.level)}
      message={getAlertTitle(warning.level)}
      description={description}
      showIcon
      closable={!!onClose}
      onClose={onClose}
      style={{
        marginBottom: '24px',
        borderRadius: '8px',
      }}
    />
  )
}
