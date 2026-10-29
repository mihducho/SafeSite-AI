import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Badge, Form, Pagination } from 'react-bootstrap'
import { layDanhSachMauMat, STREAM_URL } from '../../api/endpoints.js'
import { chuCaiDau } from '../../lib/format.js'

const BLANK_GIF = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'

/**
 * Hình trực tiếp camera cổng (MJPEG /stream/gate qua backend, không mở thẳng URL camera).
 * Khi gỡ khỏi trang PHẢI đổi src sang ảnh trống: Chrome/Edge không tự đóng luồng MJPEG của <img> đã bị gỡ, mà mỗi máy
 * chủ chỉ được 6 kết nối -> chuyển trang vài lần là mọi lệnh gọi API bị kẹt.
 */
export const LiveStream = forwardRef(function LiveStream({ src = STREAM_URL, ...props }, ref) {
  const inner = useRef(null)
  useImperativeHandle(ref, () => inner.current)
  useEffect(() => {
    const el = inner.current
    return () => { if (el) el.src = BLANK_GIF }
  }, [])
  return <img ref={inner} src={src} {...props} />
})

/** Badge theo bảng nhãn trong lib/labels.js, vd <StatusBadge map={KET_QUA} value="DAT" /> */
export function StatusBadge({ map, value, className }) {
  const [text, color] = map[value] ?? [value ?? '—', 'secondary']
  const dark = color === 'warning' || color === 'info'
  return <Badge bg={color} text={dark ? 'dark' : undefined} className={className}>{text}</Badge>
}

/** Ô nhập giờ 24 giờ HH:MM (kiểm tra bằng hhmm() trong lib/format.js khi gửi). */
export function TimeInput({ value, onChange, ...props }) {
  return (
    <Form.Control type="text" inputMode="numeric" maxLength={5} placeholder="HH:MM" autoComplete="off"
      value={value ?? ''} onChange={(e) => onChange(e.target.value)} {...props} />
  )
}

/** Phân trang: Trước · 1 … 4 5 [6] 7 8 … 20 · Sau */
export function Pager({ page, pages, onChange }) {
  if (pages <= 1) return null
  const nums = new Set([1, pages])
  for (let p = page - 2; p <= page + 2; p++) if (p >= 1 && p <= pages) nums.add(p)
  const list = [...nums].sort((a, b) => a - b)
  const items = []
  list.forEach((p, i) => {
    if (i && p - list[i - 1] > 1) items.push(<Pagination.Ellipsis key={`e${p}`} disabled />)
    items.push(<Pagination.Item key={p} active={p === page} onClick={() => onChange(p)}>{p}</Pagination.Item>)
  })
  return (
    <Pagination className="mb-0 sg-pager">
      <Pagination.Prev disabled={page <= 1} onClick={() => onChange(page - 1)}>‹ Trước</Pagination.Prev>
      {items}
      <Pagination.Next disabled={page >= pages} onClick={() => onChange(page + 1)}>Sau ›</Pagination.Next>
    </Pagination>
  )
}

/**
 * Ảnh đại diện công nhân: ảnh mẫu khuôn mặt đầu tiên (face=true, đọc /api/cong-nhan/{id}/mau-mat, có bộ nhớ đệm),
 * hoặc chữ cái đầu của tên.
 */
export function Avatar({ name, workerId, size = 40, face = false }) {
  const { data } = useQuery({
    queryKey: ['mau-mat', workerId],
    queryFn: () => layDanhSachMauMat(workerId),
    enabled: face && !!workerId,
    staleTime: 60_000,
    meta: { silent: true },
  })
  const src = face ? data?.ds?.[0]?.anh : null
  const style = { width: size, height: size, fontSize: size * 0.38 }
  return src
    ? <img className="sg-avatar" src={src} alt={name} style={style} />
    : <span className="sg-avatar sg-avatar--text" style={style} title={name}>{chuCaiDau(name)}</span>
}

/** Khối "đang tải / lỗi / trống" dùng chung cho bảng */
export function EmptyRow({ colSpan, children }) {
  return <tr><td colSpan={colSpan} className="text-center py-4" style={{ color: 'var(--text-muted)' }}>{children}</td></tr>
}
