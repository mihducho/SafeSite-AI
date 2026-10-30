import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button, Form, Modal, Spinner } from 'react-bootstrap'
import { CircleAlert } from 'lucide-react'
import { themPhep } from '../../api/endpoints.js'
import { useLamMoiCong } from '../../hooks/useLamMoiCong.js'
import { hhmm, thuNgay } from '../../lib/format.js'
import { LOAI_PHEP } from '../../lib/labels.js'
import { toast } from '../../lib/toast.js'
import { TimeInput } from './ui.jsx'

const LOAI = Object.entries(LOAI_PHEP)
const GIAI_THICH = {
  ve_som: 'Ra từ giờ được phép (trừ 15 phút) trở đi thì tính là về sớm có phép.',
  di_muon: 'Vào trước giờ dự kiến (cộng 15 phút) thì tính là đi muộn có phép.',
  ra_ngoai_cong_viec: 'Thời gian ra ngoài trong khoảng này không tính là ra ngoài; có tính công thì cộng vào phút công tác.',
  nghi_ca_ngay: 'Ngày đó tính là nghỉ phép, không tính vắng.',
}

/**
 * Form thêm phép (dùng trong modal Thêm phép và tab Phép của modal ngày công).
 * defaults = { loai, ngay, tu_gio, den_gio }; lockDate = không cho đổi ngày (đang xem 1 ngày cụ thể).
 */
export function LeaveForm({ worker, defaults = {}, lockDate = false, onDone, onCancel, submitLabel = 'Thêm phép' }) {
  const lamMoi = useLamMoiCong()
  const [loai, setLoai] = useState(defaults.loai ?? 've_som')
  const [ngay, setNgay] = useState(defaults.ngay ?? '')
  const [tu, setTu] = useState(defaults.tu_gio ?? '')
  const [den, setDen] = useState(defaults.den_gio ?? '')
  const [tinhCong, setTinhCong] = useState(defaults.tinh_cong ?? (defaults.loai === 'ra_ngoai_cong_viec'))
  const [lyDo, setLyDo] = useState('')
  const [error, setError] = useState('')
  const save = useMutation({
    mutationFn: themPhep,
    meta: { silent: true },
    onSuccess: (p) => {
      toast.success(`Đã thêm phép: ${p.mo_ta}`)
      lamMoi()
      onDone?.(p)
    },
    onError: (err) => setError(err.message),
  })
  const changeLoai = (v) => { setLoai(v); setTinhCong(v === 'ra_ngoai_cong_viec') }
  const submit = (e) => {
    e.preventDefault()
    try {
      if (!ngay) throw new Error('Chọn ngày của phép.')
      const body = { worker_id: worker.id, ngay, loai, ly_do: lyDo, tinh_cong: tinhCong }
      if (loai === 've_som') body.tu_gio = hhmm(tu, 'Được về từ') ?? (() => { throw new Error('Nhập giờ được phép về.') })()
      if (loai === 'di_muon') body.den_gio = hhmm(den, 'Dự kiến đến') ?? (() => { throw new Error('Nhập giờ dự kiến đến.') })()
      if (loai === 'ra_ngoai_cong_viec') {
        body.tu_gio = hhmm(tu, 'Từ giờ')
        body.den_gio = hhmm(den, 'Đến giờ')
        if (!body.tu_gio || !body.den_gio) throw new Error('Nhập đủ từ giờ và đến giờ.')
      }
      if (!lyDo.trim()) throw new Error('Bắt buộc ghi lý do của phép.')
      setError('')
      save.mutate(body)
    } catch (err) { setError(err.message) }
  }

  return (
    <Form onSubmit={submit} noValidate className="leave-form">
      <Form.Group className="mb-3">
        <Form.Label>Loại phép</Form.Label>
        <div className="choice-grid">
          {LOAI.map(([k, text]) => (
            <button key={k} type="button" className={`choice${loai === k ? ' active' : ''}`} onClick={() => changeLoai(k)}
              aria-pressed={loai === k}>{text}</button>
          ))}
        </div>
        <div className="small muted mt-2">{GIAI_THICH[loai]}</div>
      </Form.Group>
      <div className="row g-3 mb-3">
        <Form.Group className="col-sm-6">
          <Form.Label htmlFor="p-ngay">Ngày</Form.Label>
          {lockDate
            ? <div className="form-static num">{thuNgay(ngay)}</div>
            : <Form.Control id="p-ngay" type="date" value={ngay} onChange={(e) => setNgay(e.target.value)} />}
        </Form.Group>
        {loai === 've_som' && (
          <Form.Group className="col-sm-6"><Form.Label htmlFor="p-tu">Được về từ</Form.Label><TimeInput id="p-tu" value={tu} onChange={setTu} /></Form.Group>
        )}
        {loai === 'di_muon' && (
          <Form.Group className="col-sm-6"><Form.Label htmlFor="p-den">Dự kiến đến</Form.Label><TimeInput id="p-den" value={den} onChange={setDen} /></Form.Group>
        )}
        {loai === 'ra_ngoai_cong_viec' && (
          <>
            <Form.Group className="col-6 col-sm-3"><Form.Label htmlFor="p-tu">Từ giờ</Form.Label><TimeInput id="p-tu" value={tu} onChange={setTu} /></Form.Group>
            <Form.Group className="col-6 col-sm-3"><Form.Label htmlFor="p-den">Đến giờ</Form.Label><TimeInput id="p-den" value={den} onChange={setDen} /></Form.Group>
          </>
        )}
      </div>
      {loai !== 'nghi_ca_ngay' && (
        <Form.Check className="mb-3" id="p-tinh-cong" checked={tinhCong} onChange={(e) => setTinhCong(e.target.checked)}
          label="Có tính công (thời gian vắng mặt trong phép được cộng vào công)" />
      )}
      <Form.Group>
        <Form.Label htmlFor="p-ly-do">Lý do (bắt buộc)</Form.Label>
        <Form.Control id="p-ly-do" as="textarea" rows={2} maxLength={500} value={lyDo} onChange={(e) => setLyDo(e.target.value)}
          placeholder="vd Đi khám bệnh, tổ trưởng đã đồng ý" />
      </Form.Group>
      {error && <div className="note bad mt-3"><CircleAlert size={18} />{error}</div>}
      <div className="d-flex justify-content-end gap-2 mt-3">
        {onCancel && <Button variant="secondary" onClick={onCancel} disabled={save.isPending}>Huỷ</Button>}
        <Button type="submit" disabled={save.isPending}>{save.isPending && <Spinner size="sm" />}{submitLabel}</Button>
      </div>
    </Form>
  )
}

/** Modal "Thêm phép": mở từ bảng công ngày, Việc cần xử lý, chi tiết công nhân. worker = { id, ma, ten } */
export default function LeaveModal({ worker, defaults, onClose }) {
  return (
    <Modal show onHide={onClose} centered backdrop="static">
      <Modal.Header closeButton><Modal.Title>Thêm phép</Modal.Title></Modal.Header>
      <Modal.Body>
        <div className="mb-3" style={{ fontWeight: 600 }}>{worker.ten} <span className="muted" style={{ fontWeight: 400 }}>· {worker.ma}</span></div>
        <LeaveForm worker={worker} defaults={defaults} onDone={onClose} onCancel={onClose} />
      </Modal.Body>
    </Modal>
  )
}
