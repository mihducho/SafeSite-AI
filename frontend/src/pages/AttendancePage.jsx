import { Fragment, useEffect, useRef, useState } from 'react'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Spinner } from 'react-bootstrap'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  CalendarDays, CalendarRange, ChevronDown, ChevronLeft, ChevronRight, ClipboardList, FileClock, History, PencilLine,
  Users,
} from 'lucide-react'
import { layBangCongNgay, layDanhSachToDoi } from '../api/endpoints.js'
import CheckDetailModal from '../components/common/CheckDetailModal.jsx'
import DayStatus from '../components/common/DayStatus.jsx'
import LeaveModal from '../components/common/LeaveModal.jsx'
import ManualAttendanceModal from '../components/common/ManualAttendanceModal.jsx'
import SessionList from '../components/common/SessionList.jsx'
import { Card, EmptyRow, PageHead, Person, Pill, RowMenu, SkeletonRows } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents } from '../lib/events.js'
import { doiNgay, gioPhutChu, soVN, thuNgay } from '../lib/format.js'

// Thẻ tóm tắt: bấm vào thì lọc bảng. Mọi điều kiện dựa trên số liệu / trạng thái BACKEND trả về.
const SUMMARY = [
  { key: 'da_vao', label: 'Đã vào', test: (r) => !!r.gio_vao },
  { key: 'dang_lam', label: 'Đang làm', test: (r) => r.trang_thai_ngay === 'dang_lam', tone: 'ok' },
  { key: 'di_muon', label: 'Đi muộn', test: (r) => r.di_muon_phut > 0, tone: 'warn' },
  { key: 'thieu_gio_ra', label: 'Thiếu giờ ra', test: (r) => r.thieu_gio_ra, tone: 'bad' },
  { key: 'can_xu_ly', label: 'Cần xử lý', test: (r) => r.thieu_gio_ra || r.can_giai_trinh, tone: 'bad' },
  { key: 'chua_vao', label: 'Chưa vào / vắng', test: (r) => r.trang_thai_ngay === 'chua_vao' || r.trang_thai_ngay === 'vang' },
]

/** "‹ Thứ Sáu, 30/10/2026 ›": bấm vào chữ để chọn ngày */
function DayPicker({ value, onChange }) {
  const ref = useRef(null)
  return (
    <div className="day-picker">
      <Button variant="secondary" className="btn-icon" onClick={() => onChange(doiNgay(value, -1))} aria-label="Ngày trước"><ChevronLeft size={18} /></Button>
      <div className="day-picker__label" role="button" tabIndex={0} onClick={() => { try { ref.current?.showPicker?.() } catch { /* trình duyệt cũ */ } }}>
        <CalendarDays size={17} />{thuNgay(value)}
        <input ref={ref} type="date" value={value} onChange={(e) => e.target.value && onChange(e.target.value)} aria-label="Chọn ngày" tabIndex={-1} />
      </div>
      <Button variant="secondary" className="btn-icon" onClick={() => onChange(doiNgay(value, 1))} aria-label="Ngày sau"><ChevronRight size={18} /></Button>
    </div>
  )
}

export default function AttendancePage() {
  const cfg = useWebConfig()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [dayModal, setDayModal] = useState(null)   // { row, tab }
  const [leave, setLeave] = useState(null)
  const [checkId, setCheckId] = useState(null)
  const [open, setOpen] = useState(() => new Set(params.get('cn') ? [Number(params.get('cn'))] : []))
  const [only, setOnly] = useState(null)       // lọc theo thẻ tóm tắt
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
  useEffect(() => { setOnly(null) }, [ngayXem, toDoi])

  const ds = data?.ds ?? []
  const counts = Object.fromEntries(SUMMARY.map((s) => [s.key, ds.filter(s.test).length]))
  const rows = only ? ds.filter(SUMMARY.find((s) => s.key === only).test) : ds
  const toggle = (id) => setOpen((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n })
  const cols = 11

  return (
    <div className="page">
      <PageHead title="Bảng công ngày" sub={data ? `${ds.length} công nhân${isFetching ? ' · đang cập nhật…' : ''}` : ' '}>
        <Link to="/viec-can-xu-ly" className="btn btn-secondary"><ClipboardList size={18} />Việc cần xử lý</Link>
        <Link to="/bang-cong-thang" className="btn btn-secondary"><CalendarRange size={18} />Bảng công tháng</Link>
      </PageHead>

      <div className="d-flex align-items-center gap-2 flex-wrap mb-3">
        <DayPicker value={ngayXem} onChange={(v) => go({ ngay: v })} />
        <Button variant="secondary" onClick={() => go({ ngay: cfg.today })} disabled={ngayXem === cfg.today}>Hôm nay</Button>
        <Form.Select value={toDoi} onChange={(e) => go({ to_doi: e.target.value })} aria-label="Tổ đội" style={{ width: 200 }}>
          <option value="">Tất cả tổ</option>
          {(teams?.ds ?? []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </Form.Select>
        {isFetching && <Spinner size="sm" />}
      </div>

      <div className="summary summary-6 mb-3">
        {SUMMARY.map((s) => (
          <button key={s.key} type="button" className={`summary__item${only === s.key ? ' active' : ''}`}
            onClick={() => setOnly(only === s.key ? null : s.key)} aria-pressed={only === s.key}>
            <span className="summary__label">{s.label}</span>
            <span className={`summary__value${s.tone && counts[s.key] ? ` text-${s.tone}` : ''}`}>
              {counts[s.key]}{s.key === 'da_vao' && <small>/{ds.length}</small>}
            </span>
          </button>
        ))}
      </div>

      <Card flush>
        <div className="table-wrap">
          <table className="sg-table day-table">
            <thead>
              <tr><th className="shrink" /><th>Công nhân</th><th>Giờ vào</th><th>Giờ ra</th><th>Đi muộn</th><th>Về sớm</th>
                <th>Giờ làm</th><th>Ra ngoài</th><th className="right">Công</th><th>Trạng thái</th><th className="shrink" /></tr>
            </thead>
            <tbody>
              {isLoading ? <SkeletonRows cols={cols} />
                : !rows.length ? (
                  <EmptyRow colSpan={cols} icon={Users} title={only ? 'Không có ai trong nhóm này' : 'Chưa có công nhân nào'}
                    text={only ? 'Bấm lại vào thẻ tóm tắt để xem tất cả.' : 'Thêm công nhân ở trang Công nhân.'} />
                ) : rows.map((r) => {
                  const isOpen = open.has(r.worker_id)
                  const hasSegs = (r.phien?.length ?? 0) > 0
                  return (
                    <Fragment key={r.worker_id}>
                      <tr className={`clickable${isOpen ? ' expanded' : ''}`} onClick={() => toggle(r.worker_id)}>
                        <td className="shrink">
                          <span className={`expand-btn${isOpen ? ' open' : ''}`} aria-label={isOpen ? 'Thu gọn' : 'Xem các phiên'}>
                            <ChevronDown size={16} strokeWidth={1.5} />
                          </span>
                        </td>
                        <td><Person name={r.ho_ten} code={r.ma} sub={r.to_doi} workerId={r.worker_id} to={`/cong-nhan/${r.worker_id}`} /></td>
                        <td className="num" style={{ fontWeight: 600 }}>{r.gio_vao}</td>
                        <td className="num" style={{ fontWeight: 600 }}>{r.gio_ra}</td>
                        <td>{r.di_muon_phut > 0 && <Pill tone={r.muon_co_phep ? 'info' : 'warn'}>+{r.di_muon_phut} phút</Pill>}</td>
                        <td className="nowrap">{r.ve_som_phut > 0 && r.gio_ra ? `${r.ve_som_phut} phút` : ''}</td>
                        <td className="nowrap">{r.so_phut_lam ? gioPhutChu(r.so_phut_lam) : ''}</td>
                        <td className="nowrap">{r.so_lan_ra_ngoai > 0 ? `${r.so_lan_ra_ngoai} lần · ${r.phut_ra_ngoai} phút` : ''}</td>
                        <td className="right num">{hasSegs ? soVN(r.cong_quy_doi) : ''}</td>
                        <td><DayStatus r={r} /></td>
                        <td className="shrink">
                          <RowMenu items={[
                            { label: 'Chấm công thủ công', icon: PencilLine, onClick: () => setDayModal({ row: r, tab: 'phien' }) },
                            { label: 'Thêm phép', icon: ClipboardList, onClick: () => setLeave(r) },
                            { label: 'Nhật ký sửa', icon: FileClock, onClick: () => setDayModal({ row: r, tab: 'nhat_ky' }) },
                            { label: 'Xem lịch sử kiểm tra', icon: History, onClick: () => navigate(`/lich-su?ngay=${r.ngay}&cong_nhan_id=${r.worker_id}`) },
                          ]} />
                        </td>
                      </tr>
                      {isOpen && (
                        <tr className="expand-row">
                          <td />
                          <td colSpan={cols - 1}>
                            <div className="expand-body">
                              <SessionList phien={r.phien} onOpenCheck={setCheckId} />
                              {(r.phep?.length ?? 0) > 0 && (
                                <div className="d-flex gap-2 flex-wrap align-items-center mt-2">
                                  <span className="small muted">Phép:</span>
                                  {r.phep.map((p) => <Pill key={p.id} tone="info" className="no-dot">{p.mo_ta}</Pill>)}
                                </div>
                              )}
                              <div className="d-flex gap-2 mt-2">
                                <Button size="sm" variant="secondary" onClick={() => setDayModal({ row: r, tab: 'phien' })}><PencilLine size={15} />Chấm công thủ công</Button>
                                {r.attendance_id && <Button size="sm" variant="text" onClick={() => setDayModal({ row: r, tab: 'nhat_ky' })}><FileClock size={15} />Nhật ký sửa</Button>}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
            </tbody>
          </table>
        </div>
        <div className="sg-card__foot"><span>Bấm vào một dòng để xem các phiên vào – ra. Trạng thái do máy chủ tính theo quy tắc chấm công.</span></div>
      </Card>

      {dayModal && (
        <ManualAttendanceModal worker={{ id: dayModal.row.worker_id, ma: dayModal.row.ma, ten: dayModal.row.ho_ten }}
          ngay={dayModal.row.ngay} tab={dayModal.tab} onClose={() => setDayModal(null)} />
      )}
      {leave && (
        <LeaveModal worker={{ id: leave.worker_id, ma: leave.ma, ten: leave.ho_ten }} defaults={{ ngay: leave.ngay }}
          onClose={() => setLeave(null)} />
      )}
      <CheckDetailModal id={checkId} onHide={() => setCheckId(null)} />
    </div>
  )
}
