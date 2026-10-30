import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Modal, Spinner } from 'react-bootstrap'
import { CircleAlert } from 'lucide-react'
import { chamCongThuCong, layDanhSachCongNhan } from '../../api/endpoints.js'
import { hhmm, thuNgay } from '../../lib/format.js'
import { toast } from '../../lib/toast.js'
import { TimeInput } from './ui.jsx'

/**
 * Chấm công thủ công (bắt buộc lý do). worker = { id, ma, ten } hoặc null (lượt "không nhận ra": cán bộ chọn người).
 * ngay = YYYY-MM-DD; gioVao / gioRa = giờ điền sẵn (HH:MM) nếu có.
 */
export default function ManualAttendanceModal({ worker, ngay, gioVao = '', gioRa = '', note, onClose }) {
  const qc = useQueryClient()
  const [vao, setVao] = useState(gioVao ?? '')
  const [ra, setRa] = useState(gioRa ?? '')
  const [lyDo, setLyDo] = useState('')
  const [workerId, setWorkerId] = useState(worker?.id ?? '')
  const [error, setError] = useState('')
  const { data: workers } = useQuery({
    queryKey: ['cong-nhan', { trang_thai: 'dang_lam' }],
    queryFn: () => layDanhSachCongNhan({ trang_thai: 'dang_lam' }),
    enabled: !worker,
  })
  const save = useMutation({
    mutationFn: chamCongThuCong,
    meta: { silent: true },
    onSuccess: () => {
      toast.success('Đã lưu chấm công thủ công')
      qc.invalidateQueries({ queryKey: ['bang-cong-ngay'] })
      qc.invalidateQueries({ queryKey: ['bang-cong-cn'] })
      onClose()
    },
    onError: (err) => setError(err.message),
  })
  const submit = (e) => {
    e.preventDefault()
    try {
      if (!workerId) throw new Error('Chọn công nhân cần chấm công.')
      const body = { worker_id: Number(workerId), ngay, gio_vao: hhmm(vao, 'Giờ vào'), gio_ra: hhmm(ra, 'Giờ ra'), ly_do: lyDo }
      if (!body.gio_vao && !body.gio_ra) throw new Error('Nhập ít nhất giờ vào hoặc giờ ra.')
      if (!lyDo.trim()) throw new Error('Bắt buộc ghi lý do khi chấm công thủ công.')
      setError('')
      save.mutate(body)
    } catch (err) { setError(err.message) }
  }

  return (
    <Modal show onHide={onClose} centered backdrop="static">
      <Form onSubmit={submit} noValidate>
        <Modal.Header closeButton><Modal.Title>Chấm công thủ công</Modal.Title></Modal.Header>
        <Modal.Body>
          <div className="mb-3">
            {worker && <div style={{ fontWeight: 600 }}>{worker.ten} <span className="muted" style={{ fontWeight: 400 }}>· {worker.ma}</span></div>}
            <div className="small muted">{thuNgay(ngay)}{note ? ` · ${note}` : ''}</div>
          </div>
          {!worker && (
            <Form.Group className="mb-3">
              <Form.Label htmlFor="m-worker">Công nhân</Form.Label>
              <Form.Select id="m-worker" value={workerId} onChange={(e) => setWorkerId(e.target.value)}>
                <option value="">Chọn công nhân</option>
                {(workers?.ds ?? []).map((w) => <option key={w.id} value={w.id}>{w.code} – {w.full_name}</option>)}
              </Form.Select>
            </Form.Group>
          )}
          <div className="row g-3 mb-3">
            <Form.Group className="col-6"><Form.Label htmlFor="m-in">Giờ vào</Form.Label><TimeInput id="m-in" value={vao} onChange={setVao} /></Form.Group>
            <Form.Group className="col-6"><Form.Label htmlFor="m-out">Giờ ra</Form.Label><TimeInput id="m-out" value={ra} onChange={setRa} /></Form.Group>
          </div>
          <Form.Group>
            <Form.Label htmlFor="m-reason">Lý do (bắt buộc)</Form.Label>
            <Form.Control id="m-reason" as="textarea" rows={2} maxLength={500} value={lyDo} onChange={(e) => setLyDo(e.target.value)}
              placeholder="vd Camera cổng hỏng, cán bộ xác nhận có mặt lúc 07:00" />
          </Form.Group>
          <p className="small muted mt-2 mb-0">Giờ dạng 24 giờ HH:MM. Để trống ô nào thì giữ nguyên giờ đó. Dòng công chuyển sang "Chấm thủ công" và lưu người sửa.</p>
          {error && <div className="note bad mt-3" id="m-error"><CircleAlert size={18} />{error}</div>}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onClose} disabled={save.isPending}>Huỷ</Button>
          <Button type="submit" disabled={save.isPending}>{save.isPending && <Spinner size="sm" />}Lưu chấm công</Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}
