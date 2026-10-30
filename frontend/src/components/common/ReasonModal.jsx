import { useState } from 'react'
import { Button, Form, Modal, Spinner } from 'react-bootstrap'
import { CircleAlert, TriangleAlert } from 'lucide-react'

/**
 * Hộp xác nhận có ô lý do (huỷ phép, xác nhận không phép...). required = bắt buộc nhập lý do.
 * onConfirm(lyDo) trả Promise: lỗi của backend hiện ngay trong hộp.
 */
export default function ReasonModal({ title, message, confirmLabel = 'Xác nhận', variant = 'primary', required = true,
  placeholder = '', onConfirm, onClose }) {
  const [lyDo, setLyDo] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    if (required && !lyDo.trim()) { setError('Bắt buộc ghi lý do.'); return }
    setBusy(true)
    setError('')
    try {
      await onConfirm(lyDo.trim())
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }
  const danger = variant === 'danger'
  return (
    <Modal show onHide={onClose} centered backdrop="static">
      <Form onSubmit={submit} noValidate>
        <Modal.Body className="d-flex gap-3" style={{ paddingTop: 18 }}>
          <span className={`stat__icon ${danger ? 'tone-bad' : 'tone-primary'}`}>
            {danger ? <TriangleAlert size={18} strokeWidth={1.5} /> : <CircleAlert size={18} strokeWidth={1.5} />}
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{title}</div>
            {message && <div className="muted mb-3" style={{ fontSize: 13.5, lineHeight: 1.55 }}>{message}</div>}
            <Form.Label htmlFor="r-ly-do">Lý do{required ? ' (bắt buộc)' : ' (không bắt buộc)'}</Form.Label>
            <Form.Control id="r-ly-do" as="textarea" rows={2} maxLength={500} value={lyDo} autoFocus
              onChange={(e) => setLyDo(e.target.value)} placeholder={placeholder} />
            {error && <div className="note bad mt-3"><CircleAlert size={18} />{error}</div>}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Huỷ</Button>
          <Button type="submit" variant={danger ? 'danger' : 'primary'} disabled={busy}>{busy && <Spinner size="sm" />}{confirmLabel}</Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}
