/**
 * DialogueInput - 对话输入组件
 * 
 * 功能：多行文本输入框，用于输入对话内容
 */

import { Input } from 'antd'

const { TextArea } = Input

interface DialogueInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  rows?: number
  maxLength?: number
  disabled?: boolean
}

export function DialogueInput({
  value,
  onChange,
  placeholder = '请输入对话内容...',
  rows = 4,
  maxLength = 1000,
  disabled = false,
}: DialogueInputProps) {
  return (
    <TextArea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      maxLength={maxLength}
      disabled={disabled}
      showCount
      style={{
        fontSize: '16px',
        lineHeight: '1.6',
      }}
    />
  )
}
