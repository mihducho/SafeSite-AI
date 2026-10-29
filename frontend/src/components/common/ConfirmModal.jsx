import { Modal, Button } from 'react-bootstrap'

/**
 * Modal xác nhận dùng chung (thay cho window.confirm của trình duyệt).
 *
 * @param {{
 *   show: boolean,
 *   title?: string,
 *   message: import('react').ReactNode,
 *   onConfirm: () => void,
 *   onCancel: () => void,
 *   variant?: 'danger' | 'warning' | 'primary' | 'success',
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
  return (
    <Modal show={show} onHide={onCancel} centered backdrop="static">
      <Modal.Header closeButton>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="mb-0">{message}</div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onCancel} disabled={loading}>
          {cancelLabel}
        </Button>
        <Button variant={variant} onClick={onConfirm} disabled={loading}>
          {loading ? 'Đang xử lý…' : confirmLabel}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}
