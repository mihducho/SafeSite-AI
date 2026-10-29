import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Col, Modal, Row, Spinner, Table } from 'react-bootstrap'
import { danhGiaLuot, layChiTietLuot } from '../../api/endpoints.js'
import { ngay, gio } from '../../lib/format.js'
import { DO_BAO_HO, HANH_DONG, HUONG, KET_QUA, MAT, thieuText } from '../../lib/labels.js'
import { toast } from '../../lib/toast.js'
import { StatusBadge } from './ui.jsx'

/** Hộp xem chi tiết một lượt kiểm tra: ảnh lớn + số liệu + đánh giá "Đúng / Báo nhầm" (DE_TAI.md mục 9.1). */
export default function CheckDetailModal({ id, onHide }) {
  const qc = useQueryClient()
  const { data: c, isLoading } = useQuery({ queryKey: ['luot', id], queryFn: () => layChiTietLuot(id), enabled: !!id })
  const review = useMutation({
    mutationFn: (v) => danhGiaLuot(id, v),
    onSuccess: (r) => {
      qc.setQueryData(['luot', id], r)
      qc.invalidateQueries({ queryKey: ['lich-su-luot'] })
      toast.success(r.danh_gia === 'dung' ? 'Đã xác nhận kết quả đúng' : 'Đã ghi nhận báo nhầm')
    },
  })

  const d = c?.chi_tiet ?? {}
  const nd = d.nhan_dien ?? {}
  const ms = d.ms_tb ?? {}
  const rows = c ? [
    ['Công nhân', c.cong_nhan ? `${c.cong_nhan.ma} – ${c.cong_nhan.ten}` : '—'],
    ['Kết quả', <><StatusBadge map={KET_QUA} value={c.ket_qua} />{c.ly_do && <span className="ms-2 opacity-75">({c.ly_do})</span>}</>],
    ['Thiếu', thieuText(c.thieu) || '—'],
    ['Nhận diện', <><StatusBadge map={MAT} value={c.trang_thai_mat} />
      {c.diem != null && ` điểm ${c.diem.toFixed(2)}`}{d.rong_mat_px ? ` · mặt rộng ${d.rong_mat_px} px` : ''}</>],
    ['Người giống nhất', nd.gan_nhat_ma ? `${nd.gan_nhat_ma}${nd.diem_thu_hai != null ? `, người thứ hai ${nd.diem_thu_hai.toFixed(2)}` : ''}` : '—'],
    ['Hướng / hành động', <>{HUONG[c.huong] ?? '—'} / <StatusBadge map={HANH_DONG} value={c.hanh_dong} /></>],
    ['Kết quả bảo hộ gốc', d.ket_qua_bao_ho ? <StatusBadge map={KET_QUA} value={d.ket_qua_bao_ho} /> : '—'],
    ['Số khung', d.so_khung != null
      ? `${d.so_khung} (hợp lệ ${d.so_khung_hop_le ?? '—'}, có mặt ${d.so_khung_co_mat ?? '—'}, nhiều mặt ${Math.round((d.ty_le_khung_nhieu_mat ?? 0) * 100)}%)` : '—'],
    ['Tỷ lệ có mặt đồ bảo hộ', Object.entries(c.ty_le_co_mat ?? {}).map(([k, v]) => `${DO_BAO_HO[k] ?? k} ${Math.round(v * 100)}%`).join(', ') || '—'],
    ['Thời gian lượt', c.thoi_gian_ms != null ? `${(c.thoi_gian_ms / 1000).toFixed(2)} giây` : '—'],
    ['Mỗi khung', ms.bao_ho != null ? `bảo hộ ${ms.bao_ho} ms, YuNet ${ms.yunet} ms, SFace ${ms.sface ?? '—'} ms` : '—'],
    ['Từ lúc thấy mặt', d.tu_luc_thay_mat_ms != null ? `${(d.tu_luc_thay_mat_ms / 1000).toFixed(2)} giây` : '—'],
  ] : []

  return (
    <Modal show={!!id} onHide={onHide} size="xl" centered scrollable>
      <Modal.Header closeButton>
        <Modal.Title>{c ? `Lượt #${c.id} – ${ngay(c.thoi_diem)} ${gio(c.thoi_diem, true)}` : 'Lượt kiểm tra'}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {isLoading || !c ? (
          <div className="text-center py-5"><Spinner animation="border" /></div>
        ) : (
          <Row className="g-3">
            <Col lg={6} className="text-center">
              {c.anh
                ? <img src={c.anh} alt={`Ảnh lượt ${c.id}`} className="img-fluid rounded" style={{ maxHeight: '70vh' }} />
                : <div className="py-5" style={{ color: 'var(--text-muted)' }}>Lượt này không có ảnh</div>}
            </Col>
            <Col lg={6}>
              <Table size="sm" className="mb-3 sg-table">
                <tbody>
                  {rows.map(([k, v]) => <tr key={k}><th className="text-nowrap">{k}</th><td>{v}</td></tr>)}
                </tbody>
              </Table>
              <div className="d-flex align-items-center gap-2 flex-wrap">
                <span style={{ color: 'var(--text-muted)' }}>Đánh giá kết quả:</span>
                <Button size="sm" variant={c.danh_gia === 'dung' ? 'success' : 'outline-success'}
                  disabled={review.isPending} onClick={() => review.mutate('dung')}>✔ Đúng</Button>
                <Button size="sm" variant={c.danh_gia === 'bao_nham' ? 'danger' : 'outline-danger'}
                  disabled={review.isPending} onClick={() => review.mutate('bao_nham')}>✕ Báo nhầm</Button>
                {c.danh_gia && (
                  <Button size="sm" variant="link" disabled={review.isPending} onClick={() => review.mutate(null)}>Bỏ đánh giá</Button>
                )}
              </div>
            </Col>
          </Row>
        )}
      </Modal.Body>
    </Modal>
  )
}
