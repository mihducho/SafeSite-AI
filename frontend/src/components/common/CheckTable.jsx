import { CircleMinus, Eye, ImageOff, LogIn, LogOut, PencilLine, Repeat, ScanFace } from 'lucide-react'
import { gio, soVN, thuNgay } from '../../lib/format.js'
import { HANH_DONG, KET_QUA, MAT, thieuText } from '../../lib/labels.js'
import { EmptyRow, RowMenu, SkeletonRows, StatusBadge } from './ui.jsx'

const ACTION_ICON = { ghi_vao: LogIn, ghi_ra: LogOut, bo_qua_trung: Repeat, khong_ghi: CircleMinus }

/** Cột "Chấm công": icon vào/ra + chữ */
export function ChamCongCell({ value }) {
  const [text, tone] = HANH_DONG[value] ?? ['', 'neutral']
  const Icon = ACTION_ICON[value] ?? CircleMinus
  return (
    <span className={`d-inline-flex align-items-center gap-2 nowrap ${tone === 'ok' ? 'text-ok' : 'muted'}`} style={{ fontWeight: tone === 'ok' ? 600 : 400 }}>
      <Icon size={17} />{text}
    </span>
  )
}

/**
 * Bảng lượt kiểm tra 5 cột, nhóm theo ngày: Lượt (ảnh cắt quanh đầu + giờ) · Công nhân · Kết quả · Chấm công · ⋯
 * dayTotals: { 'YYYY-MM-DD': số lượt } nếu biết tổng cả ngày (lọc 1 ngày), không thì đếm trên trang.
 */
export default function CheckTable({ ds, loading, onOpen, onManual, dayTotals, emptyTitle = 'Không có lượt kiểm tra nào', emptyText }) {
  const rows = []
  let lastDay = null
  const perDay = {}
  for (const c of ds ?? []) { const k = c.thoi_diem.slice(0, 10); perDay[k] = (perDay[k] ?? 0) + 1 }
  for (const c of ds ?? []) {
    const day = c.thoi_diem.slice(0, 10)
    if (day !== lastDay) {
      lastDay = day
      const n = dayTotals?.[day] ?? perDay[day]
      rows.push(<tr key={`d${day}`} className="group"><td colSpan={5}>{thuNgay(day)} · {n} lượt</td></tr>)
    }
    const nd = c.diem != null ? `nhận diện ${soVN(c.diem)}` : ''
    rows.push(
      <tr key={c.id} className="clickable" onClick={() => onOpen(c.id)}>
        <td className="shrink">
          <div className="d-flex align-items-center gap-3">
            {c.anh ? <img className="thumb" src={c.anh} alt="" loading="lazy" /> : <span className="thumb thumb--empty"><ImageOff size={18} /></span>}
            <span className="num" style={{ fontWeight: 600 }}>{gio(c.thoi_diem, true)}</span>
          </div>
        </td>
        <td>
          {c.cong_nhan ? (
            <div className="person__text">
              <span className="person__name">{c.cong_nhan.ten}</span>
              <span className="person__sub">{[c.cong_nhan.ma, nd].filter(Boolean).join(' · ')}</span>
            </div>
          ) : <span className="text-warn" style={{ fontWeight: 600 }}>{(MAT[c.trang_thai_mat] ?? ['Không nhận ra'])[0]}</span>}
        </td>
        <td>
          <StatusBadge map={KET_QUA} value={c.ket_qua} />
          {c.thieu?.length > 0 && <div className="small text-bad mt-1">{thieuText(c.thieu)}</div>}
        </td>
        <td><ChamCongCell value={c.hanh_dong} /></td>
        <td className="shrink">
          <RowMenu items={[
            { label: 'Xem chi tiết', icon: Eye, onClick: () => onOpen(c.id) },
            onManual && { label: 'Chấm thủ công', icon: PencilLine, onClick: () => onManual(c) },
          ]} />
        </td>
      </tr>,
    )
  }
  return (
    <table className="sg-table">
      <thead><tr><th>Lượt</th><th>Công nhân</th><th>Kết quả</th><th>Chấm công</th><th className="shrink" /></tr></thead>
      <tbody>
        {loading ? <SkeletonRows cols={5} />
          : !ds?.length ? <EmptyRow colSpan={5} icon={ScanFace} title={emptyTitle} text={emptyText} />
            : rows}
      </tbody>
    </table>
  )
}
