import { useSelector } from 'react-redux'
import { Navigate, useLocation } from 'react-router-dom'
import { selectIsAuthenticated, selectIsLoading } from '../../store/authSlice.js'

/**
 * Bảo vệ route: chưa đăng nhập (hoặc hết phiên, 401) -> /login?next=<trang đang xem>.
 * Trong khi đang kiểm tra session (isLoading), hiển thị màn chờ.
 */
export default function ProtectedRoute({ children }) {
  const isAuthenticated = useSelector(selectIsAuthenticated)
  const isLoading = useSelector(selectIsLoading)
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="loading-overlay">
        <div className="loading-spinner-wrap">
          <div className="spinner-border" role="status" style={{ width: '2.5rem', height: '2.5rem' }}>
            <span className="visually-hidden">Đang tải...</span>
          </div>
          <span>Đang kiểm tra phiên đăng nhập...</span>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    const next = location.pathname + location.search
    return <Navigate to={next === '/' ? '/login' : `/login?next=${encodeURIComponent(next)}`} replace />
  }

  return children
}
