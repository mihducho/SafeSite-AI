import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Button, Form, Spinner } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { CalendarRange, ChevronLeft, ChevronRight, FileSpreadsheet } from 'lucide-react'
import { layBangCongThang, layDanhSachToDoi, taiExcelThang } from '../api/endpoints.js'
import { Card, EmptyState, PageHead, Person, Skeleton } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { gioPhutChu, laChuNhat, phut, soVN, thuNgan, thuNgay } from '../lib/format.js'
import { TRANG_THAI_NGAY } from '../lib/labels.js'
import { toast } from '../lib/toast.js'

// Màu ô ngày theo TRẠNG THÁI BACKEND (chú thích ngay trên bảng). Giao diện không tự tính "Vắng".
const LEGEND = [
  ['du', 'Đủ công'], ['muon', 'Đi muộn / về sớm'], ['phep', 'Có phép'], ['thieu', 'Thiếu giờ ra'], ['vang', 'Vắng'],
  ['nghi', 'Nghỉ tuần'], ['nghiphep', 'Nghỉ phép'], ['dang', 'Đang làm'],
]

function doiThang(ym, n) {
  const [y, m] = ym.split('-').map(Number)
  const d = new Date(Date.UTC(y, m - 1 + n, 1))
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
}

/** Ô một ngày: màu theo trạng thái backend, ghi số giờ làm; rê chuột: trạng thái, các phiên, các phép của ngày */
function DayCell({ code, c, iso }) {
  const [label, , kind] = TRANG_THAI_NGAY[code] ?? ['', 'neutral', 'trong']
  const hours = c?.so_phut_lam ? soVN(Math.round((c.so_phut_lam / 60) * 10) / 10, 1).replace(/,0$/, '') : ''
  const tip = [
    `${thuNgay(iso)}: ${c?.ten_trang_thai ?? label}`,
    ...(c?.phien ?? []).filter((p) => p.trang_thai !== 'huy')
      .map((p, i) => `Phiên ${i + 1}: ${p.vao} – ${p.ra ?? (p.trang_thai === 'thieu_gio_ra' ? 'thiếu giờ ra' : 'chưa ra')}`),
    c?.so_phut_lam ? `Làm ${gioPhutChu(c.so_phut_lam)}` : '',
    c?.di_muon_phut > 0 ? `Đi muộn ${c.di_muon_phut} phút${c.muon_co_phep ? ' (có phép)' : ''}` : '',
    c?.ve_som_phut > 0 && c?.gio_ra ? `Về sớm ${c.ve_som_phut} phút${c.som_co_phep ? ' (có phép)' : ''}` : '',
    c?.phut_ra_ngoai > 0 ? `Ra ngoài ${c.phut_ra_ngoai} phút` : '',
    ...(c?.phep ?? []).map((p) => `Phép: ${p.mo_ta}`),
    c?.co_sua_tay ? 'Có chấm thủ công' : '',
  ].filter(Boolean).join('\n')
  return (
    <span className={`mcell ${kind}${c?.co_sua_tay ? ' sua' : ''}`} title={tip}>
      {hours || (code === 'nghi_phep' ? 'P' : '')}
    </span>
  )
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
                      <th className="mstick-r r6" title="Số ngày được tính công">Ngày công</th>
                      <th className="mstick-r r5" title="Tổng giờ làm (giờ:phút)">Tổng giờ</th>
                      <th className="mstick-r r4" title="(Phút làm + phút công tác) / phút chuẩn của ca">Công quy đổi</th>
                      <th className="mstick-r r3">Vắng</th>
                      <th className="mstick-r r2">Thiếu giờ ra</th>
                      <th className="mstick-r r1" title="Số lần đi muộn / về sớm KHÔNG có phép">Muộn / sớm không phép</th>
                    </tr>
                  </thead>
                  <tbody>
                    {workers.map((wk) => {
                      const kp = wk.so_lan_muon_khong_phep + wk.so_lan_ve_som_khong_phep
                      return (
                        <tr key={wk.worker_id}>
                          <td className="mstick-l"><Person name={wk.ho_ten} code={wk.ma} workerId={wk.worker_id} size={28} to={`/cong-nhan/${wk.worker_id}`} /></td>
                          {days.map((d) => {
                            const iso = isoOf(d)
                            const c = wk.ngay?.[String(d)] ?? wk.ngay?.[d]
                            const code = wk.trang_thai_ngay?.[String(d)] ?? wk.trang_thai_ngay?.[d]
                            return (
                              <td key={d} className={`mday${laChuNhat(iso) ? ' sun' : ''}${iso === cfg.today ? ' today' : ''}`}
                                onClick={() => c && navigate(`/bang-cong?ngay=${iso}&cn=${wk.worker_id}`)} style={c ? { cursor: 'pointer' } : undefined}>
                                <DayCell code={code} c={c} iso={iso} />
                              </td>
                            )
                          })}
                          <td className="mstick-r r6 num" style={{ fontWeight: 600 }}>{wk.so_ngay_cong}</td>
                          <td className="mstick-r r5 num" style={{ fontWeight: 600 }}>{phut(wk.tong_phut)}</td>
                          <td className="mstick-r r4 num" style={{ fontWeight: 600 }}>{soVN(wk.tong_cong_quy_doi)}</td>
                          <td className={`mstick-r r3 num${wk.so_ngay_vang ? ' text-bad' : ''}`}>{wk.so_ngay_vang}</td>
                          <td className={`mstick-r r2 num${wk.so_ngay_thieu_gio_ra ? ' text-bad' : ''}`}>{wk.so_ngay_thieu_gio_ra}</td>
                          <td className={`mstick-r r1 num${kp ? ' text-warn' : ''}`}
                            title={`Đi muộn không phép ${wk.so_lan_muon_khong_phep}, về sớm không phép ${wk.so_lan_ve_som_khong_phep}`}>
                            {wk.so_lan_muon_khong_phep} / {wk.so_lan_ve_som_khong_phep}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
        <div className="sg-card__foot"><span>Mỗi ô ghi số giờ làm (P: nghỉ phép; góc chấm: có chấm thủ công). Rê chuột lên ô để xem các phiên và phép; bấm vào ô để mở ngày công đó.</span></div>
      </Card>
    </div>
  )
}
