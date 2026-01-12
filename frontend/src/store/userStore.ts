import { proxy } from 'valtio'
import type { MBTIType } from '../types/api'

// 用户状态
interface UserState {
  userId: string | null
  mbti: MBTIType | null
}

export const userStore = proxy<UserState>({
  userId: null,
  mbti: null,
})

// 持久化到 localStorage
export const saveUserStore = () => {
  localStorage.setItem('resona_user', JSON.stringify(userStore))
}

export const loadUserStore = () => {
  const saved = localStorage.getItem('resona_user')
  if (saved) {
    const data = JSON.parse(saved)
    userStore.userId = data.userId
    userStore.mbti = data.mbti
  }
}

// 初始化时加载
loadUserStore()
