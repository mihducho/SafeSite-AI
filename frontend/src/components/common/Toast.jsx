import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { CircleAlert, CircleCheck, CircleX, Info, X } from 'lucide-react'
import { removeToast, subscribeToasts } from '../../lib/toast.js'
import './Toast.css'

const ICON = { success: CircleCheck, error: CircleX, warning: CircleAlert, info: Info }

/** Nơi hiển thị mọi toast của ứng dụng (gắn một lần trong App), góc trên bên phải. Gửi toast: toast.error('...') */
export default function ToastHost() {
  const [toasts, setToasts] = useState([])
  useEffect(() => subscribeToasts(setToasts), [])
  if (!toasts.length) return null
  return createPortal(
    <div className="toast-stack" aria-live="polite">
      {toasts.map((t) => {
        const Icon = ICON[t.type] ?? Info
        return (
          <div key={t.id} className={`toast-item ${t.type}`} role="alert">
            <Icon size={20} />
            <p>{t.message}</p>
            <button onClick={() => removeToast(t.id)} aria-label="Đóng"><X size={16} /></button>
          </div>
        )
      })}
    </div>,
    document.body,
  )
}
