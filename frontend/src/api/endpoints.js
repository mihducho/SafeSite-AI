import client from './client.js'

// Mọi hàm gọi API của backend (DE_TAI.md mục 8, 9.1). Tên trường giữ nguyên như API trả về.
const data = (r) => r.data

// ─── ĐĂNG NHẬP ─────────────────────────────────────────────────────────────────
/** { username, password } -> { id, username, full_name } (đặt cookie phiên) */
export const dangNhap = (credentials) => client.post('/dang-nhap', credentials).then(data)
export const dangXuat = () => client.post('/dang-xuat').then(data)
/** Người đang đăng nhập { id, username, full_name, role }; chưa đăng nhập -> 401 */
export const layThongTinToi = () => client.get('/toi').then(data)
/** Tham số giao diện từ settings.yaml: ngày hôm nay (giờ VN), số mẫu tối thiểu/tối đa, số giây hiện kết quả... */
export const layCauHinhWeb = () => client.get('/cau-hinh-web').then(data)

// ─── TỔNG QUAN ─────────────────────────────────────────────────────────────────
export const layTongQuan = () => client.get('/tong-quan').then(data)

// ─── CÔNG NHÂN ─────────────────────────────────────────────────────────────────
/** params: { q, to_doi, trang_thai } -> { tong, ds } */
export const layDanhSachCongNhan = (params = {}) => client.get('/cong-nhan', { params }).then(data)
export const taoMoiCongNhan = (body) => client.post('/cong-nhan', body).then(data)
export const layChiTietCongNhan = (id) => client.get(`/cong-nhan/${id}`).then(data)
export const capNhatCongNhan = (id, body) => client.patch(`/cong-nhan/${id}`, body).then(data)
/** Cho nghỉ việc: backend xoá toàn bộ mẫu khuôn mặt -> { so_mau_da_xoa, ... } */
export const nghiViec = (id) => client.post(`/cong-nhan/${id}/nghi-viec`).then(data)
export const diLamLai = (id) => client.post(`/cong-nhan/${id}/di-lam-lai`).then(data)
/** Bảng công các ngày gần đây của một người -> { ds } */
export const layBangCongCongNhan = (id, soNgay = 14) =>
  client.get(`/cong-nhan/${id}/bang-cong`, { params: { so_ngay: soNgay } }).then(data)

// ─── ĐỒNG Ý + MẪU KHUÔN MẶT ───────────────────────────────────────────────────
export const layNoiDungDongY = () => client.get('/dong-y/noi-dung').then(data)
export const ghiNhanDongY = (id) => client.post(`/cong-nhan/${id}/dong-y`, { dong_y: true }).then(data)
/** -> { so_mau, toi_thieu, toi_da, du_mau, da_dong_y, ds: [{ id, quality, source, anh }] } */
export const layDanhSachMauMat = (id) => client.get(`/cong-nhan/${id}/mau-mat`).then(data)
/** Chụp 1 mẫu từ khung hình hiện tại của camera cổng (không mở camera riêng) */
export const chupMauMat = (id) => client.post(`/cong-nhan/${id}/mau-mat/chup`).then(data)
/** FormData nhiều ảnh (trường "files") -> { ket_qua: [{ ten, ok, ly_do }], so_mau } */
export const taiLenMauMat = (id, formData) => client.post(`/cong-nhan/${id}/mau-mat/tai-len`, formData).then(data)
export const xoaMauMat = (sampleId) => client.delete(`/mau-mat/${sampleId}`).then(data)
export const xoaTatCaMauMat = (id) => client.delete(`/cong-nhan/${id}/mau-mat`).then(data)

// ─── TỔ ĐỘI ────────────────────────────────────────────────────────────────────
export const layDanhSachToDoi = () => client.get('/to-doi').then(data)
export const taoMoiToDoi = (body) => client.post('/to-doi', body).then(data)
export const capNhatToDoi = (id, body) => client.patch(`/to-doi/${id}`, body).then(data)

// ─── LƯỢT KIỂM TRA ─────────────────────────────────────────────────────────────
/** params: { ngay, cong_nhan_id, ket_qua, hanh_dong, trang, so_dong } -> { tong, trang, so_trang, ds } */
export const layLichSuLuot = (params = {}) => client.get('/luot', { params }).then(data)
export const layChiTietLuot = (id) => client.get(`/luot/${id}`).then(data)
/** danhGia: 'dung' | 'bao_nham' | null */
export const danhGiaLuot = (id, danhGia) => client.patch(`/luot/${id}/danh-gia`, { danh_gia: danhGia }).then(data)

// ─── CHẤM CÔNG ─────────────────────────────────────────────────────────────────
/** { worker_id, ngay, gio_vao, gio_ra, ly_do } (lý do bắt buộc) */
export const chamCongThuCong = (body) => client.post('/cham-cong-thu-cong', body).then(data)
export const layBangCongNgay = (params = {}) => client.get('/bang-cong', { params }).then(data)
export const layBangCongThang = (params = {}) => client.get('/bang-cong/thang', { params }).then(data)
export const taiExcelThang = (params = {}) =>
  client.get('/bang-cong/thang/excel', { params, responseType: 'blob' }).then(data)

// ─── CHẤM CÔNG V2: PHIÊN, PHÉP, NHẬT KÝ, VIỆC CẦN XỬ LÝ ───────────────────────
/** Bảng công 1 ngày của 1 công nhân: trạng thái, các phiên, các phép, nhật ký sửa */
export const layNgayCong = (workerId, ngay) => client.get(`/bang-cong/cong-nhan/${workerId}/${ngay}`).then(data)
/** { worker_id, ngay, gio_vao, gio_ra?, ly_do } -> { phien, ngay } */
export const themPhien = (body) => client.post('/phien', body).then(data)
/** { gio_vao?, gio_ra?, ly_do } (giờ ra cho phiên mở / thiếu giờ ra = đóng phiên) */
export const suaPhien = (id, body) => client.patch(`/phien/${id}`, body).then(data)
export const huyPhien = (id, lyDo) => client.post(`/phien/${id}/huy`, { ly_do: lyDo }).then(data)
/** params: { worker_id, ngay, tu, den, ca_huy } -> { ds } */
export const layDanhSachPhep = (params = {}) => client.get('/phep', { params }).then(data)
/** { worker_id, ngay, loai, tu_gio?, den_gio?, tinh_cong?, ly_do } */
export const themPhep = (body) => client.post('/phep', body).then(data)
export const huyPhep = (id, lyDo) => client.post(`/phep/${id}/huy`, { ly_do: lyDo }).then(data)
/** -> { tong, ds: [{ loai, ten_loai, attendance_id, worker_id, ma, ho_ten, ngay, mo_ta, phut, segment_id, ... }] } */
export const layViecCanXuLy = () => client.get('/viec-can-xu-ly').then(data)
export const xacNhanKhongPhep = (attendanceId, lyDo) =>
  client.post('/viec-can-xu-ly/xac-nhan-khong-phep', { attendance_id: attendanceId, ly_do: lyDo || null }).then(data)

// ─── CA LÀM ────────────────────────────────────────────────────────────────────
export const layCaLam = () => client.get('/ca-lam').then(data)
/** -> { ...ca, so_dong_tinh_lai } (bảng công hôm nay được tính lại) */
export const capNhatCaLam = (body) => client.patch('/ca-lam', body).then(data)

// ─── CỔNG ──────────────────────────────────────────────────────────────────────
export const layCauHinhCong = () => client.get('/cong').then(data)
/** { name, camera_source, rotate, zone, khoi_dong_lai } -> { ...cổng, ghi_chu } */
export const capNhatCauHinhCong = (body) => client.patch('/cong', body).then(data)
export const layTrangThaiCong = () => client.get('/cong/trang-thai').then(data)
export const khoiDongLaiCong = () => client.post('/cong/khoi-dong-lai').then(data)

// ─── ĐƯỜNG DẪN ẢNH / LUỒNG HÌNH (dùng làm src của <img>) ───────────────────────
export const STREAM_URL = '/stream/gate'      // luồng hình qua backend, KHÔNG mở thẳng URL DroidCam (chỉ 1 kết nối)
export const getUrlAnhMauMat = (sampleId) => `/api/mau-mat/${sampleId}/anh`
export const getUrlAnhLuot = (luotId) => `/api/luot/${luotId}/anh`
export const getUrlAnhHienTai = () => `/api/cong/anh-hien-tai?t=${Date.now()}`
