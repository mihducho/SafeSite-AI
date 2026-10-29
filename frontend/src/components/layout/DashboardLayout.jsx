import React, { useCallback, useEffect, useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { selectUser, clearUser } from '../../store/authSlice.js'
import { dangXuat } from '../../api/endpoints.js'
import { useWebConfig } from '../../hooks/useWebConfig.js'
import { useGateStatus, useWsState } from '../../lib/events.js'
import { dongHo } from '../../lib/format.js'

const NavItem = ({ to, icon, label, collapsed, end }) => (
  <NavLink
    to={to}
    end={end}
    className={({ isActive }) => `nav-item-link${isActive ? ' active' : ''}`}
    title={collapsed ? label : undefined}
  >
    <span className="nav-item-icon">{icon}</span>
    {!collapsed && <span className="nav-item-text">{label}</span>}
  </NavLink>
)

const NAV = [
  {
    section: 'Chính',
    items: [
      { to: '/', icon: '📊', label: 'Tổng quan', end: true },
      { to: '/man-hinh-cong', icon: '📷', label: 'Màn hình cổng' },
    ],
  },
  {
    section: 'Quản lý',
    items: [
      { to: '/cong-nhan', icon: '👷', label: 'Công nhân' },
      { to: '/to-doi', icon: '👥', label: 'Tổ đội' },
      { to: '/lich-su', icon: '🕐', label: 'Lịch sử kiểm tra' },
    ],
  },
  {
    section: 'Chấm công',
    items: [
      { to: '/bang-cong', icon: '📅', label: 'Bảng công ngày' },
      { to: '/bang-cong-thang', icon: '🗓️', label: 'Bảng công tháng' },
      { to: '/cau-hinh-ca', icon: '⏰', label: 'Ca làm' },
    ],
  },
  {
    section: 'Hệ thống',
    items: [
      { to: '/cau-hinh-cong', icon: '⚙️', label: 'Cấu hình cổng' },
    ],
  },
]

/** Chấm trạng thái cổng (xanh: đang chạy, vàng: đang khởi động, đỏ: lỗi / mất camera / mất kết nối) */
function GateDot() {
  const st = useGateStatus()
  const ws = useWsState()
  let kind = 'warn'
  let text = 'Cổng: đang kết nối…'
  if (ws === 'mat') { kind = 'err'; text = 'Mất kết nối máy chủ' }
  else if (st?.mat_camera) { kind = 'err'; text = 'Cổng: mất kết nối camera, đang thử lại' }
  else if (st?.trang_thai === 'dang_chay' && !st.loi) { kind = 'ok'; text = `Cổng: đang chạy${st.pha === 'KIEM_TRA' ? ' · đang kiểm tra' : ''}` }
  else if (st?.trang_thai === 'dang_khoi_dong') { text = 'Cổng: đang khởi động' }
  else if (st?.trang_thai === 'tat') { kind = 'err'; text = 'Cổng: đang tắt' }
  else if (st) { kind = 'err'; text = `Cổng: lỗi${st.loi ? ` – ${st.loi}` : ''}` }
  return <span className={`sg-gate-dot ${kind}`} title={text}><i />{text}</span>
}

function Clock() {
  const { tz } = useWebConfig()
  const [now, setNow] = useState(() => dongHo(tz))
  useEffect(() => {
    const t = setInterval(() => setNow(dongHo(tz)), 1000)
    return () => clearInterval(t)
  }, [tz])
  return <span className="sg-clock d-none d-md-inline">{now.ngay} · {now.gio}</span>
}

export default function DashboardLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const user = useSelector(selectUser)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => { setMobileOpen(false) }, [location.pathname])   // đổi trang trên điện thoại -> đóng menu

  const handleLogout = useCallback(async () => {
    try {
      setIsLoggingOut(true)
      await dangXuat()
    } catch (_) {
      // bỏ qua lỗi mạng: vẫn xoá phiên phía giao diện
    } finally {
      dispatch(clearUser())
      navigate('/login', { replace: true })
    }
  }, [dispatch, navigate])

  const toggleSidebar = () => {
    if (window.innerWidth <= 768) setMobileOpen((v) => !v)
    else setSidebarCollapsed((v) => !v)
  }

  const avatarLetter = (user?.full_name || user?.username || 'U').charAt(0).toUpperCase()

  return (
    <div className="page-wrapper">
      {mobileOpen && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 999, backdropFilter: 'blur(2px)' }}
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* ════════════════════ SIDEBAR ════════════════════ */}
      <aside className={['sidebar', sidebarCollapsed ? 'collapsed' : '', mobileOpen ? 'mobile-open' : ''].filter(Boolean).join(' ')}>
        <NavLink to="/" className="sidebar-logo">
          <img src="/favicon.svg" alt="" className="sidebar-logo-icon" style={{ padding: 0, background: 'none' }} />
          <div className="sidebar-logo-text">
            <span className="brand-name">SafeGate</span>
            <span className="brand-sub">Chấm công · Bảo hộ</span>
          </div>
        </NavLink>

        <nav className="sidebar-nav">
          {NAV.map((group) => (
            <React.Fragment key={group.section}>
              <div className="sidebar-section-title">{group.section}</div>
              {group.items.map((item) => (
                <NavItem key={item.to} {...item} collapsed={sidebarCollapsed} />
              ))}
            </React.Fragment>
          ))}
        </nav>

        {!sidebarCollapsed && (
          <div style={{ padding: '0.75rem 1.25rem', borderTop: '1px solid var(--border-color)', fontSize: '0.75rem' }}>
            <a href="/cu/" title="Giao diện Jinja2 cũ, dùng khi giao diện này gặp sự cố">↩ Giao diện dự phòng</a>
            <span style={{ color: 'var(--text-muted)' }}> · </span>
            <a href="/docs" target="_blank" rel="noreferrer">Thử API</a>
          </div>
        )}
      </aside>

      {/* ════════════════════ MAIN CONTENT ════════════════════ */}
      <div className={['main-content', sidebarCollapsed ? 'sidebar-collapsed' : ''].filter(Boolean).join(' ')}>
        <header className="topbar">
          <div className="topbar-left">
            <button className="topbar-toggle" onClick={toggleSidebar} aria-label="Ẩn/hiện menu">☰</button>
            <GateDot />
          </div>

          <div className="topbar-right">
            <Clock />
            <div className="topbar-user">
              <div className="topbar-avatar">{avatarLetter}</div>
              <div className="topbar-user-info">
                <span className="topbar-user-name">{user?.full_name || user?.username || 'Người dùng'}</span>
                <span className="topbar-user-role">{user?.role === 'admin' ? 'Quản trị viên' : (user?.role ?? '')}</span>
              </div>
            </div>
            <button className="topbar-logout-btn" onClick={handleLogout} disabled={isLoggingOut}>
              {isLoggingOut ? '⏳ Đang thoát…' : '🚪 Đăng xuất'}
            </button>
          </div>
        </header>

        <main className="content-area">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
