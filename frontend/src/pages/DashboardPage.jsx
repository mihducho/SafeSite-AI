import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Card, Col, Row, Spinner } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import { layTongQuan } from '../api/endpoints.js'
import CheckDetailModal from '../components/common/CheckDetailModal.jsx'
import { Avatar, StatusBadge } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents, useGateStatus, useWsState } from '../lib/events.js'
import { gio, ngay } from '../lib/format.js'
import { HANH_DONG, KET_QUA, MAT, thieuText } from '../lib/labels.js'

// ─── thẻ số liệu ───────────────────────────────────────────────────────────────
function StatCard({ label, value, icon, color, note }) {
  return (
    <div className="stat-card h-100">
      <div className={`stat-card-icon ${color}`}>{icon}</div>
      <div>
        <div className="stat-card-value">{value ?? '—'}</div>
        <div className="stat-card-label">{label}</div>
        {note && <div className="sg-sub">{note}</div>}
      </div>
    </div>
  )
}

// ─── biểu đồ cột số lượt theo giờ hôm nay (không cần thư viện biểu đồ) ─────────
const COLORS = { dat: '#2ed573', khong_dat: '#e74c3c', khac: '#ffc107' }

function HourChart({ rows, nowHour }) {
  const used = rows.filter((r) => r.dat + r.khong_dat + r.khac > 0).map((r) => r.gio)
  const from = Math.min(6, ...used)
  const to = Math.max(18, nowHour, ...used)
  const shown = rows.filter((r) => r.gio >= from && r.gio <= to)
  const max = Math.max(1, ...shown.map((r) => r.dat + r.khong_dat + r.khac))
  return (
    <>
      <div className="sg-bars">
        {shown.map((r) => {
          const total = r.dat + r.khong_dat + r.khac
          return (
            <div key={r.gio} className="sg-bar" title={`${r.gio}h: đạt ${r.dat}, không đạt ${r.khong_dat}, khác ${r.khac}`}>
              <div className="sg-bar__num">{total || ''}</div>
              <div className="sg-bar__stack" style={{ height: `${(total / max) * 100}%` }}>
                {['dat', 'khong_dat', 'khac'].map((k) => r[k] > 0 && (
                  <span key={k} style={{ background: COLORS[k], height: `${(r[k] / total) * 100}%` }} />
                ))}
              </div>
              <div className="sg-bar__label" style={r.gio === nowHour ? { color: 'var(--orange)', fontWeight: 700 } : undefined}>{r.gio}h</div>
            </div>
          )
        })}
      </div>
      <div className="sg-legend mt-2">
        <span><i style={{ background: COLORS.dat }} />Đạt</span>
        <span><i style={{ background: COLORS.khong_dat }} />Không đạt</span>
        <span><i style={{ background: COLORS.khac }} />Khác (không xác định, nhiều người, không có người)</span>
      </div>
    </>
  )
}

function GateCard() {
  const st = useGateStatus()
  const ws = useWsState()
  let color = 'warning'
  let text = 'Đang kết nối…'
  if (ws === 'mat') { color = 'danger'; text = 'Mất kết nối máy chủ' }
  else if (st?.mat_camera) { color = 'danger'; text = 'Mất kết nối camera, đang thử lại' }
  else if (st?.trang_thai === 'dang_chay' && !st.loi) { color = 'success'; text = st.pha === 'KIEM_TRA' ? 'Đang kiểm tra' : 'Đang chạy, chờ người' }
  else if (st?.trang_thai === 'dang_khoi_dong') text = 'Đang khởi động'
  else if (st) { color = 'danger'; text = st.trang_thai === 'tat' ? 'Đang tắt' : `Lỗi${st.loi ? ` – ${st.loi}` : ''}` }
  return (
    <Card className="h-100">
      <Card.Header>Trạng thái cổng</Card.Header>
      <Card.Body>
        <Badge bg={color} text={color === 'warning' ? 'dark' : undefined} style={{ fontSize: '0.95rem', padding: '0.5rem 0.8rem' }}>{text}</Badge>
        <div className="mt-3 small" style={{ color: 'var(--text-secondary)', lineHeight: 1.9 }}>
          <div>Nguồn hình: <b style={{ color: 'var(--text-primary)' }}>{st?.nguon ?? '—'}</b></div>
          <div>Độ phân giải: <b style={{ color: 'var(--text-primary)' }}>{st?.do_phan_giai?.replace('x', ' × ') ?? '—'}</b></div>
          <div>Khung/giây: <b style={{ color: 'var(--text-primary)' }}>{st?.khung_giay ?? '—'}</b></div>
          <div>Số lượt từ lúc khởi động: <b style={{ color: 'var(--text-primary)' }}>{st?.so_luot ?? 0}</b></div>
        </div>
        <div className="d-flex gap-2 mt-3 flex-wrap">
          <Link to="/man-hinh-cong" className="btn btn-primary btn-sm">📷 Mở màn hình cổng</Link>
          <Link to="/cau-hinh-cong" className="btn btn-secondary btn-sm">⚙️ Cấu hình</Link>
        </div>
      </Card.Body>
    </Card>
  )
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const qc = useQueryClient()
  const ws = useWsState()
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

  if (isLoading || !data) return <div className="text-center py-5"><Spinner animation="border" /></div>

  const tyLe = data.ty_le_dat == null ? '—' : `${Math.round(data.ty_le_dat * 100)}%`
  const tong = data.luot_dat + data.luot_khong_dat
  const nowHour = Number(new Intl.DateTimeFormat('en-GB', { hour: '2-digit', hour12: false, timeZone: tz }).format(new Date()))

  return (
    <div className="sg-page">
      <div className="section-header">
        <h1 className="section-title mb-0">Tổng quan hôm nay <span className="sg-sub ms-2">{ngay(data.ngay)}</span></h1>
        <Badge bg={ws === 'mo' ? 'success' : 'danger'}>{ws === 'mo' ? '● Trực tiếp' : '● Mất kết nối, đang thử lại'}</Badge>
      </div>

      <Row className="g-3 mb-3">
        <Col xs={6} md={4} xl><StatCard label="Công nhân đang làm" value={data.so_cong_nhan} icon="👷" color="blue" /></Col>
        <Col xs={6} md={4} xl><StatCard label="Đã vào hôm nay" value={data.da_vao} icon="🔓" color="green" /></Col>
        <Col xs={6} md={4} xl><StatCard label="Đang có mặt" value={data.dang_co_mat} icon="✅" color="orange" /></Col>
        <Col xs={6} md={6} xl><StatCard label="Lượt không đạt" value={data.luot_khong_dat} icon="⛔" color="red" /></Col>
        <Col xs={12} md={6} xl><StatCard label="Tỷ lệ đạt bảo hộ" value={tyLe} icon="🦺" color="yellow"
          note={tong ? `${data.luot_dat}/${tong} lượt đạt` : 'chưa có lượt'} /></Col>
      </Row>

      <Row className="g-3 mb-3">
        <Col lg={8}>
          <Card className="h-100">
            <Card.Header className="d-flex align-items-center">Số lượt kiểm tra theo giờ
              <span className="sg-sub ms-2">({data.so_luot} lượt hôm nay)</span></Card.Header>
            <Card.Body>{data.luot_theo_gio && <HourChart rows={data.luot_theo_gio} nowHour={nowHour} />}</Card.Body>
          </Card>
        </Col>
        <Col lg={4}><GateCard /></Col>
      </Row>

      <Row className="g-3">
        <Col lg={8}>
          <Card>
            <Card.Header className="d-flex align-items-center">Lượt kiểm tra mới nhất
              <Link to="/lich-su" className="ms-auto small">Xem tất cả →</Link></Card.Header>
            <Card.Body className="py-1">
              {!luot.length ? <div className="sg-muted py-3 text-center">Chưa có lượt kiểm tra nào.</div> : (
                <ul className="sg-timeline">
                  {luot.map((c) => (
                    <li key={c.id} className={newIds.includes(c.id) ? 'new' : undefined}>
                      <span className={`sg-dot ${(KET_QUA[c.ket_qua] ?? [])[1] ?? ''}`} />
                      {c.anh ? <img className="sg-thumb" src={c.anh} alt="" loading="lazy" onClick={() => setCheckId(c.id)} />
                        : <span className="sg-thumb sg-thumb--empty" />}
                      <div className="flex-grow-1" style={{ minWidth: 0 }}>
                        <div>
                          {c.cong_nhan
                            ? <><Link to={`/cong-nhan/${c.cong_nhan.id}`} style={{ fontWeight: 600 }}>{c.cong_nhan.ten}</Link> <span className="sg-sub">{c.cong_nhan.ma}</span></>
                            : <span style={{ color: 'var(--text-secondary)' }}>{(MAT[c.trang_thai_mat] ?? ['—'])[0]}</span>}
                        </div>
                        <div className="d-flex gap-1 flex-wrap align-items-center">
                          <StatusBadge map={KET_QUA} value={c.ket_qua} /> <StatusBadge map={HANH_DONG} value={c.hanh_dong} />
                          {c.thieu.length > 0 && <span className="small text-danger">{thieuText(c.thieu)}</span>}
                        </div>
                      </div>
                      <div className="text-end text-nowrap">
                        <div style={{ fontWeight: 600 }}>{gio(c.thoi_diem, true)}</div>
                        <div className="sg-sub">{c.diem != null ? `điểm ${c.diem.toFixed(2)}` : ''}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card.Body>
          </Card>
        </Col>
        <Col lg={4}>
          <Card>
            <Card.Header>Đang có mặt ({data.dang_co_mat_ds.length})</Card.Header>
            <Card.Body className="py-1">
              {!data.dang_co_mat_ds.length ? <div className="sg-muted py-3 text-center">Chưa có ai.</div> : (
                <ul className="sg-timeline">
                  {data.dang_co_mat_ds.map((p) => (
                    <li key={p.worker_id}>
                      <Avatar name={p.ho_ten} workerId={p.worker_id} size={40} face />
                      <div className="flex-grow-1" style={{ minWidth: 0 }}>
                        <Link to={`/cong-nhan/${p.worker_id}`} style={{ fontWeight: 600 }}>{p.ho_ten}</Link>
                        <div className="sg-sub">{p.ma}{p.to_doi ? ` · ${p.to_doi}` : ''}</div>
                      </div>
                      <span className="text-nowrap">vào {p.gio_vao}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <CheckDetailModal id={checkId} onHide={() => setCheckId(null)} />
    </div>
  )
}
