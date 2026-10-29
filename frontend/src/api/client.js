import axios from 'axios'
import store from '../store/index.js'
import { clearUser } from '../store/authSlice.js'

/**
 * Module gọi API dùng chung. Luôn dùng đường dẫn tương đối /api/... (chế độ phát triển: Vite chuyển sang backend;
 * chế độ demo: chính FastAPI phục vụ giao diện) nên cookie phiên đăng nhập gửi kèm tự động, không cần CORS.
 * - Lỗi: error.message là câu tiếng Việt (backend trả {"detail": "..."}; lỗi kiểm tra dữ liệu 422 là một danh sách).
 * - 401 (hết phiên): xoá người dùng trong store -> ProtectedRoute chuyển về /login?next=<trang đang xem>.
 * Toast lỗi do QueryClient (main.jsx) hiện chung cho mọi query/mutation, nên trang không phải tự bắt lỗi.
 */
const client = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

export function thongBaoLoi(error) {
  const res = error?.response
  if (res) {
    const detail = res.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((e) => (e.loc ? `${e.loc.filter((x) => x !== 'body').join('.')}: ` : '') + e.msg).join('; ')
    }
    if (res.status === 413) return 'Tệp tải lên quá lớn'
    if (res.status === 404) return 'Không tìm thấy dữ liệu'
    if (res.status >= 500) return `Lỗi máy chủ (${res.status}), xem cửa sổ chạy backend`
    return `Lỗi ${res.status}`
  }
  if (error?.request) return 'Không kết nối được máy chủ (backend chưa chạy hoặc mất mạng)'
  return error?.message || 'Có lỗi xảy ra'
}

// Kiểm tra phiên lúc mở trang (/toi) và đăng nhập sai (/dang-nhap) cũng trả 401: không coi là hết phiên.
const KHONG_DANG_XUAT = ['/toi', '/dang-nhap']

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url ?? ''
    if (error.response?.status === 401 && !KHONG_DANG_XUAT.some((p) => url.startsWith(p))) {
      store.dispatch(clearUser())
    }
    error.message = thongBaoLoi(error)
    return Promise.reject(error)
  },
)

export default client
