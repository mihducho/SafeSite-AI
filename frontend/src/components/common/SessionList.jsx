import { useState } from 'react'
import { ArrowRight, ImageOff } from 'lucide-react'
import { getUrlAnhLuot } from '../../api/endpoints.js'
import { NGUON, TRANG_THAI_PHIEN } from '../../lib/labels.js'
import { Pill, StatusBadge } from './ui.jsx'

/** Ảnh nhỏ của lượt vào / ra (nếu lượt có ảnh); bấm để xem chi tiết lượt. Lượt không có ảnh -> ô trống. */
function LuotThumb({ id, label, onOpen }) {
  const [ok, setOk] = useState(true)
  if (!id) return <span className="seg-thumb seg-thumb--empty" title={`${label}: chấm thủ công`}><ImageOff size={13} strokeWidth={1.5} /></span>
  return ok ? (
    <button type="button" className="seg-thumb" title={`Xem lượt ${label.toLowerCase()}`} onClick={() => onOpen?.(id)}>
      <img src={getUrlAnhLuot(id)} alt={label} loading="lazy" onError={() => setOk(false)} />
    </button>
  ) : <span className="seg-thumb seg-thumb--empty" title={`${label}: không có ảnh`}><ImageOff size={13} strokeWidth={1.5} /></span>
}

/**
 * Danh sách phiên vào - ra của một ngày (phien = mảng phiên do API trả).
 * Mỗi phiên: giờ vào → giờ ra, nguồn (tự động / thủ công), trạng thái phiên, ảnh lượt vào / ra.
 * actions(phien) -> nút thao tác bên phải (modal chấm công); onOpenCheck(id) -> mở chi tiết lượt.
 */
export default function SessionList({ phien, actions, onOpenCheck, compact = false }) {
  if (!phien?.length) return <div className="small muted">Chưa có phiên nào trong ngày.</div>
  return (
    <ul className={`seg-list${compact ? ' compact' : ''}`}>
      {phien.map((p, i) => {
        const nguon = p.nguon_vao === 'thu_cong' || p.nguon_ra === 'thu_cong'
        return (
          <li key={p.id} className={p.trang_thai === 'huy' ? 'cancelled' : ''}>
            <span className="seg-idx num">{i + 1}</span>
            <span className="seg-time num">
              {p.vao}<ArrowRight size={13} strokeWidth={1.5} />{p.ra ?? <span className="muted">chưa ra</span>}
            </span>
            {!compact && (
              <span className="seg-thumbs">
                <LuotThumb id={p.vao_check_id} label="Vào" onOpen={onOpenCheck} />
                <LuotThumb id={p.ra_check_id} label="Ra" onOpen={onOpenCheck} />
              </span>
            )}
            {!(compact && p.trang_thai === 'dong') && <StatusBadge map={TRANG_THAI_PHIEN} value={p.trang_thai} />}
            {nguon && (
              <Pill tone="neutral" className="no-dot">
                {p.nguon_vao === 'thu_cong' && p.nguon_ra === 'thu_cong' ? 'Thủ công'
                  : p.nguon_vao === 'thu_cong' ? `Vào: ${NGUON.thu_cong.toLowerCase()}` : `Ra: ${NGUON.thu_cong.toLowerCase()}`}
              </Pill>
            )}
            {actions && <span className="seg-actions">{actions(p)}</span>}
          </li>
        )
      })}
    </ul>
  )
}
