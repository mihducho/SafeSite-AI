import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ClipboardX, DoorOpen, ImageOff, ListTodo, LogIn, MonitorPlay, ScanFace, UserCheck, Users } from 'lucide-react'
import { layTongQuan } from '../api/endpoints.js'
import CheckDetailModal from '../components/common/CheckDetailModal.jsx'
import { Card, EmptyState, PageHead, Person, Pill, Skeleton, StatCard, StatusBadge } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents, useGateStatus, useWsState } from '../lib/events.js'
import { gio, thuNgay } from '../lib/format.js'
import { HANH_DONG, KET_QUA, MAT, thieuText, trangThaiCong } from '../lib/labels.js'

// ─── biểu đồ cột: số lượt theo giờ hôm nay, tô theo MÀU MÀN HÌNH CỔNG (backend phân loại, giống "lượt không đạt") ──
const C_DAT = '#059669'    // xanh: đã ghi công (vào / ra / bỏ qua trùng)
const C_KHONG = '#DC2626'  // đỏ: vào thiếu bảo hộ
const C_VANG = '#D97706'   // vàng: chưa nhận ra, nhiều người, ngoài giờ vào ca...
const tong = (r) => r.xanh + r.do + r.vang

function HourChart({ rows, nowHour }) {
  const used = rows.filter((r) => tong(r) > 0).map((r) => r.gio)
  const from = Math.min(6, ...used)
  const to = Math.max(18, nowHour, ...used)
  const shown = rows.filter((r) => r.gio >= from && r.gio <= to)
  const peak = Math.max(1, ...shown.map(tong))
  const top = peak <= 4 ? 4 : Math.ceil(peak / 4) * 4          // trục dọc chia 4 vạch số nguyên
  const ticks = [top, (top * 3) / 4, top / 2, top / 4, 0]
  return (
    <div className="chart">
      <div className="chart__y">{ticks.map((v) => <span key={v}>{Number.isInteger(v) ? v : ''}</span>)}</div>
      <div className="chart__plot">
        <div className="chart__gridbox">
          {ticks.map((v) => <i key={v} className={`chart__grid${v === 0 ? ' base' : ''}`} style={{ bottom: `${(v / top) * 100}%` }} />)}
        </div>
        <div className="chart__bars">
          {shown.map((r) => {
            const total = tong(r)
            return (
              <div key={r.gio} className="chart__col"
                title={`${r.gio} giờ: ${r.xanh} đã ghi công, ${r.do} không đạt, ${r.vang} cần làm lại`}>
                <div className="chart__stack" style={{ height: `${(total / top) * 100}%` }}>
                  {r.vang > 0 && <span style={{ background: C_VANG, flexGrow: r.vang }} />}
                  {r.do > 0 && <span style={{ background: C_KHONG, flexGrow: r.do }} />}
                  {r.xanh > 0 && <span style={{ background: C_DAT, flexGrow: r.xanh }} />}
                </div>
                <span className={`chart__x${r.gio === nowHour ? ' now' : ''}`}>{r.gio}h</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function GateCard({ last }) {
  const st = useGateStatus()
  const ws = useWsState()
  const [, sentence, tone] = trangThaiCong(st, ws)
  return (
    <Card title="Trạng thái cổng" className="h-100">
      <div className={`note ${tone === 'ok' ? 'ok' : tone === 'bad' ? 'bad' : 'warn'}`} style={{ fontWeight: 600 }}>
        <span className={`gate-pill ${tone}`} style={{ background: 'transparent', borderColor: 'transparent', padding: 0, height: 'auto' }}><i /></span>
        {sentence}
      </div>
      <div className="small muted mt-3 mb-2">Lượt gần nhất</div>
      {last ? (
        <div className="d-flex gap-3 align-items-center">
          {last.anh ? <img className="thumb" style={{ width: 64, height: 84 }} src={last.anh} alt="" />
            : <span className="thumb thumb--empty" style={{ width: 64, height: 84 }}><ImageOff size={18} strokeWidth={1.5} /></span>}
          <div style={{ minWidth: 0 }}>
            <div className="person__name">{last.cong_nhan?.ten ?? (MAT[last.trang_thai_mat] ?? ['Không nhận ra'])[0]}</div>
            <div className="small muted num mono-meta mb-2">{gio(last.thoi_diem)}{last.cong_nhan ? ` · ${last.cong_nhan.ma}` : ''}</div>
            <StatusBadge map={KET_QUA} value={last.ket_qua} />
          </div>
        </div>
      ) : <div className="small muted">Chưa có lượt nào.</div>}
      <Link to="/man-hinh-cong" className="btn btn-primary w-100 mt-3"><MonitorPlay size={16} strokeWidth={1.5} />Mở màn hình cổng</Link>
    </Card>
  )
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const qc = useQueryClient()
  const { tz } = useWebConfig()
  const [checkId, setCheckId] = useState(null)
  const lastTop = useRef(null)
  const [newIds, setNewIds] = useState([])
  const reloadTimer = useRef(null)

  const { data, isLoading } = useQuery({ queryKey: ['tong-quan'], queryFn: layTongQuan, refetchInterval: 60_000 })

  // lượt mới (WebSocket) -> tải lại số liệu (gộp nhiều sự kiện liền nhau)
  useGateEvents((ev) => {
    if (ev.loai !== 'luot') return
    clearTimeout(reloadTimer.current)
    reloadTimer.current = setTimeout(() => qc.invalidateQueries({ queryKey: ['tong-quan'] }), 300)
  })
  useEffect(() => () => clearTimeout(reloadTimer.current), [])

  const luot = data?.luot_moi_nhat ?? []
  useEffect(() => {
    if (!luot.length) return
    if (lastTop.current !== null) setNewIds(luot.filter((c) => c.id > lastTop.current).map((c) => c.id))
    lastTop.current = luot[0].id
  }, [luot])

  const nowHour = Number(new Intl.DateTimeFormat('en-GB', { hour: '2-digit', hour12: false, timeZone: tz }).format(new Date()))
  const d = data ?? {}

  return (
    <div className="page">
      <PageHead title="Tổng quan hôm nay" sub={data ? thuNgay(data.ngay) : ' '} />

      <div className="grid grid-5 mb-3">
        <StatCard icon={Users} tone="neutral" label="Công nhân đang làm" value={d.so_cong_nhan} loading={isLoading}
          sub="trong danh sách đang làm việc" />
        <StatCard icon={LogIn} tone="ok" label="Đã vào hôm nay" value={d.da_vao} loading={isLoading}
          sub={data ? `${d.da_vao}/${d.so_cong_nhan} công nhân` : ''} />
        <StatCard icon={UserCheck} tone="primary" label="Đang có mặt" value={d.dang_co_mat} loading={isLoading}
          sub={data ? (d.da_vao ? `${d.da_vao - d.dang_co_mat} người đã ra về` : 'chưa ai vào') : ''} />
        <StatCard icon={ClipboardX} tone="bad" label="Lượt không đạt hôm nay" value={d.luot_khong_dat} loading={isLoading}
          sub={data ? `vào thiếu bảo hộ · trong ${d.so_luot} lượt` : ''} />
        <Link to="/viec-can-xu-ly" className="stat-link" aria-label="Mở danh sách Việc cần xử lý">
          <StatCard icon={ListTodo} tone={d.viec_can_xu_ly ? 'warn' : 'ok'} label="Việc cần xử lý" value={d.viec_can_xu_ly}
            loading={isLoading} sub={data ? (d.viec_can_xu_ly ? 'thiếu giờ ra, muộn / sớm chưa có phép' : 'không có việc tồn') : ''} />
        </Link>
      </div>

      <div className="grid grid-2-1 mb-3">
        <Card title="Lượt kiểm tra theo giờ hôm nay"
          end={<div className="legend"><span><i style={{ background: C_DAT }} />Đã ghi công</span><span><i style={{ background: C_KHONG }} />Không đạt</span><span><i style={{ background: C_VANG }} />Cần làm lại</span></div>}>
          {isLoading ? <Skeleton height={220} /> : <HourChart rows={d.luot_theo_gio ?? []} nowHour={nowHour} />}
        </Card>
        <GateCard last={luot[0]} />
      </div>

      <div className="grid grid-2-1 start">
        <Card title="Lượt kiểm tra mới nhất" sub="cập nhật trực tiếp" flush
          end={<Link to="/lich-su" className="btn btn-text btn-sm">Xem tất cả</Link>}>
          {isLoading ? <div className="sg-card__body"><Skeleton height={44} /><Skeleton height={44} style={{ marginTop: 12 }} /></div>
            : !luot.length ? <EmptyState icon={ScanFace} title="Chưa có lượt kiểm tra nào" text="Lượt kiểm tra ở cổng sẽ hiện ở đây ngay khi có người đứng vào." />
              : (
                <table className="sg-table">
                  <tbody>
                    {luot.map((c) => (
                      <tr key={c.id} className={`clickable${newIds.includes(c.id) ? ' flash' : ''}`} onClick={() => setCheckId(c.id)}>
                        <td className="shrink">
                          {c.anh ? <img className="thumb" src={c.anh} alt="" loading="lazy" /> : <span className="thumb thumb--empty"><ImageOff size={17} strokeWidth={1.5} /></span>}
                        </td>
                        <td>
                          {c.cong_nhan
                            ? <div className="person__text"><span className="person__name">{c.cong_nhan.ten}</span><span className="person__sub num">{c.cong_nhan.ma}</span></div>
                            : <span className="text-warn" style={{ fontWeight: 600 }}>{(MAT[c.trang_thai_mat] ?? ['Không nhận ra'])[0]}</span>}
                        </td>
                        <td>
                          <StatusBadge map={KET_QUA} value={c.ket_qua} />
                          {c.thieu.length > 0 && <div className="small text-bad mt-1">{thieuText(c.thieu)}</div>}
                        </td>
                        <td className="muted nowrap">{(HANH_DONG[c.hanh_dong] ?? [''])[0]}</td>
                        <td className="right num mono-meta" style={{ fontWeight: 600 }}>{gio(c.thoi_diem, true)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
        </Card>
        <Card title="Đang có mặt" sub={data ? `${d.dang_co_mat_ds.length} người` : ''} flush>
          {isLoading ? <div className="sg-card__body"><Skeleton height={40} /></div>
            : !d.dang_co_mat_ds.length ? <EmptyState icon={DoorOpen} title="Chưa có ai đang có mặt" text="Công nhân qua cổng đủ bảo hộ sẽ được ghi giờ vào và hiện ở đây." />
              : (
                <table className="sg-table">
                  <tbody>
                    {d.dang_co_mat_ds.map((p) => (
                      <tr key={p.worker_id}>
                        <td><Person name={p.ho_ten} code={p.ma} sub={p.to_doi} workerId={p.worker_id} to={`/cong-nhan/${p.worker_id}`} /></td>
                        <td className="right num"><Pill tone="ok">vào {p.gio_vao}</Pill></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
        </Card>
      </div>
      <CheckDetailModal id={checkId} onHide={() => setCheckId(null)} />
    </div>
  )
}
