// Nhãn tiếng Việt + tông màu cho các mã trong CSDL (không bao giờ hiện mã kỹ thuật như KHONG_DAT ra giao diện).
// Tông màu (badge chữ đậm trên nền nhạt, styles/global.css .pill):
//   ok      xanh  : đạt, đã ghi giờ vào/ra, đang làm, đã đồng ý
//   bad     đỏ    : không đạt, thiếu giờ ra, nghỉ việc
//   warn    vàng  : không xác định, nhiều người, không nhận ra, đi muộn, ngoài ca
//   info    xanh dương: chấm thủ công
//   neutral xám   : chưa vào, không có người, bỏ qua trùng, không ghi công

export const KET_QUA = {
  DAT: ['Đạt', 'ok'],
  KHONG_DAT: ['Không đạt', 'bad'],
  KHONG_XAC_DINH: ['Không xác định', 'warn'],
  NHIEU_NGUOI: ['Nhiều người', 'warn'],
  KHONG_CO_NGUOI: ['Không có người', 'neutral'],
}

export const HANH_DONG = {
  ghi_vao: ['Đã ghi giờ vào', 'ok'],
  ghi_ra: ['Đã ghi giờ ra', 'ok'],
  bo_qua_trung: ['Bỏ qua trùng', 'neutral'],
  khong_ghi: ['Không ghi công', 'neutral'],
}

export const MAT = {
  DA_NHAN_RA: ['Đã nhận ra', 'ok'],
  KHONG_NHAN_RA: ['Không nhận ra', 'warn'],
  KHONG_THAY_MAT: ['Không thấy mặt', 'warn'],
}

export const CHAM_CONG = {
  binh_thuong: ['Bình thường', 'ok'],
  ngoai_ca: ['Ngoài ca', 'warn'],
  cham_thu_cong: ['Chấm thủ công', 'info'],
  chua_vao: ['Chưa vào', 'neutral'],
}

export const CONG_NHAN = {
  dang_lam: ['Đang làm', 'ok'],
  nghi_viec: ['Nghỉ việc', 'bad'],
}

export const HUONG = { vao: 'Vào', ra: 'Ra' }

export const THIEU = { thieu_mu: 'thiếu mũ bảo hộ', thieu_ao: 'thiếu áo phản quang' }
export const THIEU_NGAN = { thieu_mu: 'Mũ bảo hộ', thieu_ao: 'Áo phản quang' }
export const DO_BAO_HO = { hardhat: 'mũ bảo hộ', vest: 'áo phản quang' }   // tên món trong ppe.items (settings.yaml)
export const DO_BAO_HO_TEN = { hardhat: 'Mũ bảo hộ', vest: 'Áo phản quang' }

/** ["thieu_mu", "thieu_ao"] -> "Thiếu mũ bảo hộ, thiếu áo phản quang" (viết hoa chữ đầu) */
export function thieuText(list) {
  const s = (list ?? []).map((t) => THIEU[t] ?? t).join(', ')
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
}

/**
 * Trạng thái một dòng bảng công ngày bằng chữ dễ hiểu:
 * Thiếu giờ ra / Chấm thủ công / Ngoài ca / Đã ra / Đang làm / Chưa vào.
 */
export function trangThaiNgay(r) {
  if (r.thieu_gio_ra) return ['Thiếu giờ ra', 'bad']
  if (r.trang_thai === 'cham_thu_cong') return ['Chấm thủ công', 'info']
  if (r.trang_thai === 'ngoai_ca') return ['Ngoài ca', 'warn']
  if (r.gio_ra) return ['Đã ra', 'ok']
  if (r.gio_vao) return ['Đang làm', 'ok']
  return ['Chưa vào', 'neutral']
}

/** Trạng thái cổng (sự kiện trang_thai + tình trạng WebSocket) bằng câu dễ hiểu -> [câu ngắn, câu dài, tông] */
export function trangThaiCong(st, ws) {
  if (ws === 'mat') return ['Mất kết nối máy chủ', 'Mất kết nối tới máy chủ, đang kết nối lại', 'bad']
  if (ws !== 'mo' || !st) return ['Đang kết nối', 'Đang kết nối tới cổng', 'warn']
  if (st.mat_camera) return ['Mất kết nối camera', 'Mất kết nối camera, đang thử lại', 'bad']
  if (st.trang_thai === 'dang_khoi_dong') return ['Đang khởi động', 'Cổng đang khởi động camera', 'warn']
  if (st.trang_thai === 'tat') return ['Cổng đang tắt', 'Cổng đang tắt', 'bad']
  if (st.trang_thai === 'dang_chay' && !st.loi) {
    return st.pha === 'KIEM_TRA'
      ? ['Đang kiểm tra', 'Đang kiểm tra một người tại cổng', 'warn']
      : ['Cổng đang chạy', 'Cổng đang hoạt động, sẵn sàng kiểm tra', 'ok']
  }
  return ['Cổng gặp lỗi', 'Hệ thống kiểm tra tạm gián đoạn', 'bad']
}
