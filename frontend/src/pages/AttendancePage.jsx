import { useEffect, useRef, useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Card, Form, Modal, Spinner, Table } from 'react-bootstrap'
import { Link, useSearchParams } from 'react-router-dom'
import { chamCongThuCong, layBangCongNgay, layDanhSachToDoi } from '../api/endpoints.js'
import { EmptyRow, StatusBadge, TimeInput } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents } from '../lib/events.js'
import { doiNgay, hhmm, ngay, phut } from '../lib/format.js'
import { CHAM_CONG } from '../lib/labels.js'
import { toast } from '../lib/toast.js'

// ─── Modal chấm công thủ công (bắt buộc lý do) ────────────────────────────────
function ChamCongModal({ row, onClose }) {
  const qc = useQueryClient()
  const [gioVao, setGioVao] = useState(row.gio_vao ?? '')
  const [gioRa, setGioRa] = useState(row.gio_ra ?? '')
  const [lyDo, setLyDo] = useState('')
  const [error, setError] = useState('')
  const save = useMutation({
    mutationFn: chamCongThuCong,
    meta: { silent: true },
    onSuccess: () => {
      toast.success('Đã lưu chấm công thủ công')
      qc.invalidateQueries({ queryKey: ['bang-cong-ngay'] })
      onClose()
    },
    onError: (err) => setError(err.message),
  })
  const submit = (e) => {
    e.preventDefault()
    try {
      const body = { worker_id: row.worker_id, ngay: row.ngay, gio_vao: hhmm(gioVao, 'Giờ vào'), gio_ra: hhmm(gioRa, 'Giờ ra'), ly_do: lyDo }
      if (!lyDo.trim()) throw new Error('Bắt buộc ghi lý do khi chấm công thủ công')
      setError('')
      save.mutate(body)
    } catch (err) { setError(err.message) }
  }

  return (
    <Modal show onHide={onClose} centered backdrop="static">
      <Form onSubmit={submit} noValidate>
        <Modal.Header closeButton><Modal.Title>Chấm công thủ công</Modal.Title></Modal.Header>
        <Modal.Body>
          <p className="mb-3"><b>{row.ma} – {row.ho_ten}</b> · ngày <b>{ngay(row.ngay)}</b></p>
          <div className="d-flex gap-3 mb-3">
            <Form.Group className="flex-fill"><Form.Label htmlFor="m-in">Giờ vào</Form.Label><TimeInput id="m-in" value={gioVao} onChange={setGioVao} /></Form.Group>
            <Form.Group className="flex-fill"><Form.Label htmlFor="m-out">Giờ ra</Form.Label><TimeInput id="m-out" value={gioRa} onChange={setGioRa} /></Form.Group>
          </div>
          <Form.Group>
            <Form.Label htmlFor="m-reason">Lý do (bắt buộc)</Form.Label>
            <Form.Control id="m-reason" as="textarea" rows={2} maxLength={500} value={lyDo} onChange={(e) => setLyDo(e.target.value)}
              placeholder="vd Camera cổng hỏng, cán bộ xác nhận có mặt lúc 07:00" />
          </Form.Group>
          <div className="small mt-2" style={{ color: 'var(--text-muted)' }}>
            Giờ dạng 24 giờ HH:MM. Để trống ô giờ nào thì giữ nguyên giờ đó. Dòng công chuyển sang trạng thái "chấm thủ công", lưu người sửa.
          </div>
          {error && <Alert variant="danger" className="mt-3 mb-0 py-2" id="m-error">{error}</Alert>}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onClose} disabled={save.isPending}>Huỷ</Button>
          <Button type="submit" disabled={save.isPending}>{save.isPending ? <Spinner size="sm" /> : 'Lưu chấm công'}</Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function AttendancePage() {
  const cfg = useWebConfig()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [row, setRow] = useState(null)
  const reloadTimer = useRef(null)
  const ngayXem = params.get('ngay') || cfg.today
  const toDoi = params.get('to_doi') ?? ''
  const go = (patch) => {
    const p = new URLSearchParams({ ngay: ngayXem, ...(toDoi ? { to_doi: toDoi } : {}), ...patch })
    if (!p.get('to_doi')) p.delete('to_doi')
    setParams(p, { replace: true })
  }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['bang-cong-ngay', ngayXem, toDoi],
    queryFn: () => layBangCongNgay({ ngay: ngayXem, to_doi: toDoi || undefined }),
    placeholderData: keepPreviousData,
  })
  const { data: teams } = useQuery({ queryKey: ['to-doi'], queryFn: layDanhSachToDoi, staleTime: 60_000 })

  // Lượt ghi giờ vào/ra (WebSocket) khi đang xem hôm nay -> tải lại
  useGateEvents((ev) => {
    if (ev.loai !== 'luot' || !ev.ghi_cong || ngayXem !== cfg.today) return
    clearTimeout(reloadTimer.current)
    reloadTimer.current = setTimeout(() => qc.invalidateQueries({ queryKey: ['bang-cong-ngay'] }), 500)
  })
  useEffect(() => () => clearTimeout(reloadTimer.current), [])

  const ds = data?.ds ?? []
  const came = ds.filter((r) => r.gio_vao).length

  return (
    <div className="sg-page">
      <div className="section-header">
        <h1 className="section-title mb-0">Bảng công <span className="sg-sub ms-2">ngày {ngay(ngayXem)}</span></h1>
        <Link to="/bang-cong-thang" className="btn btn-outline-primary btn-sm">🗓️ Bảng công tháng</Link>
      </div>

      <div className="sg-filters">
        <Button size="sm" variant="secondary" title="Ngày trước" onClick={() => go({ ngay: doiNgay(ngayXem, -1) })}>‹</Button>
        <Form.Group>
          <Form.Label>Ngày</Form.Label>
          <Form.Control type="date" size="sm" value={ngayXem} onChange={(e) => e.target.value && go({ ngay: e.target.value })} />
        </Form.Group>
        <Button size="sm" variant="secondary" title="Ngày sau" onClick={() => go({ ngay: doiNgay(ngayXem, 1) })}>›</Button>
        <Button size="sm" variant="outline-secondary" onClick={() => go({ ngay: cfg.today })} disabled={ngayXem === cfg.today}>Hôm nay</Button>
        <Form.Group>
          <Form.Label>Tổ đội</Form.Label>
          <Form.Select size="sm" value={toDoi} onChange={(e) => go({ to_doi: e.target.value })} style={{ minWidth: 180 }}>
            <option value="">Tất cả tổ</option>
            {(teams?.ds ?? []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </Form.Select>
        </Form.Group>
        {isFetching && <Spinner size="sm" className="mb-2" />}
      </div>

      <Card>
        <div className="table-responsive">
          <Table hover className="mb-0 sg-table">
            <thead>
              <tr><th>Mã</th><th>Họ tên</th><th>Tổ đội</th><th>Giờ vào</th><th>Giờ ra</th><th>Đi muộn</th><th>Về sớm</th>
                <th>Số giờ làm</th><th>Trạng thái</th><th>Ghi chú</th><th /></tr>
            </thead>
            <tbody>
              {isLoading ? <EmptyRow colSpan={11}><Spinner size="sm" /></EmptyRow>
                : !ds.length ? <EmptyRow colSpan={11}>Không có công nhân nào.</EmptyRow>
                  : ds.map((r) => (
                    <tr key={r.worker_id}>
                      <td style={{ fontWeight: 600 }}>{r.ma}</td>
                      <td><Link to={`/cong-nhan/${r.worker_id}`}>{r.ho_ten}</Link></td>
                      <td>{r.to_doi ?? ''}</td>
                      <td>{r.gio_vao ?? ''}</td>
                      <td>{r.gio_ra ?? (r.thieu_gio_ra ? <Badge bg="danger">Thiếu giờ ra</Badge>
                        : r.gio_vao ? <span className="sg-sub">đang có mặt</span> : '')}</td>
                      <td>{r.di_muon_phut ? <span className="text-danger">{r.di_muon_phut} phút</span> : ''}</td>
                      <td>{r.ve_som_phut && r.gio_ra ? `${r.ve_som_phut} phút` : ''}</td>
                      <td style={{ fontWeight: 600 }}>{r.gio_ra ? phut(r.so_phut_lam) : ''}</td>
                      <td><StatusBadge map={CHAM_CONG} value={r.trang_thai} /></td>
                      <td className="small" style={{ whiteSpace: 'pre-line', maxWidth: '22rem' }}>{r.ghi_chu ?? ''}</td>
                      <td className="text-end"><Button size="sm" variant="outline-primary" className="text-nowrap" onClick={() => setRow(r)}>Chấm thủ công</Button></td>
                    </tr>
                  ))}
            </tbody>
          </Table>
        </div>
        <Card.Footer className="small" style={{ color: 'var(--text-secondary)' }}>
          {came}/{ds.length} người đã vào · {ds.filter((r) => r.di_muon_phut).length} người đi muộn ·{' '}
          {ds.filter((r) => r.gio_vao && !r.gio_ra).length} người chưa ra
        </Card.Footer>
      </Card>

      {row && <ChamCongModal row={row} onClose={() => setRow(null)} />}
    </div>
  )
}
