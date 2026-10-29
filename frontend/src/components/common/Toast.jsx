import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { removeToast, subscribeToasts } from '../../lib/toast.js'
import './Toast.css'

const TYPE_CONFIG = {
  success: { bg: '#198754', icon: '✅' },
  error:   { bg: '#dc3545', icon: '❌' },
  warning: { bg: '#ffc107', icon: '⚠️', dark: true },
  info:    { bg: '#0dcaf0', icon: 'ℹ️', dark: true },
}

/** Nơi hiển thị mọi toast của ứng dụng (gắn một lần trong App). Gửi toast: toast.error('...') trong lib/toast.js. */
export default function ToastHost() {
  const [toasts, setToasts] = useState([])
  useEffect(() => subscribeToasts(setToasts), [])
  if (!toasts.length) return null
  return createPortal(
    <div className="sg-toast-container">
      {toasts.map((t) => {
        const cfg = TYPE_CONFIG[t.type] ?? TYPE_CONFIG.info
        return (
          <div key={t.id} className="sg-toast sg-toast--enter" role="alert"
            style={{ background: cfg.bg, color: cfg.dark ? '#212529' : '#fff' }}>
            <span className="sg-toast__icon">{cfg.icon}</span>
            <span className="sg-toast__msg">{t.message}</span>
            <button className="sg-toast__close" style={{ color: cfg.dark ? '#212529' : '#fff' }}
              onClick={() => removeToast(t.id)} aria-label="Đóng">×</button>
          </div>
        )
      })}
    </div>,
    document.body,
  )
}
