import { useEffect, useRef, useState } from 'react'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Spinner } from 'react-bootstrap'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { CalendarDays, CalendarRange, ChevronLeft, ChevronRight, History, PencilLine, Users } from 'lucide-react'
import { layBangCongNgay, layDanhSachToDoi } from '../api/endpoints.js'
import ManualAttendanceModal from '../components/common/ManualAttendanceModal.jsx'
import { Card, EmptyRow, PageHead, Person, Pill, RowMenu, SkeletonRows } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents } from '../lib/events.js'
import { doiNgay, gioPhutChu, thuNgay } from '../lib/format.js'
import { trangThaiNgay } from '../lib/labels.js'

// Thẻ tóm tắt: bấm vào thì lọc bảng
const SUMMARY = [
  { key: 'da_vao', label: 'Đã vào', test: (r) => !!r.gio_vao },
  { key: 'di_muon', label: 'Đi muộn', test: (r) => r.di_muon_phut > 0, tone: 'warn' },
  { key: 'co_mat', label: 'Đang có mặt', test: (r) => !!r.gio_vao && !r.gio_ra && !r.thieu_gio_ra, tone: 'ok' },
  { key: 'chua_ra', label: 'Chưa ra', test: (r) => r.thieu_gio_ra, tone: 'bad' },
  { key: 'chua_vao', label: 'Chưa vào', test: (r) => !r.gio_vao },
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
  const [row, setRow] = useState(null)
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

  return (
    <div className="page">
      <PageHead title="Bảng công ngày" sub={data ? `${ds.length} công nhân${isFetching ? ' · đang cập nhật…' : ''}` : ' '}>
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

      <div className="summary mb-3">
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
          <table className="sg-table">
            <thead>
              <tr><th>Công nhân</th><th>Tổ đội</th><th>Giờ vào</th><th>Giờ ra</th><th>Đi muộn</th><th>Về sớm</th>
                <th>Giờ làm</th><th>Trạng thái</th><th>Ghi chú</th><th className="shrink" /></tr>
            </thead>
            <tbody>
              {isLoading ? <SkeletonRows cols={10} />
                : !rows.length ? (
                  <EmptyRow colSpan={10} icon={Users} title={only ? 'Không có ai trong nhóm này' : 'Chưa có công nhân nào'}
                    text={only ? 'Bấm lại vào thẻ tóm tắt để xem tất cả.' : 'Thêm công nhân ở trang Công nhân.'} />
                ) : rows.map((r) => {
                  const [text, tone] = trangThaiNgay(r)
                  return (
                    <tr key={r.worker_id}>
                      <td><Person name={r.ho_ten} code={r.ma} workerId={r.worker_id} to={`/cong-nhan/${r.worker_id}`} /></td>
                      <td>{r.to_doi}</td>
                      <td className="num" style={{ fontWeight: 600 }}>{r.gio_vao}</td>
                      <td className="num" style={{ fontWeight: 600 }}>{r.gio_ra}</td>
                      <td>{r.di_muon_phut > 0 && <Pill tone="warn">+{r.di_muon_phut} phút</Pill>}</td>
                      <td className="nowrap">{r.ve_som_phut > 0 && r.gio_ra ? `${r.ve_som_phut} phút` : ''}</td>
                      <td className="nowrap">{r.gio_ra ? gioPhutChu(r.so_phut_lam) : ''}</td>
                      <td><Pill tone={tone}>{text}</Pill></td>
                      <td><span className="note-cell" title={r.ghi_chu ?? ''}>{r.ghi_chu}</span></td>
                      <td className="shrink">
                        <RowMenu items={[
                          { label: 'Chấm thủ công', icon: PencilLine, onClick: () => setRow(r) },
                          { label: 'Xem lịch sử kiểm tra', icon: History, onClick: () => navigate(`/lich-su?ngay=${r.ngay}&cong_nhan_id=${r.worker_id}`) },
                        ]} />
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      </Card>

      {row && (
        <ManualAttendanceModal worker={{ id: row.worker_id, ma: row.ma, ten: row.ho_ten }} ngay={row.ngay}
          gioVao={row.gio_vao ?? ''} gioRa={row.gio_ra ?? ''} onClose={() => setRow(null)} />
      )}
    </div>
  )
}
