import { forwardRef, useCallback, useEffect, useState } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { Dropdown } from 'react-bootstrap'
import {
  CalendarDays, CalendarRange, ChevronDown, Clock, Code2, History, LayoutDashboard, LifeBuoy, LogOut, MonitorPlay,
  PanelLeftClose, PanelLeftOpen, Settings2, Users, UsersRound,
} from 'lucide-react'
import { selectUser, clearUser } from '../../store/authSlice.js'
import { dangXuat } from '../../api/endpoints.js'
import { useWebConfig } from '../../hooks/useWebConfig.js'
import { useGateStatus, useWsState } from '../../lib/events.js'
import { dongHo } from '../../lib/format.js'
import { trangThaiCong } from '../../lib/labels.js'
import { Logo, LogoMark } from '../common/Logo.jsx'

const NAV = [
  { group: 'Chính', items: [
    { to: '/', icon: LayoutDashboard, label: 'Tổng quan', end: true },
    { to: '/man-hinh-cong', icon: MonitorPlay, label: 'Màn hình cổng' },
  ] },
  { group: 'Quản lý', items: [
    { to: '/cong-nhan', icon: Users, label: 'Công nhân' },
    { to: '/to-doi', icon: UsersRound, label: 'Tổ đội' },
    { to: '/lich-su', icon: History, label: 'Lịch sử kiểm tra' },
  ] },
  { group: 'Chấm công', items: [
    { to: '/bang-cong', icon: CalendarDays, label: 'Bảng công ngày' },
    { to: '/bang-cong-thang', icon: CalendarRange, label: 'Bảng công tháng' },
    { to: '/cau-hinh-ca', icon: Clock, label: 'Ca làm' },
  ] },
  { group: 'Hệ thống', items: [
    { to: '/cau-hinh-cong', icon: Settings2, label: 'Cấu hình cổng' },
  ] },
]

/** Tên trang + đường dẫn nhỏ cho thanh trên, theo địa chỉ đang mở */
function pageTitle(path) {
  if (/^\/cong-nhan\/\d+/.test(path)) return ['Chi tiết công nhân', 'Quản lý / Công nhân']
  for (const { group, items } of NAV) {
    for (const it of items) {
      if (path === it.to || (!it.end && path.startsWith(`${it.to}/`))) return [it.label, group]
    }
  }
  return ['SafeGate', '']
}

function GatePill() {
  const st = useGateStatus()
  const ws = useWsState()
  const [short, long, tone] = trangThaiCong(st, ws)
  return <span className={`gate-pill ${tone}`} title={long}><i />{short}</span>
}

function TopClock() {
  const { tz } = useWebConfig()
  const [now, setNow] = useState(() => dongHo(tz))
  useEffect(() => {
    const t = setInterval(() => setNow(dongHo(tz)), 1000)
    return () => clearInterval(t)
  }, [tz])
  return <span className="topbar__clock">{now.ngay} · {now.gio}</span>
}

const UserToggle = forwardRef(function UserToggle({ onClick, user }, ref) {
  const name = user?.full_name || user?.username || 'Người dùng'
  return (
    <button ref={ref} type="button" className="user-btn" onClick={(e) => { e.preventDefault(); onClick(e) }}>
      <span className="avatar" style={{ width: 26, height: 26, fontSize: 11.5 }}>
        {name.charAt(0).toUpperCase()}
      </span>
      <span className="d-none d-lg-inline">{name}</span>
      <ChevronDown size={15} strokeWidth={1.5} className="muted" />
    </button>
  )
})

export default function DashboardLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('sg-sidebar') === 'thu-gon' } catch { return false }
  })
  const [mobileOpen, setMobileOpen] = useState(false)
  const user = useSelector(selectUser)
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const [title, crumb] = pageTitle(location.pathname)

  useEffect(() => { setMobileOpen(false) }, [location.pathname])   // đổi trang trên màn hình hẹp -> đóng menu
  useEffect(() => { document.title = `${title} · SafeGate` }, [title])

  const toggle = () => {
    if (window.innerWidth <= 900) { setMobileOpen((v) => !v); return }
    setCollapsed((v) => {
      try { localStorage.setItem('sg-sidebar', v ? 'mo-rong' : 'thu-gon') } catch { /* không lưu được: bỏ qua */ }
      return !v
    })
  }

  const handleLogout = useCallback(async () => {
    try { await dangXuat() } catch { /* bỏ qua lỗi mạng: vẫn xoá phiên phía giao diện */ }
    dispatch(clearUser())
    navigate('/login', { replace: true })
  }, [dispatch, navigate])

  return (
    <div className={`app${collapsed ? ' collapsed' : ''}${mobileOpen ? ' mobile-open' : ''}`}>
      <div className="side-backdrop" onClick={() => setMobileOpen(false)} />
      <aside className="sidebar">
        <NavLink to="/" className="sidebar__brand" title="SafeGate">
          {collapsed ? <LogoMark size={30} /> : <Logo size={30} />}
        </NavLink>
        <nav className="sidebar__nav">
          {NAV.map(({ group, items }) => (
            <div key={group}>
              <div className="sidebar__group">{group}</div>
              {items.map(({ to, icon: Icon, label, end }) => (
                <NavLink key={to} to={to} end={end} className="sidebar__link" title={collapsed ? label : undefined}>
                  <Icon size={16} strokeWidth={1.5} />
                  <span className="sidebar__label">{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar__foot">
          <a href="/cu/" title="Giao diện Jinja2 cũ, dùng khi giao diện này gặp sự cố"><LifeBuoy size={15} strokeWidth={1.5} /><span>Giao diện dự phòng</span></a>
          <a href="/docs" target="_blank" rel="noreferrer" title="Thử API"><Code2 size={15} strokeWidth={1.5} /><span>API</span></a>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="btn btn-text btn-icon" onClick={toggle} aria-label="Thu gọn / mở rộng menu">
            {collapsed ? <PanelLeftOpen size={17} strokeWidth={1.5} /> : <PanelLeftClose size={17} strokeWidth={1.5} />}
          </button>
          <div className="topbar__title">
            <b>{title}</b>
            {crumb && <span className="topbar__crumb">{crumb}</span>}
          </div>
          <div className="topbar__right">
            <GatePill />
            <TopClock />
            <Dropdown align="end">
              <Dropdown.Toggle as={UserToggle} user={user} />
              <Dropdown.Menu>
                <div className="px-2 py-1 mb-1" style={{ borderBottom: '1px solid var(--line)' }}>
                  <div style={{ fontWeight: 600 }}>{user?.full_name || user?.username}</div>
                  <div className="small muted">{user?.role === 'admin' ? 'Quản trị viên' : 'Tài khoản'} · {user?.username}</div>
                </div>
                <Dropdown.Item as="button" onClick={handleLogout}><LogOut size={15} strokeWidth={1.5} />Đăng xuất</Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
