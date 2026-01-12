import axios from 'axios'
import type {
  ReplyGenerateRequest,
  ReplyGenerateResponse,
  UserProfileRequest,
  UserProfileResponse,
  HealthCheckResponse,
} from '../types/api'

// API 基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// API 方法
export const apiClient = {
  // 健康检查
  health: () => api.get<HealthCheckResponse>('/api/v1/health'),

  // 生成回复
  generateReplies: (data: ReplyGenerateRequest) =>
    api.post<ReplyGenerateResponse>('/api/v1/reply/generate', data),

  // 更新用户画像
  updateUserProfile: (data: UserProfileRequest) =>
    api.post<UserProfileResponse>('/api/v1/user/profile', data),

  // 获取用户画像
  getUserProfile: (userId: string) =>
    api.get<UserProfileResponse>(`/api/v1/user/profile/${userId}`),
}

export default api
