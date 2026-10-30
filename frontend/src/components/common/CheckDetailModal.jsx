import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Modal, Spinner } from 'react-bootstrap'
import { ImageOff, PencilLine, ThumbsDown, ThumbsUp } from 'lucide-react'
import { danhGiaLuot, layChiTietLuot } from '../../api/endpoints.js'
import { gio, soVN, thuNgay } from '../../lib/format.js'
import { DO_BAO_HO, KET_QUA, MAT, thieuText } from '../../lib/labels.js'
import { toast } from '../../lib/toast.js'
import { ChamCongCell } from './CheckTable.jsx'
import ManualAttendanceModal from './ManualAttendanceModal.jsx'
import { Skeleton, StatusBadge } from './ui.jsx'

/** Cửa sổ chi tiết một lượt kiểm tra: ảnh lượt lớn (khung dọc) + số liệu + Đúng / Báo nhầm + Chấm thủ công. */
export default function CheckDetailModal({ id, onHide }) {
  const qc = useQueryClient()
  const [manual, setManual] = useState(false)
  const { data: c, isLoading } = useQuery({ queryKey: ['luot', id], queryFn: () => layChiTietLuot(id), enabled: !!id })
  const review = useMutation({
    mutationFn: (v) => danhGiaLuot(id, v),
    onSuccess: (r) => {
      qc.setQueryData(['luot', id], r)
      qc.invalidateQueries({ queryKey: ['lich-su-luot'] })
      toast.success(r.danh_gia === 'dung' ? 'Đã xác nhận kết quả đúng' : r.danh_gia === 'bao_nham' ? 'Đã ghi nhận báo nhầm' : 'Đã bỏ đánh giá')
    },
  })

  const d = c?.chi_tiet ?? {}
  const nd = d.nhan_dien ?? {}
  const ms = d.ms_tb ?? {}
  const ppe = Object.entries(c?.ty_le_co_mat ?? {}).map(([k, v]) => `${DO_BAO_HO[k] ?? k} ${Math.round(v * 100)}% số khung`).join(', ')
  const rows = c ? [
    ['Kết quả', <StatusBadge map={KET_QUA} value={c.ket_qua} />],
    ['Thiếu', c.thieu?.length ? <span className="text-bad" style={{ fontWeight: 600 }}>{thieuText(c.thieu)}</span> : ''],
    ['Nhận diện', <>
      <StatusBadge map={MAT} value={c.trang_thai_mat} />
      {c.diem != null && <span className="ms-2">điểm {soVN(c.diem)}</span>}
      {d.rong_mat_px ? <span className="muted"> · mặt rộng {d.rong_mat_px} px</span> : null}
    </>],
    ['Người giống nhất', !c.cong_nhan && nd.gan_nhat_ma ? `${nd.gan_nhat_ma} (điểm ${soVN(nd.diem)})` : ''],
    ['Chấm công', <ChamCongCell value={c.hanh_dong} />],
    ['Thấy đồ bảo hộ', ppe],
    ['Số khung đã xét', d.so_khung != null ? `${d.so_khung} khung (hợp lệ ${d.so_khung_hop_le ?? 0}, thấy mặt ${d.so_khung_co_mat ?? 0})` : ''],
    ['Thời gian xử lý', c.thoi_gian_ms != null
      ? `${soVN(c.thoi_gian_ms / 1000, 1)} giây${ms.bao_ho != null ? ` (mỗi khung: bảo hộ ${Math.round(ms.bao_ho)} ms, khuôn mặt ${Math.round((ms.yunet ?? 0) + (ms.sface ?? 0))} ms)` : ''}` : ''],
  ].filter(([, v]) => v) : []

  return (
    <>
      <Modal show={!!id && !manual} onHide={onHide} size="xl" centered scrollable>
        <Modal.Header closeButton>
          <Modal.Title>{c ? `Lượt kiểm tra lúc ${gio(c.thoi_diem, true)}` : 'Lượt kiểm tra'}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {isLoading || !c ? (
            <div className="d-flex gap-4"><Skeleton width={280} height={420} /><div className="flex-grow-1"><Skeleton height={20} /><Skeleton height={20} style={{ marginTop: 14 }} /></div></div>
          ) : (
            <div className="d-flex gap-4 flex-wrap flex-lg-nowrap">
              <div style={{ flex: '0 0 auto' }}>
                {c.anh
                  ? <img src={c.anh} alt={`Ảnh lượt ${c.id}`} className="portrait" style={{ height: 'min(64vh, 620px)', width: 'calc(min(64vh, 620px) * 0.5625)' }} />
                  : <div className="portrait thumb--empty" style={{ height: 360, width: 202, display: 'flex', color: '#94A3B8' }}><ImageOff size={32} /></div>}
              </div>
              <div style={{ flex: "1 1 280px", minWidth: 280 }}>
                <div className="mb-3">
                  <div style={{ fontSize: 20, fontWeight: 700 }}>{c.cong_nhan ? c.cong_nhan.ten : (MAT[c.trang_thai_mat] ?? ['Không nhận ra'])[0]}</div>
                  <div className="muted">{[c.cong_nhan?.ma, thuNgay(c.thoi_diem)].filter(Boolean).join(' · ')}</div>
                </div>
                <table className="kv mb-4"><tbody>{rows.map(([k, v]) => <tr key={k}><th>{k}</th><td>{v}</td></tr>)}</tbody></table>
                <div className="small muted mb-2">Kết quả này đúng không?</div>
                <div className="d-flex gap-2 flex-wrap">
                  <Button variant={c.danh_gia === 'dung' ? 'success' : 'secondary'} disabled={review.isPending}
                    onClick={() => review.mutate(c.danh_gia === 'dung' ? null : 'dung')}><ThumbsUp size={17} />Đúng</Button>
                  <Button variant={c.danh_gia === 'bao_nham' ? 'danger' : 'secondary'} disabled={review.isPending}
                    onClick={() => review.mutate(c.danh_gia === 'bao_nham' ? null : 'bao_nham')}><ThumbsDown size={17} />Báo nhầm</Button>
                  <Button variant="secondary" className="ms-auto" onClick={() => setManual(true)}><PencilLine size={17} />Chấm thủ công</Button>
                </div>
              </div>
            </div>
          )}
        </Modal.Body>
      </Modal>
      {manual && c && (
        <ManualAttendanceModal
          worker={c.cong_nhan}
          ngay={c.thoi_diem.slice(0, 10)}
          gioVao={c.huong !== 'ra' ? gio(c.thoi_diem) : ''}
          gioRa={c.huong === 'ra' ? gio(c.thoi_diem) : ''}
          note={`từ lượt lúc ${gio(c.thoi_diem, true)}`}
          onClose={() => setManual(false)}
        />
      )}
    </>
  )
}
