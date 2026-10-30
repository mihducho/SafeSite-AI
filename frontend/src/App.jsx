import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { setUser, clearUser } from './store/authSlice.js'
import { layThongTinToi } from './api/endpoints.js'

import DashboardLayout from './components/layout/DashboardLayout.jsx'
import ProtectedRoute from './components/layout/ProtectedRoute.jsx'
import ToastHost from './components/common/Toast.jsx'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import GateScreen from './pages/GateScreen.jsx'
import WorkerListPage from './pages/WorkerListPage.jsx'
import WorkerDetailPage from './pages/WorkerDetailPage.jsx'
import TeamPage from './pages/TeamPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import AttendancePage from './pages/AttendancePage.jsx'
import MonthlyAttendancePage from './pages/MonthlyAttendancePage.jsx'
import ShiftConfigPage from './pages/ShiftConfigPage.jsx'
import GateConfigPage from './pages/GateConfigPage.jsx'
import TodoPage from './pages/TodoPage.jsx'

export default function App() {
  const dispatch = useDispatch()

  // Kiểm tra phiên đăng nhập (cookie session) khi ứng dụng khởi động
  useEffect(() => {
    layThongTinToi()
      .then((user) => dispatch(setUser(user)))
      .catch(() => dispatch(clearUser()))
  }, [dispatch])

  return (
    <>
      <ToastHost />
      <Routes>
        {/* Công khai */}
        <Route path="/login" element={<LoginPage />} />

        {/* Màn hình cổng: toàn màn hình, không có thanh menu (mở trên màn hình đặt ở cổng) */}
        <Route path="/man-hinh-cong" element={<ProtectedRoute><GateScreen /></ProtectedRoute>} />

        {/* Cần đăng nhập, nằm trong DashboardLayout */}
        <Route path="/" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="cong-nhan" element={<WorkerListPage />} />
          <Route path="cong-nhan/:id" element={<WorkerDetailPage />} />
          <Route path="to-doi" element={<TeamPage />} />
          <Route path="lich-su" element={<HistoryPage />} />
          <Route path="bang-cong" element={<AttendancePage />} />
          <Route path="bang-cong-thang" element={<MonthlyAttendancePage />} />
          <Route path="viec-can-xu-ly" element={<TodoPage />} />
          <Route path="cau-hinh-ca" element={<ShiftConfigPage />} />
          <Route path="cau-hinh-cong" element={<GateConfigPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}
