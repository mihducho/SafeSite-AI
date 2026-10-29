import { defineConfig } from '@playwright/test'

// Kiểm thử giao diện tự động (npm run test:ui). Chạy trên Microsoft Edge có sẵn trong máy (không tải trình duyệt).
// Cần backend đang chạy và đã build giao diện (chế độ demo, cổng 8000) hoặc chạy npm run dev (đặt SAFEGATE_URL).
// Tài khoản lấy từ biến môi trường SAFEGATE_USER / SAFEGATE_PASSWORD (không ghi mật khẩu vào code).
export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.SAFEGATE_URL || 'http://127.0.0.1:8000',
    channel: 'msedge',
    headless: true,
    viewport: { width: 1400, height: 900 },
    locale: 'vi-VN',
  },
})
