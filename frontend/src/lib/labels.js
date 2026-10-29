// Nhãn tiếng Việt + màu cho các mã trong CSDL. Màu thống nhất toàn giao diện:
// xanh lá (success) = đạt / ghi công, đỏ (danger) = không đạt, vàng (warning) = không xác định / không nhận ra,
// xám (secondary) = trung tính.

export const KET_QUA = {
  DAT: ['Đạt', 'success'],
  KHONG_DAT: ['Không đạt', 'danger'],
  KHONG_XAC_DINH: ['Không xác định', 'warning'],
  NHIEU_NGUOI: ['Nhiều người', 'warning'],
  KHONG_CO_NGUOI: ['Không có người', 'secondary'],
}

export const HANH_DONG = {
  ghi_vao: ['Ghi giờ vào', 'success'],
  ghi_ra: ['Ghi giờ ra', 'success'],
  bo_qua_trung: ['Bỏ qua (trùng)', 'secondary'],
  khong_ghi: ['Không ghi công', 'secondary'],
}

export const MAT = {
  DA_NHAN_RA: ['Đã nhận ra', 'success'],
  KHONG_NHAN_RA: ['Không nhận ra', 'warning'],
  KHONG_THAY_MAT: ['Không thấy mặt', 'secondary'],
}

export const CHAM_CONG = {
  binh_thuong: ['Bình thường', 'success'],
  ngoai_ca: ['Ngoài ca', 'warning'],
  cham_thu_cong: ['Chấm thủ công', 'info'],
  chua_vao: ['Chưa vào', 'secondary'],
}

export const CONG_NHAN = {
  dang_lam: ['Đang làm', 'success'],
  nghi_viec: ['Nghỉ việc', 'secondary'],
}

export const HUONG = { vao: 'Vào', ra: 'Ra' }

export const THIEU = { thieu_mu: 'thiếu mũ bảo hộ', thieu_ao: 'thiếu áo phản quang' }
export const THIEU_NGAN = { thieu_mu: '⛑ Mũ bảo hộ', thieu_ao: '🦺 Áo phản quang' }
export const DO_BAO_HO = { hardhat: 'mũ bảo hộ', vest: 'áo phản quang' }   // tên món trong ppe.items (settings.yaml)

export const thieuText = (list) => (list ?? []).map((t) => THIEU[t] ?? t).join(', ')
