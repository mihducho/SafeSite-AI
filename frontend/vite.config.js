import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Chế độ phát triển (npm run dev, cổng 3000): Vite chuyển các đường dẫn của backend sang FastAPI (cổng 8000).
// Trình duyệt chỉ thấy một địa chỉ (localhost:3000) nên cookie đăng nhập dùng chung, không vướng CORS.
// Frontend chỉ gọi đường dẫn tương đối (/api/...). Đổi địa chỉ backend: đặt biến môi trường SAFEGATE_BACKEND.
const BACKEND = process.env.SAFEGATE_BACKEND || 'http://127.0.0.1:8000'
const toBackend = { target: BACKEND, changeOrigin: true }

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': toBackend,
      '/stream': toBackend,                    // luồng hình MJPEG của camera cổng
      '/ws': { ...toBackend, ws: true },       // WebSocket /ws/events
      '/docs': toBackend,                      // thử API (Swagger)
      '/openapi.json': toBackend,
      '/cu': toBackend,                        // giao diện cũ (Jinja2) giữ làm dự phòng
      '/static': toBackend,                    // file tĩnh của giao diện cũ
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1000,
  },
})
