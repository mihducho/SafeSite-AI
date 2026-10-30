// Định dạng ngày giờ. API trả giờ Việt Nam dạng ISO có múi giờ ("2026-10-29T07:02:00+07:00") nên chỉ cần cắt chuỗi,
// không đổi theo múi giờ của máy chạy trình duyệt. Ngày hiển thị dd/mm/yyyy, giờ 24 giờ.

export const MUI_GIO_MAC_DINH = 'Asia/Ho_Chi_Minh'

/** "2026-10-29..." -> "29/10/2026" */
export function ngay(iso) {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-')
  return d && m && y ? `${d}/${m}/${y}` : iso
}

/** ISO -> "07:02" (hoặc "07:02:15") */
export const gio = (iso, giay = false) => (iso ? iso.slice(11, giay ? 19 : 16) : '—')

export const ngayGio = (iso, giay = false) => (iso ? `${ngay(iso)} ${gio(iso, giay)}` : '—')

/** số phút -> "8:30" (giờ:phút) */
export function phut(m) {
  if (m == null) return '—'
  return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}`
}

/** Ngày hôm nay YYYY-MM-DD theo múi giờ công trường */
export function homNay(tz = MUI_GIO_MAC_DINH) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' })
    .format(new Date())
}

/** Cộng/trừ n ngày trên chuỗi YYYY-MM-DD (tính theo UTC để không lệch múi giờ) */
export function doiNgay(iso, n) {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

/** Đồng hồ: { gio: "07:02:15", ngay: "Thứ năm, 30/10/2026" } theo múi giờ công trường */
export function dongHo(tz = MUI_GIO_MAC_DINH, now = new Date()) {
  const time = new Intl.DateTimeFormat('vi-VN', { timeZone: tz, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(now)
  const thu = new Intl.DateTimeFormat('vi-VN', { timeZone: tz, weekday: 'long' }).format(now)
  const d = homNay(tz)
  return { gio: time, ngay: `${thu.charAt(0).toUpperCase()}${thu.slice(1)}, ${ngay(d)}` }
}

/**
 * Ô giờ HH:MM (24 giờ): rỗng -> null; sai dạng -> ném Error kèm tên ô. Chấp nhận "730" / "7:30" / "07:30".
 * Không dùng <input type="time"> vì Edge tiếng Việt hiện kiểu 12 giờ SA/CH.
 */
export function hhmm(value, label) {
  const v = String(value ?? '').trim()
  if (!v) return null
  const m = v.match(/^(\d{1,2}):?(\d{2})$/)
  if (!m || Number(m[1]) > 23 || Number(m[2]) > 59) throw new Error(`${label}: nhập giờ dạng HH:MM (24 giờ), ví dụ 07:30`)
  return `${m[1].padStart(2, '0')}:${m[2]}`
}

/** Số thập phân kiểu Việt Nam: 0.534 -> "0,53" */
export const soVN = (x, digits = 2) => (x == null ? '' : Number(x).toFixed(digits).replace('.', ','))

/** số phút -> "7 giờ 45 phút" / "45 phút" / "8 giờ" */
export function gioPhutChu(m) {
  if (m == null) return ''
  const h = Math.floor(m / 60)
  const p = m % 60
  if (!h) return `${p} phút`
  return p ? `${h} giờ ${p} phút` : `${h} giờ`
}

const THU = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy']
const THU_NGAN = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']
const thuSo = (iso) => new Date(`${iso.slice(0, 10)}T00:00:00Z`).getUTCDay()

/** "2026-10-30" -> "Thứ Sáu, 30/10/2026" */
export const thuNgay = (iso) => (iso ? `${THU[thuSo(iso)]}, ${ngay(iso)}` : '')
/** "2026-10-30" -> "T6" (Chủ nhật -> "CN") */
export const thuNgan = (iso) => THU_NGAN[thuSo(iso)]
export const laChuNhat = (iso) => thuSo(iso) === 0

/** Chữ cái đầu cho ảnh đại diện: "Nguyễn Văn An" -> "NA" */
export function chuCaiDau(name) {
  const words = String(name ?? '').trim().split(/\s+/).filter(Boolean)
  if (!words.length) return '?'
  const first = words[0][0]
  const last = words.length > 1 ? words[words.length - 1][0] : ''
  return (first + last).toUpperCase()
}
