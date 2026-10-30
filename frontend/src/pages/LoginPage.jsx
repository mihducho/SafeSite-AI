import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { selectIsAuthenticated, setUser } from '../store/authSlice.js'
import { dangNhap } from '../api/endpoints.js'
import { Check, CircleAlert, HardHat, LoaderCircle, LockKeyhole, LogIn, UserRound } from 'lucide-react'

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
      <aside className="login__art" aria-label="Giám sát an toàn công trường">
        <div className="login__bg" aria-hidden="true" />
        <span className="login__corner login__corner--tl" aria-hidden="true" />
        <span className="login__corner login__corner--tr" aria-hidden="true" />
        <span className="login__corner login__corner--bl" aria-hidden="true" />
        <span className="login__corner login__corner--br" aria-hidden="true" />

        <div className="login__top-tag">
          <i className="login__tag-dot" aria-hidden="true" />
          <span>CAM-GATE-01 // AI PPE &amp; ATTENDANCE ACTIVE</span>
        </div>

        <div className="login__caption">
          <div className="login__hud">
            <span className="login__hud-item">
              [<Check size={11} strokeWidth={2.5} aria-hidden="true" /> HARDHAT: VERIFIED]
            </span>
            <span className="login__hud-item">
              [<Check size={11} strokeWidth={2.5} aria-hidden="true" /> SAFETY VEST: VERIFIED]
            </span>
          </div>
          <h1 className="login__tagline">Hệ thống Chấm công &amp; Kiểm soát Bảo hộ Lao động</h1>
          <p className="login__lead">Giám sát an toàn công trường và xác thực nhân sự thời gian thực.</p>
        </div>
      </aside>

      <main className="login__panel">
        <form className="login__form" onSubmit={handleSubmit} noValidate>
          <div className="login__header">
            <div className="login__badge" aria-hidden="true">
              <HardHat size={18} strokeWidth={1.75} />
            </div>
            <div className="login__eyebrow">CỔNG THÔNG TIN VẬN HÀNH</div>
            <h2 className="login__title">Đăng nhập hệ thống</h2>
            <p className="login__subtitle">Dành cho cán bộ quản lý công trường.</p>
          </div>

          {error && (
            <div className="login__error" role="alert">
              <CircleAlert size={16} strokeWidth={1.75} />
              <span>{error}</span>
            </div>
          )}

          <div className="login__field">
            <label className="form-label" htmlFor="username">Tên đăng nhập</label>
            <div className="input-icon">
              <UserRound size={16} strokeWidth={1.5} />
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                autoFocus
                className="form-control login__input"
                value={form.username}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="login__field login__field--last">
            <label className="form-label" htmlFor="password">Mật khẩu</label>
            <div className="input-icon">
              <LockKeyhole size={16} strokeWidth={1.5} />
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                className="form-control login__input"
                value={form.password}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>
          </div>

          <button type="submit" className="btn login__submit w-100" disabled={isLoading}>
            {isLoading ? <LoaderCircle size={16} strokeWidth={1.75} className="spin" /> : <LogIn size={16} strokeWidth={1.75} />}
            {isLoading ? 'Đang đăng nhập…' : 'Đăng nhập'}
          </button>

          <p className="login__fallback">
            Giao diện gặp sự cố? Dùng <a href="/cu/login">giao diện dự phòng</a>.
          </p>
        </form>
      </main>
    </div>
  )
}
