import { Modal, Button, Spinner } from 'react-bootstrap'
import { CircleAlert, TriangleAlert } from 'lucide-react'

/**
 * Hộp xác nhận dùng chung (thay cho window.confirm của trình duyệt).
 *
 * @param {{
 *   show: boolean,
 *   title?: string,
 *   message: import('react').ReactNode,
 *   onConfirm: () => void,
 *   onCancel: () => void,
 *   variant?: 'danger' | 'primary' | 'success',
 *   confirmLabel?: string,
 *   cancelLabel?: string,
 *   loading?: boolean,
 * }} props
 */
export default function ConfirmModal({
  show,
  title = 'Xác nhận',
  message,
  onConfirm,
  onCancel,
  variant = 'primary',
  confirmLabel = 'Xác nhận',
  cancelLabel = 'Huỷ',
  loading = false,
}) {
  const danger = variant === 'danger'
  const Icon = danger ? TriangleAlert : CircleAlert
  return (
    <Modal show={show} onHide={onCancel} centered backdrop="static">
      <Modal.Body className="d-flex gap-3" style={{ paddingTop: 24 }}>
        <span className={`stat__icon ${danger ? 'tone-bad' : 'tone-primary'}`}><Icon size={20} /></span>
        <div>
          <div style={{ fontSize: 17, fontWeight: 600, marginBottom: 6 }}>{title}</div>
          <div className="muted" style={{ fontSize: 14, lineHeight: 1.6 }}>{message}</div>
        </div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onCancel} disabled={loading}>{cancelLabel}</Button>
        <Button variant={variant} onClick={onConfirm} disabled={loading}>
          {loading && <Spinner size="sm" />}{confirmLabel}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}
