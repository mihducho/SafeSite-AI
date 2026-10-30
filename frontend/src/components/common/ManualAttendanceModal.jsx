import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Button, Form, Modal, Spinner } from 'react-bootstrap'
import { CircleAlert, ClipboardList, DoorClosed, FileClock, Pencil, Plus, Timer, Trash2, X } from 'lucide-react'
import { huyPhep, huyPhien, layDanhSachCongNhan, layNgayCong, suaPhien, themPhien } from '../../api/endpoints.js'
import { useLamMoiCong } from '../../hooks/useLamMoiCong.js'
import { gio, gioPhutChu, hhmm, ngay as ngayVN, soVN, thuNgay } from '../../lib/format.js'
import { NHAT_KY, trangThaiNgay } from '../../lib/labels.js'
import { toast } from '../../lib/toast.js'
import { LeaveForm } from './LeaveModal.jsx'
import SessionList from './SessionList.jsx'
import { EmptyState, Pill, Skeleton, Tabs, TimeInput } from './ui.jsx'

const MO_TA_THAO_TAC = {
  them: 'Thêm phiên',
  sua: 'Sửa giờ của phiên',
  dong: 'Đóng phiên (nhập giờ ra)',
  huy: 'Huỷ phiên',
}

/** Dòng tóm tắt số liệu của ngày: giờ làm, muộn, về sớm, ra ngoài, công quy đổi */
function DaySummary({ r }) {
  const parts = [
    r.so_phut_lam ? `Làm ${gioPhutChu(r.so_phut_lam)}` : null,
    r.di_muon_phut ? `Muộn ${r.di_muon_phut} phút` : null,
    r.ve_som_phut && r.gio_ra ? `Về sớm ${r.ve_som_phut} phút` : null,
    r.phut_ra_ngoai ? `Ra ngoài ${r.phut_ra_ngoai} phút (${r.so_lan_ra_ngoai} lần)` : null,
    r.phut_cong_tac ? `Công tác ${r.phut_cong_tac} phút` : null,
    r.cong_quy_doi ? `Công quy đổi ${soVN(r.cong_quy_doi)}` : null,
  ].filter(Boolean)
  return <div className="small muted num">{parts.join(' · ') || 'Chưa có số liệu công'}</div>
}

/** Nhật ký lưu giờ có giây (giờ ở cổng chính xác tới giây); giây ":00" (giờ nhập tay) thì bỏ cho gọn: 17:00:00 -> 17:00 */
const boGiay00 = (s) => s?.replace(/\b(\d{2}:\d{2}):00\b/g, '$1')

/**
 * Ngày công của 1 công nhân: thao tác THEO PHIÊN (thêm, sửa giờ vào / ra, đóng phiên thiếu giờ ra, huỷ), phép của ngày,
 * nhật ký sửa. Bắt buộc lý do; lỗi của backend hiện bằng câu tiếng Việt ngay trong hộp.
 * worker = { id, ma, ten } hoặc null (lượt "không nhận ra": cán bộ chọn người). ngay = YYYY-MM-DD.
 * gioVao / gioRa: giờ từ lượt kiểm tra (điền sẵn thao tác phù hợp); focusSegmentId: mở sẵn "Đóng phiên" cho phiên đó.
 */
export default function ManualAttendanceModal({ worker, ngay, gioVao = '', gioRa = '', note, tab: tab0 = 'phien',
  focusSegmentId, onClose }) {
  const lamMoi = useLamMoiCong()
  const [workerId, setWorkerId] = useState(worker?.id ?? '')
  const [tab, setTab] = useState(tab0)
  const [mode, setMode] = useState(null)      // { type: them | sua | dong | huy, seg }
  const [vao, setVao] = useState('')
  const [ra, setRa] = useState('')
  const [lyDo, setLyDo] = useState('')
  const [error, setError] = useState('')
  const [addLeave, setAddLeave] = useState(false)
  const [cancelLeave, setCancelLeave] = useState(null)   // phép đang huỷ
  const prefilled = useRef(false)

  const { data: workers } = useQuery({
    queryKey: ['cong-nhan', { trang_thai: 'dang_lam' }],
    queryFn: () => layDanhSachCongNhan({ trang_thai: 'dang_lam' }),
    enabled: !worker,
  })
  const { data: r, isLoading } = useQuery({
    queryKey: ['ngay-cong', Number(workerId), ngay],
    queryFn: () => layNgayCong(workerId, ngay),
    enabled: !!workerId,
  })
  const phien = r?.phien ?? []
  const conHieuLuc = phien.filter((p) => p.trang_thai !== 'huy')
  const ten = worker?.ten ?? r?.ho_ten
  const ma = worker?.ma ?? r?.ma

  const open = (type, seg, preset = {}) => {
    setMode({ type, seg })
    setVao(preset.vao ?? (type === 'sua' ? seg?.vao ?? '' : ''))
    setRa(preset.ra ?? (type === 'sua' ? seg?.ra ?? '' : ''))
    setError('')
  }

  // Mở từ 1 lượt kiểm tra / Việc cần xử lý: chọn sẵn thao tác hợp lý (chỉ 1 lần, khi đã có dữ liệu ngày)
  useEffect(() => {
    if (!r || prefilled.current) return
    prefilled.current = true
    const dangMo = conHieuLuc.find((p) => p.trang_thai === 'mo' || p.trang_thai === 'thieu_gio_ra')
    if (focusSegmentId) {
      const seg = phien.find((p) => p.id === focusSegmentId)
      if (seg) open('dong', seg)
    } else if (gioRa) {
      if (dangMo) open('dong', dangMo, { ra: gioRa })
      else if (conHieuLuc.length) open('sua', conHieuLuc[conHieuLuc.length - 1], { ra: gioRa })
      else open('them', null, { ra: gioRa })
    } else if (gioVao) {
      open('them', null, { vao: gioVao })
    }
  }, [r])  // eslint-disable-line react-hooks/exhaustive-deps

  const done = (msg) => {
    toast.success(msg)
    lamMoi()
    setMode(null)
    setLyDo('')
  }
  const save = useMutation({
    mutationFn: ({ type, seg, body }) => (
      type === 'them' ? themPhien({ worker_id: Number(workerId), ngay, ...body })
        : type === 'huy' ? huyPhien(seg.id, body.ly_do)
          : suaPhien(seg.id, body)),
    meta: { silent: true },
    onSuccess: (_, { type }) => done(type === 'them' ? 'Đã thêm phiên' : type === 'huy' ? 'Đã huỷ phiên'
      : type === 'dong' ? 'Đã đóng phiên' : 'Đã sửa giờ của phiên'),
    onError: (err) => setError(err.message),
  })
  const huyP = useMutation({
    mutationFn: ({ id, lyDoHuy }) => huyPhep(id, lyDoHuy),
    meta: { silent: true },
    onSuccess: () => { setCancelLeave(null); done('Đã huỷ phép') },
    onError: (err) => setError(err.message),
  })

  const submit = (e) => {
    e.preventDefault()
    try {
      const body = { ly_do: lyDo }
      if (mode.type === 'them') {
        body.gio_vao = hhmm(vao, 'Giờ vào')
        body.gio_ra = hhmm(ra, 'Giờ ra')
        if (!body.gio_vao) throw new Error('Nhập giờ vào của phiên.')
      } else if (mode.type === 'sua') {
        const v = hhmm(vao, 'Giờ vào')
        const o = hhmm(ra, 'Giờ ra')
        if (v && v !== mode.seg.vao) body.gio_vao = v
        if (o && o !== mode.seg.ra) body.gio_ra = o
        if (!body.gio_vao && !body.gio_ra) throw new Error('Giờ nhập giống giờ đang có, không có gì để sửa.')
      } else if (mode.type === 'dong') {
        body.gio_ra = hhmm(ra, 'Giờ ra')
        if (!body.gio_ra) throw new Error('Nhập giờ ra để đóng phiên.')
      }
      if (!lyDo.trim()) throw new Error('Bắt buộc ghi lý do khi chấm công thủ công.')
      setError('')
      save.mutate({ type: mode.type, seg: mode.seg, body })
    } catch (err) { setError(err.message) }
  }

  const [stText, stTone] = r ? trangThaiNgay(r) : ['', 'neutral']
  const phepHieuLuc = r?.phep ?? []

  return (
    <Modal show onHide={onClose} centered size="lg" backdrop="static" className="day-modal">
      <Modal.Header closeButton>
        <Modal.Title>Ngày công</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="day-modal__head">
          <div style={{ minWidth: 0 }}>
            {ten ? <div style={{ fontWeight: 600 }}>{ten} <span className="muted" style={{ fontWeight: 400 }}>· {ma}</span></div> : null}
            <div className="small muted">{thuNgay(ngay)}{note ? ` · ${note}` : ''}</div>
          </div>
          {r && (
            <div className="text-end">
              <div className="d-flex gap-1 justify-content-end flex-wrap">
                <Pill tone={stTone}>{stText}</Pill>
                {(r.muon_co_phep || r.som_co_phep || phepHieuLuc.length > 0) && <Pill tone="info" className="no-dot">Có phép</Pill>}
                {r.co_sua_tay && <Pill tone="neutral" className="no-dot">Sửa tay</Pill>}
              </div>
              <DaySummary r={r} />
            </div>
          )}
        </div>

        {!worker && (
          <Form.Group className="mb-3">
            <Form.Label htmlFor="m-worker">Công nhân</Form.Label>
            <Form.Select id="m-worker" value={workerId} onChange={(e) => { setWorkerId(e.target.value); prefilled.current = false }}>
              <option value="">Chọn công nhân</option>
              {(workers?.ds ?? []).map((w) => <option key={w.id} value={w.id}>{w.code} – {w.full_name}</option>)}
            </Form.Select>
          </Form.Group>
        )}

        {workerId && (
          <div className="day-modal__tabs">
            <Tabs active={tab} onChange={(k) => { setTab(k); setError('') }} tabs={[
              { key: 'phien', label: 'Phiên làm việc', icon: Timer, count: conHieuLuc.length },
              { key: 'phep', label: 'Phép', icon: ClipboardList, count: phepHieuLuc.length },
              { key: 'nhat_ky', label: 'Nhật ký sửa', icon: FileClock, count: r?.nhat_ky?.length },
            ]} />
          </div>
        )}

        {!workerId ? null : isLoading || !r ? <Skeleton height={120} style={{ marginTop: 12 }} />
          : tab === 'phien' ? (
            <div className="mt-3">
              <SessionList phien={phien} actions={(p) => p.trang_thai === 'huy' ? null : (
                <>
                  {(p.trang_thai === 'mo' || p.trang_thai === 'thieu_gio_ra') && (
                    <Button size="sm" variant={p.trang_thai === 'thieu_gio_ra' ? 'primary' : 'secondary'} onClick={() => open('dong', p)}>
                      <DoorClosed size={15} />Nhập giờ ra
                    </Button>
                  )}
                  <Button size="sm" variant="secondary" className="btn-icon" title="Sửa giờ" aria-label="Sửa giờ" onClick={() => open('sua', p)}><Pencil size={15} /></Button>
                  <Button size="sm" variant="secondary" className="btn-icon" title="Huỷ phiên" aria-label="Huỷ phiên" onClick={() => open('huy', p)}><Trash2 size={15} /></Button>
                </>
              )} />
              {!mode && (
                <Button variant="secondary" size="sm" className="mt-3" onClick={() => open('them', null)}><Plus size={16} />Thêm phiên</Button>
              )}
              {mode && (
                <Form onSubmit={submit} noValidate className="action-panel mt-3">
                  <div className="action-panel__head">
                    <b>{MO_TA_THAO_TAC[mode.type]}</b>
                    {mode.seg && <span className="muted num">phiên {mode.seg.vao} – {mode.seg.ra ?? 'chưa ra'}</span>}
                    <button type="button" className="btn btn-text btn-icon btn-sm ms-auto" aria-label="Đóng" onClick={() => { setMode(null); setError('') }}><X size={16} /></button>
                  </div>
                  {mode.type === 'huy'
                    ? <p className="small muted mb-3">Phiên bị huỷ không còn tính vào công; vẫn giữ trong nhật ký.</p>
                    : (
                      <div className="row g-3 mb-3">
                        {mode.type !== 'dong' && (
                          <Form.Group className="col-6"><Form.Label htmlFor="m-in">Giờ vào</Form.Label><TimeInput id="m-in" value={vao} onChange={setVao} /></Form.Group>
                        )}
                        <Form.Group className="col-6">
                          <Form.Label htmlFor="m-out">Giờ ra{mode.type === 'them' ? ' (trống = đang làm)' : ''}</Form.Label>
                          <TimeInput id="m-out" value={ra} onChange={setRa} autoFocus={mode.type === 'dong'} />
                        </Form.Group>
                      </div>
                    )}
                  <Form.Group>
                    <Form.Label htmlFor="m-reason">Lý do (bắt buộc)</Form.Label>
                    <Form.Control id="m-reason" as="textarea" rows={2} maxLength={500} value={lyDo} onChange={(e) => setLyDo(e.target.value)}
                      placeholder="vd Camera cổng hỏng, tổ trưởng xác nhận ra lúc 17:00" />
                  </Form.Group>
                  {error && <div className="note bad mt-3" id="m-error"><CircleAlert size={18} />{error}</div>}
                  <div className="d-flex justify-content-end gap-2 mt-3">
                    <Button variant="secondary" onClick={() => { setMode(null); setError('') }} disabled={save.isPending}>Huỷ</Button>
                    <Button type="submit" variant={mode.type === 'huy' ? 'danger' : 'primary'} disabled={save.isPending}>
                      {save.isPending && <Spinner size="sm" />}{mode.type === 'huy' ? 'Huỷ phiên' : 'Lưu'}
                    </Button>
                  </div>
                </Form>
              )}
              <p className="small muted mt-3 mb-0">Giờ dạng 24 giờ HH:MM. Mỗi thao tác ghi 1 dòng nhật ký (giá trị cũ, mới, người sửa, lý do).</p>
            </div>
          ) : tab === 'phep' ? (
            <div className="mt-3">
              {!phepHieuLuc.length && !addLeave && <div className="small muted">Ngày này chưa có phép.</div>}
              {phepHieuLuc.length > 0 && (
                <ul className="leave-list">
                  {phepHieuLuc.map((p) => (
                    <li key={p.id}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 600 }}>{p.mo_ta}</div>
                        <div className="small muted">{p.ly_do}</div>
                      </div>
                      {cancelLeave?.id === p.id ? (
                        <Form className="d-flex gap-2 align-items-start" onSubmit={(e) => {
                          e.preventDefault()
                          if (!cancelLeave.lyDo?.trim()) { setError('Bắt buộc ghi lý do huỷ phép.'); return }
                          huyP.mutate({ id: p.id, lyDoHuy: cancelLeave.lyDo })
                        }}>
                          <Form.Control size="sm" placeholder="Lý do huỷ" value={cancelLeave.lyDo ?? ''} autoFocus
                            onChange={(e) => setCancelLeave({ ...cancelLeave, lyDo: e.target.value })} />
                          <Button size="sm" type="submit" variant="danger" disabled={huyP.isPending}>Huỷ phép</Button>
                          <Button size="sm" variant="secondary" className="btn-icon" aria-label="Thôi" onClick={() => setCancelLeave(null)}><X size={15} /></Button>
                        </Form>
                      ) : (
                        <Button size="sm" variant="secondary" onClick={() => { setCancelLeave({ id: p.id }); setError('') }}><Trash2 size={15} />Huỷ</Button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {error && tab === 'phep' && <div className="note bad mt-3"><CircleAlert size={18} />{error}</div>}
              {addLeave
                ? <div className="action-panel mt-3"><LeaveForm worker={{ id: Number(workerId), ma, ten }} defaults={{ ngay }} lockDate
                    onDone={() => setAddLeave(false)} onCancel={() => setAddLeave(false)} /></div>
                : <Button variant="secondary" size="sm" className="mt-3" onClick={() => setAddLeave(true)}><Plus size={16} />Thêm phép</Button>}
            </div>
          ) : (
            <div className="mt-3">
              {!r.nhat_ky?.length ? <EmptyState icon={FileClock} title="Chưa có thao tác sửa nào" text="Mỗi lần chấm tay, thêm / huỷ phép sẽ ghi lại ở đây." />
                : (
                  <div className="table-wrap no-max">
                    <table className="sg-table">
                      <thead><tr><th>Thời điểm</th><th>Người sửa</th><th>Thao tác</th><th>Cũ → mới</th><th>Lý do</th></tr></thead>
                      <tbody>
                        {r.nhat_ky.map((n) => (
                          <tr key={n.id}>
                            <td className="nowrap num mono-meta">{gio(n.thoi_diem)} {ngayVN(n.thoi_diem).slice(0, 5)}</td>
                            <td className="nowrap">{n.nguoi_sua ?? '—'}</td>
                            <td className="nowrap">{NHAT_KY[n.hanh_dong] ?? n.hanh_dong}</td>
                            <td className="num mono-meta">{boGiay00(n.gia_tri_cu) ?? '—'} → {boGiay00(n.gia_tri_moi) ?? '—'}</td>
                            <td><span className="note-cell" title={n.ly_do ?? ''}>{n.ly_do}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
            </div>
          )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onClose}>Đóng</Button>
      </Modal.Footer>
    </Modal>
  )
}
