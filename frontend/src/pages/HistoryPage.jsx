import { useEffect, useRef, useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Card, Form, Modal, Spinner, Table } from 'react-bootstrap'
import { Link, useSearchParams } from 'react-router-dom'
import { chamCongThuCong, layDanhSachCongNhan, layLichSuLuot } from '../api/endpoints.js'
import CheckDetailModal from '../components/common/CheckDetailModal.jsx'
import { EmptyRow, Pager, StatusBadge, TimeInput } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents } from '../lib/events.js'
import { gio, hhmm, ngay } from '../lib/format.js'
import { HANH_DONG, HUONG, KET_QUA, MAT, thieuText } from '../lib/labels.js'
import { toast } from '../lib/toast.js'

// ─── Modal chấm công thủ công từ một lượt (vd camera nhận nhầm / không nhận ra) ──
function ChamCongModal({ luot, onClose }) {
  const qc = useQueryClient()
  const [gioVao, setGioVao] = useState(luot.huong !== 'ra' ? gio(luot.thoi_diem) : '')
  const [gioRa, setGioRa] = useState(luot.huong === 'ra' ? gio(luot.thoi_diem) : '')
  const [lyDo, setLyDo] = useState('')
  const [workerId, setWorkerId] = useState(luot.cong_nhan?.id ?? '')
  const [error, setError] = useState('')
  const { data: workers } = useQuery({
    queryKey: ['cong-nhan', { trang_thai: 'dang_lam' }],
    queryFn: () => layDanhSachCongNhan({ trang_thai: 'dang_lam' }),
    enabled: !luot.cong_nhan,
  })
  const ngayLuot = luot.thoi_diem.slice(0, 10)
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
      if (!workerId) throw new Error('Chọn công nhân cần chấm công.')
      const body = { worker_id: Number(workerId), ngay: ngayLuot, gio_vao: hhmm(gioVao, 'Giờ vào'), gio_ra: hhmm(gioRa, 'Giờ ra'), ly_do: lyDo }
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
          <p className="mb-3" style={{ color: 'var(--text-secondary)' }}>
            Lượt #{luot.id} lúc {gio(luot.thoi_diem, true)} ngày <b>{ngay(luot.thoi_diem)}</b>
            {luot.cong_nhan && <> · <b>{luot.cong_nhan.ma} – {luot.cong_nhan.ten}</b></>}
          </p>
          {!luot.cong_nhan && (
            <Form.Group className="mb-3">
              <Form.Label>Công nhân *</Form.Label>
              <Form.Select value={workerId} onChange={(e) => setWorkerId(e.target.value)}>
                <option value="">— Chọn công nhân —</option>
                {(workers?.ds ?? []).map((w) => <option key={w.id} value={w.id}>{w.code} – {w.full_name}</option>)}
              </Form.Select>
            </Form.Group>
          )}
          <div className="d-flex gap-3 mb-3">
            <Form.Group className="flex-fill"><Form.Label>Giờ vào</Form.Label><TimeInput value={gioVao} onChange={setGioVao} /></Form.Group>
            <Form.Group className="flex-fill"><Form.Label>Giờ ra</Form.Label><TimeInput value={gioRa} onChange={setGioRa} /></Form.Group>
          </div>
          <Form.Group>
            <Form.Label>Lý do (bắt buộc)</Form.Label>
            <Form.Control as="textarea" rows={2} maxLength={500} value={lyDo} onChange={(e) => setLyDo(e.target.value)}
              placeholder="vd Camera nhận nhầm, cán bộ xác nhận có mặt lúc 07:00" />
          </Form.Group>
          <div className="small mt-2" style={{ color: 'var(--text-muted)' }}>Giờ dạng 24 giờ HH:MM. Để trống ô nào thì giữ nguyên giờ đó.</div>
          {error && <Alert variant="danger" className="mt-3 mb-0 py-2">{error}</Alert>}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onClose} disabled={save.isPending}>Huỷ</Button>
          <Button type="submit" disabled={save.isPending}>{save.isPending ? <Spinner size="sm" /> : 'Lưu chấm công'}</Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}

function ReviewBadge({ value }) {
  if (value === 'dung') return <Badge bg="success">Đúng</Badge>
  if (value === 'bao_nham') return <Badge bg="danger">Báo nhầm</Badge>
  return <span className="sg-muted small">—</span>
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function HistoryPage() {
  const cfg = useWebConfig()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [checkId, setCheckId] = useState(null)
  const [manual, setManual] = useState(null)
  const reloadTimer = useRef(null)

  // Bộ lọc nằm trên địa chỉ trang (?ngay=...&cong_nhan_id=...) để tải lại / gửi link vẫn giữ.
  // Mở từ trang công nhân (?cong_nhan_id=) -> mặc định mọi ngày; còn lại mặc định hôm nay. "ngay=" (rỗng) = mọi ngày.
  const filter = {
    ngay: params.has('ngay') ? params.get('ngay') : (params.has('cong_nhan_id') ? '' : cfg.today),
    cong_nhan_id: params.get('cong_nhan_id') ?? '',
    ket_qua: params.get('ket_qua') ?? '',
    hanh_dong: params.get('hanh_dong') ?? '',
    trang: Number(params.get('trang') || 1),
  }
  const setFilter = (patch) => {
    const next = { ...filter, trang: 1, ...patch }
    const p = new URLSearchParams()
    p.set('ngay', next.ngay)
    for (const k of ['cong_nhan_id', 'ket_qua', 'hanh_dong']) if (next[k]) p.set(k, next[k])
    if (next.trang > 1) p.set('trang', next.trang)
    setParams(p, { replace: true })
  }

  const query = {
    ngay: filter.ngay || undefined, cong_nhan_id: filter.cong_nhan_id || undefined, ket_qua: filter.ket_qua || undefined,
    hanh_dong: filter.hanh_dong || undefined, trang: filter.trang, so_dong: cfg.pageSize,
  }
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['lich-su-luot', query], queryFn: () => layLichSuLuot(query), placeholderData: keepPreviousData,
  })
  const { data: workers } = useQuery({ queryKey: ['cong-nhan', {}], queryFn: () => layDanhSachCongNhan() })

  // Lượt mới khi đang xem trang 1 -> tải lại
  useGateEvents((ev) => {
    if (ev.loai !== 'luot' || filter.trang !== 1) return
    clearTimeout(reloadTimer.current)
    reloadTimer.current = setTimeout(() => qc.invalidateQueries({ queryKey: ['lich-su-luot'] }), 300)
  })
  useEffect(() => () => clearTimeout(reloadTimer.current), [])

  const ds = data?.ds ?? []

  return (
    <div className="sg-page">
      <div className="section-header">
        <h1 className="section-title mb-0">Lịch sử kiểm tra
          <span className="sg-sub ms-2">{data ? `${data.tong} lượt${filter.ngay ? ` ngày ${ngay(filter.ngay)}` : ' (mọi ngày)'}` : ''}</span>
        </h1>
        {isFetching && <Spinner size="sm" />}
      </div>

      <div className="sg-filters">
        <Form.Group>
          <Form.Label>Ngày</Form.Label>
          <Form.Control type="date" size="sm" value={filter.ngay} onChange={(e) => setFilter({ ngay: e.target.value })} style={{ minWidth: 150 }} />
        </Form.Group>
        <Button size="sm" variant="secondary" onClick={() => setFilter({ ngay: '' })} disabled={!filter.ngay}>Mọi ngày</Button>
        <Form.Group>
          <Form.Label>Công nhân</Form.Label>
          <Form.Select size="sm" value={filter.cong_nhan_id} onChange={(e) => setFilter({ cong_nhan_id: e.target.value })} style={{ minWidth: 200 }}>
            <option value="">Tất cả</option>
            {(workers?.ds ?? []).map((w) => <option key={w.id} value={w.id}>{w.code} – {w.full_name}</option>)}
          </Form.Select>
        </Form.Group>
        <Form.Group>
          <Form.Label>Kết quả</Form.Label>
          <Form.Select size="sm" value={filter.ket_qua} onChange={(e) => setFilter({ ket_qua: e.target.value })}>
            <option value="">Tất cả</option>
            {Object.entries(KET_QUA).map(([k, [t]]) => <option key={k} value={k}>{t}</option>)}
          </Form.Select>
        </Form.Group>
        <Form.Group>
          <Form.Label>Hành động</Form.Label>
          <Form.Select size="sm" value={filter.hanh_dong} onChange={(e) => setFilter({ hanh_dong: e.target.value })}>
            <option value="">Tất cả</option>
            {Object.entries(HANH_DONG).map(([k, [t]]) => <option key={k} value={k}>{t}</option>)}
          </Form.Select>
        </Form.Group>
        <Button size="sm" variant="outline-secondary" onClick={() => setParams(new URLSearchParams({ ngay: cfg.today }), { replace: true })}>Bỏ lọc</Button>
      </div>

      <Card>
        <div className="table-responsive">
          <Table hover className="mb-0 sg-table">
            <thead>
              <tr><th>Ảnh</th><th>Thời điểm</th><th>Công nhân</th><th>Kết quả</th><th>Thiếu</th><th>Nhận diện</th>
                <th>Hướng</th><th>Hành động</th><th>Thời gian</th><th>Đánh giá</th><th /></tr>
            </thead>
            <tbody>
              {isLoading ? <EmptyRow colSpan={11}><Spinner size="sm" /></EmptyRow>
                : !ds.length ? <EmptyRow colSpan={11}>Không có lượt kiểm tra nào.</EmptyRow>
                  : ds.map((c) => (
                    <tr key={c.id}>
                      <td>{c.anh ? <img className="sg-thumb" src={c.anh} alt={`Ảnh lượt ${c.id}`} loading="lazy" onClick={() => setCheckId(c.id)} />
                        : <span className="sg-thumb sg-thumb--empty" />}</td>
                      <td className="text-nowrap">{ngay(c.thoi_diem)}<br /><b>{gio(c.thoi_diem, true)}</b></td>
                      <td>{c.cong_nhan
                        ? <><Link to={`/cong-nhan/${c.cong_nhan.id}`} style={{ fontWeight: 600 }}>{c.cong_nhan.ten}</Link><div className="sg-sub">{c.cong_nhan.ma}</div></>
                        : '—'}</td>
                      <td><StatusBadge map={KET_QUA} value={c.ket_qua} /></td>
                      <td className="small text-danger">{thieuText(c.thieu)}</td>
                      <td><StatusBadge map={MAT} value={c.trang_thai_mat} />{c.diem != null && <div className="sg-sub">điểm {c.diem.toFixed(2)}</div>}</td>
                      <td>{HUONG[c.huong] ?? '—'}</td>
                      <td><StatusBadge map={HANH_DONG} value={c.hanh_dong} /></td>
                      <td className="small text-nowrap">{c.thoi_gian_ms != null ? `${(c.thoi_gian_ms / 1000).toFixed(1)} s` : ''}</td>
                      <td><ReviewBadge value={c.danh_gia} /></td>
                      <td className="text-end text-nowrap">
                        <Button size="sm" variant="outline-secondary" className="me-1" onClick={() => setCheckId(c.id)}>Chi tiết</Button>
                        {c.hanh_dong === 'khong_ghi' && (
                          <Button size="sm" variant="outline-primary" onClick={() => setManual(c)}>Chấm thủ công</Button>
                        )}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </Table>
        </div>
        <Card.Footer className="d-flex align-items-center justify-content-between flex-wrap gap-2">
          <span className="small" style={{ color: 'var(--text-secondary)' }}>Trang {data?.trang ?? 1}/{Math.max(1, data?.so_trang ?? 1)}</span>
          <Pager page={filter.trang} pages={data?.so_trang ?? 1} onChange={(p) => setFilter({ trang: p })} />
        </Card.Footer>
      </Card>

      <CheckDetailModal id={checkId} onHide={() => setCheckId(null)} />
      {manual && <ChamCongModal luot={manual} onClose={() => setManual(null)} />}
    </div>
  )
}
