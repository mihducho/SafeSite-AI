import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Button, Form, Spinner } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { CalendarRange, ChevronLeft, ChevronRight, FileSpreadsheet } from 'lucide-react'
import { layBangCongThang, layDanhSachCongNhan, layDanhSachToDoi, taiExcelThang } from '../api/endpoints.js'
import { Card, EmptyState, PageHead, Person, Skeleton } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { gioPhutChu, laChuNhat, phut, soVN, thuNgan, thuNgay } from '../lib/format.js'
import { toast } from '../lib/toast.js'

// Màu ô ngày (chú thích ngay trên bảng)
const LEGEND = [
  ['du', 'Đủ công'], ['muon', 'Đi muộn'], ['tay', 'Chấm thủ công'], ['thieu', 'Thiếu giờ ra'], ['vang', 'Vắng'],
]

function doiThang(ym, n) {
  const [y, m] = ym.split('-').map(Number)
  const d = new Date(Date.UTC(y, m - 1 + n, 1))
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
}

/** Ô một ngày: màu theo trạng thái, ghi số giờ làm; rê chuột hiện giờ vào – giờ ra */
function DayCell({ c, iso, past, since }) {
  if (!c || !c.gio_vao) {
    if (past && !laChuNhat(iso) && (!since || iso >= since)) return <span className="mcell vang" title={`${thuNgay(iso)} · vắng`} />
    return <span className="mcell" />
  }
  const kind = c.thieu_gio_ra ? 'thieu' : c.trang_thai === 'cham_thu_cong' ? 'tay' : c.di_muon_phut > 0 ? 'muon' : 'du'
  const hours = c.gio_ra ? soVN(Math.round((c.so_phut_lam / 60) * 10) / 10, 1).replace(/,0$/, '') : ''
  const tip = [thuNgay(iso), `${c.gio_vao} – ${c.gio_ra ?? (c.thieu_gio_ra ? 'thiếu giờ ra' : 'chưa ra')}`,
    c.di_muon_phut > 0 ? `đi muộn ${c.di_muon_phut} phút` : '', c.gio_ra ? gioPhutChu(c.so_phut_lam) : '',
    c.trang_thai === 'cham_thu_cong' ? 'chấm thủ công' : ''].filter(Boolean).join(' · ')
  return <span className={`mcell ${kind}`} title={tip}>{hours}</span>
}

export default function MonthlyAttendancePage() {
  const cfg = useWebConfig()
  const navigate = useNavigate()
  const [thang, setThang] = useState(cfg.today.slice(0, 7))
  const [toDoi, setToDoi] = useState('')
  const [exporting, setExporting] = useState(false)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['bang-cong-thang', thang, toDoi],
    queryFn: () => layBangCongThang({ thang, to_doi: toDoi || undefined }),
    placeholderData: keepPreviousData,
  })
  const { data: teams } = useQuery({ queryKey: ['to-doi'], queryFn: layDanhSachToDoi, staleTime: 60_000 })
  // ngày thêm công nhân: chỉ đánh dấu "vắng" từ ngày đó trở đi
  const { data: allWorkers } = useQuery({ queryKey: ['cong-nhan', { trang_thai: '' }], queryFn: () => layDanhSachCongNhan(), staleTime: 60_000 })
  const since = Object.fromEntries((allWorkers?.ds ?? []).map((w) => [w.id, w.created_at?.slice(0, 10)]))

  const days = Array.from({ length: data?.so_ngay ?? 0 }, (_, i) => i + 1)
  const isoOf = (d) => `${thang}-${String(d).padStart(2, '0')}`
  const workers = data?.ds ?? []
  const [y, m] = thang.split('-')

  const handleExport = async () => {
    setExporting(true)
    try {
      const blob = await taiExcelThang({ thang, to_doi: toDoi || undefined })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bang_cong_${thang.replace('-', '_')}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Đã xuất file Excel bảng công tháng')
    } catch (err) {
      toast.error(`Không xuất được file Excel: ${err.message}`)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="page">
      <PageHead title="Bảng công tháng" sub={data ? `${workers.length} công nhân${isFetching ? ' · đang cập nhật…' : ''}` : ' '}>
        <Button onClick={handleExport} disabled={exporting || !data}>
          {exporting ? <Spinner size="sm" /> : <FileSpreadsheet size={18} />}Xuất Excel
        </Button>
      </PageHead>

      <div className="d-flex align-items-center gap-2 flex-wrap mb-3">
        <div className="day-picker">
          <Button variant="secondary" className="btn-icon" onClick={() => setThang(doiThang(thang, -1))} aria-label="Tháng trước"><ChevronLeft size={18} /></Button>
          <span className="day-picker__label"><CalendarRange size={17} />Tháng {Number(m)}/{y}</span>
          <Button variant="secondary" className="btn-icon" onClick={() => setThang(doiThang(thang, 1))} aria-label="Tháng sau"><ChevronRight size={18} /></Button>
        </div>
        <Button variant="secondary" onClick={() => setThang(cfg.today.slice(0, 7))} disabled={thang === cfg.today.slice(0, 7)}>Tháng này</Button>
        <Form.Select value={toDoi} onChange={(e) => setToDoi(e.target.value)} aria-label="Tổ đội" style={{ width: 200 }}>
          <option value="">Tất cả tổ</option>
          {(teams?.ds ?? []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </Form.Select>
        <div className="legend ms-auto">
          {LEGEND.map(([k, t]) => <span key={k}><i className={`mcell-dot ${k}`} />{t}</span>)}
        </div>
      </div>

      <Card flush>
        {isLoading ? <div className="sg-card__body"><Skeleton height={240} /></div>
          : !workers.length ? <EmptyState icon={CalendarRange} title="Chưa có dữ liệu bảng công tháng này" text="Chọn tháng khác hoặc tổ khác." />
            : (
              <div className="table-wrap month-wrap">
                <table className="sg-table month">
                  <thead>
                    <tr>
                      <th className="mstick-l">Công nhân</th>
                      {days.map((d) => {
                        const iso = isoOf(d)
                        return (
                          <th key={d} className={`mday${laChuNhat(iso) ? ' sun' : ''}${iso === cfg.today ? ' today' : ''}`}>
                            <span>{d}</span><small>{thuNgan(iso)}</small>
                          </th>
                        )
                      })}
                      <th className="mstick-r r3">Ngày công</th><th className="mstick-r r2">Tổng giờ</th><th className="mstick-r r1">Lần muộn</th>
                    </tr>
                  </thead>
                  <tbody>
                    {workers.map((wk) => (
                      <tr key={wk.worker_id}>
                        <td className="mstick-l"><Person name={wk.ho_ten} code={wk.ma} workerId={wk.worker_id} size={28} to={`/cong-nhan/${wk.worker_id}`} /></td>
                        {days.map((d) => {
                          const iso = isoOf(d)
                          const c = wk.ngay?.[String(d)] ?? wk.ngay?.[d]
                          return (
                            <td key={d} className={`mday${laChuNhat(iso) ? ' sun' : ''}${iso === cfg.today ? ' today' : ''}`}
                              onClick={() => c?.gio_vao && navigate(`/bang-cong?ngay=${iso}`)} style={c?.gio_vao ? { cursor: 'pointer' } : undefined}>
                              <DayCell c={c} iso={iso} past={iso < cfg.today} since={since[wk.worker_id]} />
                            </td>
                          )
                        })}
                        <td className="mstick-r r3 num" style={{ fontWeight: 600 }}>{wk.so_ngay_cong}</td>
                        <td className="mstick-r r2 num" style={{ fontWeight: 600 }}>{phut(wk.tong_phut)}</td>
                        <td className={`mstick-r r1 num${wk.so_lan_muon ? ' text-warn' : ''}`} style={{ fontWeight: 600 }}>{wk.so_lan_muon}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        <div className="sg-card__foot"><span>Mỗi ô ghi số giờ làm. Rê chuột lên ô để xem giờ vào – giờ ra; bấm vào ô để mở bảng công ngày đó.</span></div>
      </Card>
    </div>
  )
}
