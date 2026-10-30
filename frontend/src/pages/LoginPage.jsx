import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { selectIsAuthenticated, setUser } from '../store/authSlice.js'
import { dangNhap } from '../api/endpoints.js'
import { CircleAlert, LoaderCircle, LockKeyhole, LogIn, UserRound } from 'lucide-react'
import { Logo } from '../components/common/Logo.jsx'

// Trang do backend phục vụ (không thuộc giao diện React): sau khi đăng nhập phải tải lại cả trang
const TRANG_BACKEND = ['/docs', '/openapi.json', '/cu', '/api']

export default function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const isAuthenticated = useSelector(selectIsAuthenticated)

  // Sau login -> trang đang xem trước đó (?next=...), chỉ nhận đường dẫn trong ứng dụng; mặc định về /
  const nextParam = params.get('next') || '/'
  const from = nextParam.startsWith('/') && !nextParam.startsWith('//') ? nextParam : '/'
  const goNext = () => {
    if (TRANG_BACKEND.some((p) => from === p || from.startsWith(`${p}/`) || from.startsWith(`${p}?`))) {
      window.location.assign(from)
    } else {
      navigate(from, { replace: true })
    }
  }

  // Đã đăng nhập (phiên còn hạn) mà mở /login -> đi tiếp luôn
  useEffect(() => { if (isAuthenticated) goNext() }, [isAuthenticated])  // eslint-disable-line react-hooks/exhaustive-deps

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    if (error) setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.username.trim() || !form.password) {
      setError('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.')
      return
    }
    try {
      setIsLoading(true)
      setError('')
      const userData = await dangNhap({ username: form.username.trim(), password: form.password })
      dispatch(setUser(userData))   // useEffect phía trên chuyển sang trang tiếp theo
    } catch (err) {
      setError(err.message || 'Tên đăng nhập hoặc mật khẩu không đúng.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="login">
      <aside className="login__art">
        <Logo size={44} sub="Chấm công · Kiểm tra bảo hộ" />
        <div>
          <SiteIllustration />
          <h1 className="login__tagline">Chấm công bằng khuôn mặt, kiểm tra bảo hộ tự động tại cổng</h1>
          <p className="login__lead">Công nhân chỉ cần đứng trước camera ở cổng: hệ thống nhận ra người, kiểm tra mũ bảo hộ và áo phản quang,
            đủ bảo hộ thì tự ghi giờ vào, giờ ra.</p>
        </div>
        <span className="login__foot">SafeGate · Đồ án tốt nghiệp</span>
      </aside>

      <main className="login__panel">
        <form className="login__form" onSubmit={handleSubmit} noValidate>
          <h2>Đăng nhập</h2>
          <p className="muted mb-4">Dành cho cán bộ quản lý công trường.</p>
          {error && <div className="note bad mb-3" role="alert"><CircleAlert size={18} />{error}</div>}
          <div className="mb-3">
            <label className="form-label" htmlFor="username">Tên đăng nhập</label>
            <div className="input-icon">
              <UserRound size={18} />
              <input id="username" name="username" type="text" autoComplete="username" autoFocus className="form-control form-control-lg"
                value={form.username} onChange={handleChange} disabled={isLoading} />
            </div>
          </div>
          <div className="mb-4">
            <label className="form-label" htmlFor="password">Mật khẩu</label>
            <div className="input-icon">
              <LockKeyhole size={18} />
              <input id="password" name="password" type="password" autoComplete="current-password" className="form-control form-control-lg"
                value={form.password} onChange={handleChange} disabled={isLoading} />
            </div>
          </div>
          <button type="submit" className="btn btn-primary btn-lg w-100" disabled={isLoading}>
            {isLoading ? <LoaderCircle size={18} className="spin" /> : <LogIn size={18} />}
            {isLoading ? 'Đang đăng nhập…' : 'Đăng nhập'}
          </button>
          <p className="small muted mt-4 mb-0">Giao diện gặp sự cố? Dùng <a href="/cu/login" className="text-decoration-underline">giao diện dự phòng</a>.</p>
        </form>
      </main>
    </div>
  )
}

/** Minh hoạ công trường đơn giản: cần cẩu, toà nhà đang xây, cổng có camera, công nhân đội mũ */
function SiteIllustration() {
  return (
    <svg className="login__svg" viewBox="0 0 420 240" fill="none" aria-hidden="true">
      <rect x="0" y="214" width="420" height="4" rx="2" fill="#334155" />
      {/* cần cẩu */}
      <rect x="62" y="40" width="10" height="174" fill="#F59E0B" />
      <path d="M62 40h180v8H62z" fill="#F59E0B" />
      <path d="M72 48l20 -8M92 48l20 -8M112 48l20 -8M132 48l20 -8M152 48l20 -8M172 48l20 -8" stroke="#B45309" strokeWidth="2" />
      <rect x="40" y="40" width="22" height="14" fill="#B45309" />
      <path d="M210 48v52" stroke="#94A3B8" strokeWidth="2" />
      <rect x="200" y="100" width="20" height="12" rx="2" fill="#64748B" />
      {/* toà nhà đang xây */}
      <rect x="110" y="110" width="100" height="104" fill="#1E293B" stroke="#475569" strokeWidth="2" />
      {[0, 1, 2, 3].map((r) => [0, 1, 2].map((c) => (
        <rect key={`${r}${c}`} x={122 + c * 30} y={122 + r * 22} width="18" height="12" rx="2" fill={r === 0 && c === 2 ? '#F59E0B' : '#334155'} />
      )))}
      <path d="M110 110h100M110 132h100M110 154h100M110 176h100" stroke="#475569" strokeWidth="1" />
      {/* cổng + camera */}
      <rect x="268" y="120" width="8" height="94" fill="#475569" />
      <rect x="370" y="120" width="8" height="94" fill="#475569" />
      <rect x="268" y="114" width="110" height="10" rx="3" fill="#64748B" />
      <rect x="282" y="128" width="14" height="22" rx="3" fill="#0F172A" stroke="#F59E0B" strokeWidth="2" />
      <circle cx="289" cy="135" r="3" fill="#F59E0B" />
      {/* công nhân */}
      <path d="M314 150a12 12 0 0 1 24 0z" fill="#F59E0B" />
      <rect x="310" y="149" width="32" height="4" rx="2" fill="#FCD34D" />
      <circle cx="326" cy="162" r="9" fill="#CBD5E1" />
      <path d="M310 192c0-10 7-17 16-17s16 7 16 17v8h-32z" fill="#F59E0B" />
      <path d="M314 184h24" stroke="#E2E8F0" strokeWidth="3" strokeLinecap="round" />
      <rect x="315" y="200" width="8" height="14" rx="3" fill="#64748B" />
      <rect x="329" y="200" width="8" height="14" rx="3" fill="#64748B" />
      <path d="M296 140l14 14" stroke="#22C55E" strokeWidth="2" strokeDasharray="3 3" />
    </svg>
  )
}
