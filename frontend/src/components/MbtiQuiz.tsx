/**
 * MBTI 测试问卷组件
 * 
 * 提供 10 题快速测试
 */

import React, { useState } from 'react'
import { Card, Radio, Button, Space, Typography, Progress } from 'antd'
import type { RadioChangeEvent } from 'antd'
import { getAllQuestions } from '../data/mbtiQuestions'
import type { MBTIQuestion } from '../data/mbtiQuestions'

const { Title, Text, Paragraph } = Typography

interface MbtiQuizProps {
  onComplete: (selectedOptions: number[]) => void
  onCancel?: () => void
}

const MbtiQuiz: React.FC<MbtiQuizProps> = ({ onComplete, onCancel }) => {
  const questions = getAllQuestions()
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [selectedOptions, setSelectedOptions] = useState<number[]>(new Array(questions.length).fill(-1))
  
  const currentQuestion = questions[currentQuestionIndex]
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100
  const isLastQuestion = currentQuestionIndex === questions.length - 1
  const isFirstQuestion = currentQuestionIndex === 0
  const isCurrentAnswered = selectedOptions[currentQuestionIndex] !== -1
  
  /**
   * 选择选项
   */
  const handleOptionChange = (e: RadioChangeEvent) => {
    const newSelectedOptions = [...selectedOptions]
    newSelectedOptions[currentQuestionIndex] = e.target.value
    setSelectedOptions(newSelectedOptions)
  }
  
  /**
   * 下一题
   */
  const handleNext = () => {
    if (isLastQuestion) {
      // 完成测试
      onComplete(selectedOptions)
    } else {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
    }
  }
  
  /**
   * 上一题
   */
  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1)
    }
  }
  
  /**
   * 跳转到指定题目
   */
  const handleJumpTo = (index: number) => {
    setCurrentQuestionIndex(index)
  }
  
  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      {/* 进度条 */}
      <Card style={{ marginBottom: 20 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text strong>测试进度</Text>
            <Text type="secondary">{currentQuestionIndex + 1} / {questions.length}</Text>
          </div>
          <Progress percent={progress} showInfo={false} />
        </Space>
      </Card>
      
      {/* 问题卡片 */}
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Title level={4}>
              问题 {currentQuestionIndex + 1}
            </Title>
            <Paragraph style={{ fontSize: 16, marginTop: 10 }}>
              {currentQuestion.question}
            </Paragraph>
          </div>
          
          <Radio.Group
            onChange={handleOptionChange}
            value={selectedOptions[currentQuestionIndex]}
            style={{ width: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {currentQuestion.options.map((option, index) => (
                <Radio
                  key={index}
                  value={index}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: selectedOptions[currentQuestionIndex] === index
                      ? '2px solid #1890ff'
                      : '1px solid #d9d9d9',
                    borderRadius: 8,
                    backgroundColor: selectedOptions[currentQuestionIndex] === index
                      ? '#e6f7ff'
                      : '#ffffff'
                  }}
                >
                  <Text style={{ fontSize: 15 }}>{option.text}</Text>
                </Radio>
              ))}
            </Space>
          </Radio.Group>
          
          {/* 导航按钮 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 20 }}>
            <Button
              onClick={handlePrevious}
              disabled={isFirstQuestion}
            >
              上一题
            </Button>
            
            <Space>
              {onCancel && (
                <Button onClick={onCancel}>
                  取消
                </Button>
              )}
              <Button
                type="primary"
                onClick={handleNext}
                disabled={!isCurrentAnswered}
              >
                {isLastQuestion ? '完成测试' : '下一题'}
              </Button>
            </Space>
          </div>
        </Space>
      </Card>
      
      {/* 题目导航 */}
      <Card style={{ marginTop: 20 }} title="快速跳转">
        <Space wrap>
          {questions.map((_, index) => (
            <Button
              key={index}
              size="small"
              type={index === currentQuestionIndex ? 'primary' : 'default'}
              onClick={() => handleJumpTo(index)}
              style={{
                backgroundColor: selectedOptions[index] !== -1 && index !== currentQuestionIndex
                  ? '#52c41a'
                  : undefined,
                borderColor: selectedOptions[index] !== -1 && index !== currentQuestionIndex
                  ? '#52c41a'
                  : undefined,
                color: selectedOptions[index] !== -1 && index !== currentQuestionIndex
                  ? '#ffffff'
                  : undefined
              }}
            >
              {index + 1}
            </Button>
          ))}
        </Space>
      </Card>
    </div>
  )
}

export default MbtiQuiz
