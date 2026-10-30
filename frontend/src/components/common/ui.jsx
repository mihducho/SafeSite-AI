import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Dropdown, Form, Pagination } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Inbox, MoreHorizontal } from 'lucide-react'
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

/** Badge trạng thái theo bảng nhãn trong lib/labels.js, vd <StatusBadge map={KET_QUA} value="DAT" /> */
export function StatusBadge({ map, value, className = '' }) {
  if (value == null) return null
  const [text, tone] = map[value] ?? [value, 'neutral']
  return <span className={`pill ${tone} ${className}`}>{text}</span>
}

/** Badge tự đặt chữ + tông: <Pill tone="warn">+12 phút</Pill> */
export function Pill({ tone = 'neutral', icon: Icon, children, className = '' }) {
  return (
    <span className={`pill ${tone} ${Icon ? 'no-dot' : ''} ${className}`}>
      {Icon && <Icon size={13} strokeWidth={1.5} />}{children}
    </span>
  )
}

/** Ô nhập giờ 24 giờ HH:MM (kiểm tra bằng hhmm() trong lib/format.js khi gửi). */
export function TimeInput({ value, onChange, ...props }) {
  return (
    <Form.Control type="text" inputMode="numeric" maxLength={5} placeholder="HH:MM" autoComplete="off"
      value={value ?? ''} onChange={(e) => onChange(e.target.value)} {...props} />
  )
}

/** Phân trang: ‹ 1 … 4 5 [6] 7 8 … 20 › */
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
    <Pagination size="sm">
      <Pagination.Prev disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Trang trước"><ChevronLeft size={16} /></Pagination.Prev>
      {items}
      <Pagination.Next disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Trang sau"><ChevronRight size={16} /></Pagination.Next>
    </Pagination>
  )
}

/**
 * Ảnh đại diện: ảnh mẫu khuôn mặt đầu tiên nếu có (đọc /api/cong-nhan/{id}/mau-mat, có bộ nhớ đệm), không thì chữ cái
 * đầu của tên trên nền trung tính.
 */
export function Avatar({ name, workerId, size = 34, face = true }) {
  const { data } = useQuery({
    queryKey: ['mau-mat', workerId],
    queryFn: () => layDanhSachMauMat(workerId),
    enabled: face && !!workerId,
    staleTime: 60_000,
    meta: { silent: true },
  })
  const src = face ? data?.ds?.[0]?.anh : null
  const style = { width: size, height: size, fontSize: Math.round(size * 0.36) }
  return src
    ? <img className="avatar" src={src} alt={name} style={style} />
    : <span className="avatar" style={style} title={name}>{chuCaiDau(name)}</span>
}

/** Tên người: avatar + tên đậm màu chữ chính + mã nhỏ màu phụ bên dưới (to: mở trang chi tiết) */
export function Person({ name, code, workerId, sub, to, size = 34, face = true }) {
  const inner = (
    <>
      <Avatar name={name} workerId={workerId} size={size} face={face} />
      <span className="person__text">
        <span className="person__name">{name}</span>
        {(code || sub) && <span className="person__sub num">{[code, sub].filter(Boolean).join(' · ')}</span>}
      </span>
    </>
  )
  return to
    ? <Link to={to} className="person" onClick={(e) => e.stopPropagation()}>{inner}</Link>
    : <span className="person">{inner}</span>
}

const MenuToggle = forwardRef(function MenuToggle({ onClick }, ref) {
  return (
    <button ref={ref} type="button" className="row-menu-btn" aria-label="Thao tác"
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClick(e) }}>
      <MoreHorizontal size={16} strokeWidth={1.5} />
    </button>
  )
})

/** Nút "⋯" gom thao tác trên một dòng: items = [{ label, icon, onClick, danger }] */
export function RowMenu({ items }) {
  return (
    <Dropdown align="end" onClick={(e) => e.stopPropagation()}>
      <Dropdown.Toggle as={MenuToggle} />
      <Dropdown.Menu popperConfig={{ strategy: 'fixed' }} renderOnMount>
        {items.filter(Boolean).map(({ label, icon: Icon, onClick, danger }) => (
          <Dropdown.Item key={label} as="button" className={danger ? 'danger' : ''} onClick={onClick}>
            {Icon && <Icon size={15} strokeWidth={1.5} />}{label}
          </Dropdown.Item>
        ))}
      </Dropdown.Menu>
    </Dropdown>
  )
}

/** Khung xương lúc đang tải */
export function Skeleton({ width = '100%', height = 14, style }) {
  return <span className="skeleton" style={{ display: 'block', width, height, ...style }} />
}

export function SkeletonRows({ rows = 6, cols = 5 }) {
  return Array.from({ length: rows }, (_, r) => (
    <tr key={r}>
      {Array.from({ length: cols }, (_, c) => (
        <td key={c}><Skeleton width={c === 0 ? '70%' : `${40 + ((r + c) % 4) * 12}%`} /></td>
      ))}
    </tr>
  ))
}

/** Chưa có dữ liệu: icon + câu hướng dẫn + nút hành động (nếu có) */
export function EmptyState({ icon: Icon = Inbox, title, text, action }) {
  return (
    <div className="empty">
      <span className="empty__icon"><Icon size={18} strokeWidth={1.5} /></span>
      {title && <b>{title}</b>}
      {text && <span className="small">{text}</span>}
      {action}
    </div>
  )
}

/** Dòng bảng chứa trạng thái trống */
export function EmptyRow({ colSpan, ...props }) {
  return <tr><td colSpan={colSpan} style={{ height: 'auto' }}><EmptyState {...props} /></td></tr>
}

/** Đầu trang: tiêu đề 24px, một dòng mô tả, nút ở bên phải */
export function PageHead({ title, sub, children }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {sub && <p>{sub}</p>}
      </div>
      {children && <div className="page-head__actions">{children}</div>}
    </div>
  )
}

/** Thẻ: tiêu đề 16px, phần phụ bên phải. flush = nội dung sát mép (bảng) */
export function Card({ title, sub, end, children, flush = false, className = '', bodyClassName = '', style }) {
  return (
    <section className={`sg-card ${className}`} style={style}>
      {(title || end) && (
        <div className="sg-card__head">
          {title && <h2>{title}</h2>}
          {sub && <span className="sub">{sub}</span>}
          {end && <div className="end">{end}</div>}
        </div>
      )}
      {flush ? children : <div className={`sg-card__body ${bodyClassName}`}>{children}</div>}
    </section>
  )
}

/** Thẻ số liệu: icon 17px mảnh không nền tròn, số lớn tabular-nums, dòng phụ */
export function StatCard({ icon: Icon, tone = 'neutral', label, value, sub, loading }) {
  return (
    <section className="sg-card stat">
      <span className={`stat__icon tone-${tone}`}><Icon size={17} strokeWidth={1.5} /></span>
      <div style={{ minWidth: 0 }}>
        <div className="stat__label">{label}</div>
        {loading ? <Skeleton width={70} height={30} style={{ margin: '4px 0' }} /> : <div className="stat__value num">{value}</div>}
        {sub && <div className="stat__sub num">{sub}</div>}
      </div>
    </section>
  )
}

/** Tab: tabs = [{ key, label, count, icon }] */
export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map(({ key, label, count, icon: Icon }) => (
        <button key={key} type="button" role="tab" aria-selected={active === key} className={active === key ? 'active' : ''}
          onClick={() => onChange(key)}>
          {Icon && <Icon size={16} strokeWidth={1.5} />}{label}{count != null && <span className="count num">{count}</span>}
        </button>
      ))}
    </div>
  )
}

/** Nút chọn dạng đoạn: options = [{ value, label }] */
export function Segmented({ options, value, onChange, ariaLabel }) {
  return (
    <div className="segmented" role="group" aria-label={ariaLabel}>
      {options.map((o) => (
        <button key={String(o.value)} type="button" className={o.value === value ? 'active' : ''} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Thanh tiến độ nhỏ */
export function Meter({ value, max, warn = false, style }) {
  const pct = max ? Math.min(100, (value / max) * 100) : 0
  return <div className={`meter ${warn ? 'warn' : ''}`} style={style}><span style={{ width: `${pct}%` }} /></div>
}
