import { trangThaiNgay } from '../../lib/labels.js'
import { Pill } from './ui.jsx'

/** Trạng thái một ngày công DO BACKEND TÍNH + badge "Có phép" / "Sửa tay" (r = dòng bảng công của API) */
export default function DayStatus({ r }) {
  const [text, tone] = trangThaiNgay(r)
  const coPhep = r.muon_co_phep || r.som_co_phep || (r.phep?.length ?? 0) > 0
  const daNoiPhep = r.trang_thai_ngay === 'nghi_phep' || r.trang_thai_ngay?.endsWith('co_phep')
  return (
    <span className="d-inline-flex gap-1 flex-wrap">
      <Pill tone={tone}>{text}</Pill>
      {coPhep && !daNoiPhep && <Pill tone="info" className="no-dot">Có phép</Pill>}
      {r.co_sua_tay && <Pill tone="neutral" className="no-dot">Sửa tay</Pill>}
    </span>
  )
}
