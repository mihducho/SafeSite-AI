import { expect, test } from '@playwright/test'

// Kịch bản ngắn: đăng nhập -> mở từng trang -> có dữ liệu thật từ API -> không lỗi JavaScript / lỗi API,
// không còn emoji hay mã kỹ thuật (KHONG_DAT, bo_qua_trung...) trên giao diện. Chỉ đọc dữ liệu (không sửa gì trong CSDL).
// Chạy (PowerShell):  $env:SAFEGATE_USER="admin"; $env:SAFEGATE_PASSWORD="<mật khẩu admin trong .env>"; npm run test:ui

const USER = process.env.SAFEGATE_USER || 'admin'
const PASSWORD = process.env.SAFEGATE_PASSWORD

const PAGES = [
  ['/', 'Tổng quan hôm nay'],
  ['/cong-nhan', 'Công nhân'],
  ['/to-doi', 'Tổ đội'],
  ['/lich-su', 'Lịch sử kiểm tra'],
  ['/bang-cong', 'Bảng công ngày'],
  ['/bang-cong-thang', 'Bảng công tháng'],
  ['/cau-hinh-ca', 'Ca làm'],
  ['/cau-hinh-cong', 'Cấu hình cổng'],
]
const EMOJI = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{FE0F}]/u
const MA_KY_THUAT = /\b(KHONG_DAT|KHONG_XAC_DINH|NHIEU_NGUOI|KHONG_CO_NGUOI|DA_NHAN_RA|KHONG_NHAN_RA|KHONG_THAY_MAT|bo_qua_trung|khong_ghi|ghi_vao|ghi_ra|dang_lam|nghi_viec|binh_thuong|ngoai_ca|cham_thu_cong|chua_vao|KIEM_TRA|CHO_ROI_DI)\b/

async function giaoDienSach(page, path) {
  const text = await page.locator('body').innerText()
  expect(text, `${path}: còn emoji`).not.toMatch(EMOJI)
  expect(text, `${path}: còn mã kỹ thuật`).not.toMatch(MA_KY_THUAT)
}

test.beforeAll(() => {
  if (!PASSWORD) throw new Error('Đặt biến môi trường SAFEGATE_PASSWORD (mật khẩu admin trong .env) trước khi chạy')
})

test('đăng nhập, mở từng trang, không lỗi', async ({ page }) => {
  // chưa đăng nhập -> về trang đăng nhập (giữ trang muốn mở trong ?next=). Lúc này /api/toi trả 401 là đúng.
  await page.goto('/lich-su')
  await expect(page).toHaveURL(/\/login\?next=%2Flich-su/)
  await giaoDienSach(page, '/login')
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
    await expect(page.locator('.page-head h1').first()).toHaveText(title)
    await page.waitForLoadState('networkidle').catch(() => {})   // trang có luồng hình MJPEG không bao giờ "idle"
    await giaoDienSach(page, path)
  }

  // chi tiết công nhân đầu tiên (nếu có): tab Khuôn mặt có khối đồng ý
  await page.goto('/cong-nhan?trang_thai=')
  const first = page.locator('table tbody tr.clickable').first()
  if (await first.count()) {
    await first.click()
    await expect(page.getByRole('tab', { name: /Khuôn mặt/ })).toBeVisible()
    await expect(page.getByText('Đồng ý đăng ký khuôn mặt')).toBeVisible()
    await giaoDienSach(page, 'chi tiết công nhân')
  }

  // màn hình cổng: toàn màn hình, có ô kết quả, loa luôn bật (không có nút tắt), WebSocket báo trạng thái cổng
  await page.goto('/man-hinh-cong')
  await expect(page.locator('.gs-box')).toBeVisible()
  await expect(page.locator('.gs-top')).toContainText(/Loa đang bật|Chạm để bật loa/)
  await expect(page.getByRole('button', { name: /Tắt loa|Bật âm thanh/ })).toHaveCount(0)
  await expect(page.locator('.gs-status')).not.toHaveText(/Đang kết nối/, { timeout: 10_000 })
  await giaoDienSach(page, '/man-hinh-cong')

  // Chuyển trang trong ứng dụng (bấm menu, không tải lại) qua lại giữa các trang có luồng hình MJPEG nhiều lần:
  // luồng cũ phải được đóng, nếu không trình duyệt hết 6 kết nối tới máy chủ và mọi lệnh gọi API bị kẹt.
  await page.goto('/')
  const apiOk = () => page.evaluate(() => Promise.race([
    fetch('/api/toi').then((r) => r.status),
    new Promise((res) => setTimeout(() => res('kẹt kết nối'), 5000)),
  ]))
  for (let i = 0; i < 5; i++) {
    await page.getByRole('link', { name: 'Cấu hình cổng' }).click()
    await expect(page.locator('img.portrait').first()).toBeVisible()
    await page.getByRole('link', { name: 'Tổng quan' }).click()
    await expect(page.locator('.stat').first()).toBeVisible()
  }
  expect(await apiOk()).toBe(200)

  // đăng xuất (menu người dùng ở thanh trên)
  await page.goto('/')
  await page.locator('.user-btn').click()
  await page.getByRole('button', { name: /Đăng xuất/ }).click()
  await expect(page).toHaveURL(/\/login/)

  expect(errors, errors.join('\n')).toEqual([])
})
