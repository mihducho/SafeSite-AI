import { expect, test } from '@playwright/test'

// Kịch bản ngắn: đăng nhập -> mở từng trang -> có dữ liệu thật từ API -> không có lỗi JavaScript / lỗi API.
// Chỉ đọc dữ liệu (không thêm, không sửa gì trong CSDL).
// Chạy (PowerShell):  $env:SAFEGATE_USER="admin"; $env:SAFEGATE_PASSWORD="<mật khẩu admin trong .env>"; npm run test:ui

const USER = process.env.SAFEGATE_USER || 'admin'
const PASSWORD = process.env.SAFEGATE_PASSWORD

const PAGES = [
  ['/', 'Tổng quan hôm nay'],
  ['/cong-nhan', 'Công nhân'],
  ['/to-doi', 'Tổ đội'],
  ['/lich-su', 'Lịch sử kiểm tra'],
  ['/bang-cong', 'Bảng công'],
  ['/bang-cong-thang', 'Bảng công tháng'],
  ['/cau-hinh-ca', 'Ca làm'],
  ['/cau-hinh-cong', 'Cấu hình cổng'],
]

test.beforeAll(() => {
  if (!PASSWORD) throw new Error('Đặt biến môi trường SAFEGATE_PASSWORD (mật khẩu admin trong .env) trước khi chạy')
})

test('đăng nhập, mở từng trang, không lỗi', async ({ page }) => {
  // chưa đăng nhập -> về trang đăng nhập (giữ trang muốn mở trong ?next=). Lúc này /api/toi trả 401 là đúng.
  await page.goto('/lich-su')
  await expect(page).toHaveURL(/\/login\?next=%2Flich-su/)
  await page.locator('#username').fill(USER)
  await page.locator('#password').fill(PASSWORD)
  await page.locator('form button[type=submit]').click()
  await expect(page).toHaveURL(/\/lich-su/)

  // từ đây không được có lỗi JavaScript hay API lỗi nào
  const errors = []
  page.on('pageerror', (e) => errors.push(`JS: ${e.message}`))
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text()}`) })
  page.on('response', (r) => {
    const u = new URL(r.url())
    if (u.pathname.startsWith('/api/') && r.status() >= 400) errors.push(`API ${r.status()} ${u.pathname}`)
  })

  for (const [path, title] of PAGES) {
    await page.goto(path)
    await expect(page.locator('.section-title').first()).toContainText(title)
    await page.waitForLoadState('networkidle').catch(() => {})   // trang có luồng hình MJPEG không bao giờ "idle"
  }

  // chi tiết công nhân đầu tiên (nếu có)
  await page.goto('/cong-nhan?trang_thai=')
  const first = page.locator('table tbody tr td a').first()
  if (await first.count()) {
    await first.click()
    await expect(page.locator('.card-header', { hasText: 'Mẫu khuôn mặt' })).toBeVisible()
    await expect(page.locator('text=Đồng ý đăng ký khuôn mặt')).toBeVisible()
  }

  // màn hình cổng: toàn màn hình, có ô kết quả và nút bật âm thanh, WebSocket báo trạng thái cổng
  await page.goto('/man-hinh-cong')
  await expect(page.locator('.gate-result')).toBeVisible()
  await expect(page.getByRole('button', { name: /Bật âm thanh/ })).toBeVisible()
  await expect(page.locator('.gate-chip')).not.toHaveText(/Đang kết nối/, { timeout: 10_000 })

  // Chuyển trang trong ứng dụng (bấm menu, không tải lại) qua lại giữa các trang có luồng hình MJPEG nhiều lần:
  // luồng cũ phải được đóng, nếu không trình duyệt hết 6 kết nối tới máy chủ và mọi lệnh gọi API bị kẹt.
  await page.goto('/')
  const apiOk = () => page.evaluate(() => Promise.race([
    fetch('/api/toi').then((r) => r.status),
    new Promise((res) => setTimeout(() => res('kẹt kết nối'), 5000)),
  ]))
  for (let i = 0; i < 5; i++) {
    await page.getByRole('link', { name: 'Cấu hình cổng' }).click()
    await expect(page.locator('img.sg-preview-portrait')).toBeVisible()
    await page.getByRole('link', { name: 'Tổng quan' }).click()
    await expect(page.locator('.stat-card').first()).toBeVisible()
  }
  expect(await apiOk()).toBe(200)

  // đăng xuất
  await page.goto('/')
  await page.getByRole('button', { name: /Đăng xuất/ }).click()
  await expect(page).toHaveURL(/\/login/)

  expect(errors, errors.join('\n')).toEqual([])
})
