import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { selectIsAuthenticated, setUser } from '../store/authSlice.js'
import { dangNhap } from '../api/endpoints.js'

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
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `
          radial-gradient(ellipse at 20% 50%, rgba(247,147,30,0.08) 0%, transparent 60%),
          radial-gradient(ellipse at 80% 20%, rgba(255,193,7,0.05) 0%, transparent 50%),
          var(--navy)
        `,
        padding: '1rem',
      }}
    >
      <div style={{ width: '100%', maxWidth: '420px' }}>
        {/* ── Logo / Header ── */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '16px',
              background: 'linear-gradient(135deg, var(--orange), var(--yellow))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1rem',
              fontSize: '1.6rem',
              fontWeight: '800',
              color: '#fff',
              boxShadow: '0 0 32px rgba(247,147,30,0.35)',
            }}
          >
            SG
          </div>
          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: '800',
              color: 'var(--text-primary)',
              marginBottom: '0.25rem',
              letterSpacing: '-0.02em',
            }}
          >
            SafeGate
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Chấm công bằng khuôn mặt và kiểm tra bảo hộ tại cổng
          </p>
        </div>

        {/* ── Login Card ── */}
        <div
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            padding: '2rem',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          <h2
            style={{
              fontSize: '1.05rem',
              fontWeight: '700',
              marginBottom: '1.5rem',
              color: 'var(--text-primary)',
            }}
          >
            Đăng nhập hệ thống
          </h2>

          {/* Error Alert */}
          {error && (
            <div
              role="alert"
              style={{
                background: 'rgba(231,76,60,0.12)',
                border: '1px solid rgba(231,76,60,0.3)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.75rem 1rem',
                marginBottom: '1.25rem',
                color: '#e74c3c',
                fontSize: '0.875rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            {/* Username */}
            <div style={{ marginBottom: '1rem' }}>
              <label className="form-label" htmlFor="username">
                Tên đăng nhập
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                autoFocus
                className="form-control"
                placeholder="Nhập tên đăng nhập"
                value={form.username}
                onChange={handleChange}
                disabled={isLoading}
                style={{ padding: '0.625rem 0.875rem' }}
              />
            </div>

            {/* Password */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label className="form-label" htmlFor="password">
                Mật khẩu
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                className="form-control"
                placeholder="Nhập mật khẩu"
                value={form.password}
                onChange={handleChange}
                disabled={isLoading}
                style={{ padding: '0.625rem 0.875rem' }}
              />
            </div>

            {/* Submit */}
            <button
              type="submit"
              className="btn btn-primary w-100"
              disabled={isLoading}
              style={{
                padding: '0.7rem',
                fontSize: '0.95rem',
                fontWeight: '700',
                letterSpacing: '0.03em',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              {isLoading ? (
                <>
                  <span
                    className="spinner-border spinner-border-sm me-2"
                    role="status"
                    aria-hidden="true"
                    style={{ color: '#fff' }}
                  />
                  Đang đăng nhập...
                </>
              ) : (
                '🔓 Đăng Nhập'
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p
          style={{
            textAlign: 'center',
            marginTop: '1.5rem',
            color: 'var(--text-muted)',
            fontSize: '0.75rem',
          }}
        >
          © {new Date().getFullYear()} SafeGate &bull; Hệ thống nhận diện khuôn mặt
        </p>
      </div>
    </div>
  )
}
