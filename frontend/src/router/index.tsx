import { Routes, Route, Navigate } from 'react-router-dom'
import Home from '../pages/Home'
import MBTITest from '../pages/MBTITest'
import Settings from '../pages/Settings'
import History from '../pages/History'

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/mbti-test" element={<MBTITest />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/history" element={<History />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRouter
