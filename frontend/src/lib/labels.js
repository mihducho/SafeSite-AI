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
 * Trạng thái ngày công DO BACKEND TÍNH (trường trang_thai_ngay + ten_trang_thai, docs/LOGIC_CHAM_CONG.md mục 10).
 * Giao diện chỉ chọn tông màu theo mã, không tự suy ra trạng thái. kind = lớp màu ô ở bảng công tháng.
 */
export const TRANG_THAI_NGAY = {
  dang_lam: ['Đang làm', 'info', 'dang'],
  thieu_gio_ra: ['Thiếu giờ ra', 'bad', 'thieu'],
  du_cong: ['Đủ công', 'ok', 'du'],
  di_muon: ['Đi muộn', 'warn', 'muon'],
  ve_som: ['Về sớm', 'warn', 'muon'],
  di_muon_ve_som: ['Đi muộn, về sớm', 'warn', 'muon'],
  di_muon_co_phep: ['Đi muộn có phép', 'info', 'phep'],
  ve_som_co_phep: ['Về sớm có phép', 'info', 'phep'],
  chua_vao: ['Chưa vào', 'neutral', 'trong'],
  vang: ['Vắng', 'bad', 'vang'],
  nghi_tuan: ['Nghỉ tuần', 'neutral', 'nghi'],
  nghi_phep: ['Nghỉ phép', 'info', 'nghiphep'],
  chua_den: ['Chưa đến', 'neutral', 'trong'],
  ngoai_thoi_gian_lam_viec: ['Ngoài thời gian làm việc', 'neutral', 'ngoai'],
}

/** Dòng bảng công (API) -> [chữ, tông] theo trạng thái backend */
export function trangThaiNgay(r) {
  const [text, tone] = TRANG_THAI_NGAY[r.trang_thai_ngay] ?? [r.ten_trang_thai ?? '', 'neutral']
  return [r.ten_trang_thai ?? text, tone]
}

export const TRANG_THAI_PHIEN = {
  mo: ['Đang mở', 'info'],
  dong: ['Đã đóng', 'ok'],
  thieu_gio_ra: ['Thiếu giờ ra', 'bad'],
  huy: ['Đã huỷ', 'neutral'],
}
export const NGUON = { tu_dong: 'Tự động', thu_cong: 'Thủ công' }

export const LOAI_PHEP = {
  ve_som: 'Về sớm',
  di_muon: 'Đi muộn',
  ra_ngoai_cong_viec: 'Ra ngoài vì công việc',
  nghi_ca_ngay: 'Nghỉ cả ngày',
}

export const NHAT_KY = {
  them_phien: 'Thêm phiên',
  sua_vao: 'Sửa giờ vào',
  sua_ra: 'Sửa giờ ra',
  huy_phien: 'Huỷ phiên',
  dong_khi_nghi_viec: 'Đóng phiên khi nghỉ việc',
  them_phep: 'Thêm phép',
  huy_phep: 'Huỷ phép',
  xac_nhan_khong_phep: 'Xác nhận không phép',
  bao_nham: 'Báo nhầm',
}

/** Loại mục trong Việc cần xử lý -> [chữ, tông] */
export const VIEC = {
  thieu_gio_ra: ['Thiếu giờ ra', 'bad'],
  di_muon_khong_phep: ['Đi muộn chưa có phép', 'warn'],
  ve_som_khong_phep: ['Về sớm chưa có phép', 'warn'],
}

/** Ngày nghỉ hằng tuần (Cấu hình ca): [mã, chữ ngắn, chữ đủ] */
export const THU_TUAN = [
  ['thu_hai', 'T2', 'Thứ Hai'], ['thu_ba', 'T3', 'Thứ Ba'], ['thu_tu', 'T4', 'Thứ Tư'], ['thu_nam', 'T5', 'Thứ Năm'],
  ['thu_sau', 'T6', 'Thứ Sáu'], ['thu_bay', 'T7', 'Thứ Bảy'], ['chu_nhat', 'CN', 'Chủ nhật'],
]

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
