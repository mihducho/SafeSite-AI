import { showToast } from '../lib/toast.js'

/**
 * Giữ tên cũ cho các trang: showToast(message, type) gửi tới ToastHost dùng chung (lib/toast.js).
 * @returns {{ showToast: (message: string, type?: 'success'|'error'|'warning'|'info') => void }}
 */
export function useToast() {
  return { showToast }
}
