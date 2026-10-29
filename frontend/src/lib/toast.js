// Thông báo nhỏ (toast) dùng chung cả ứng dụng: gọi được từ bất kỳ đâu (kể cả ngoài component, vd module gọi API).
// ToastHost (components/common/Toast.jsx) gắn một lần trong App để hiển thị.

let nextId = 0
let items = []
const subscribers = new Set()

const emit = () => subscribers.forEach((fn) => fn(items))

export function removeToast(id) {
  items = items.filter((t) => t.id !== id)
  emit()
}

export function showToast(message, type = 'info') {
  if (!message) return
  // cùng một lỗi lặp lại liên tục (vd mất mạng) thì không chồng nhiều toast giống nhau
  if (items.some((t) => t.message === message && t.type === type)) return
  const t = { id: ++nextId, message, type }
  items = [...items, t]
  emit()
  setTimeout(() => removeToast(t.id), type === 'error' ? 6000 : 3500)
}

export const toast = {
  success: (m) => showToast(m, 'success'),
  error: (m) => showToast(m, 'error'),
  warning: (m) => showToast(m, 'warning'),
  info: (m) => showToast(m, 'info'),
}

export function subscribeToasts(fn) {
  subscribers.add(fn)
  fn(items)
  return () => subscribers.delete(fn)
}
