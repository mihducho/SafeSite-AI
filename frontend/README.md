# SafeGate – giao diện chính (React)

Giao diện web quản lý chấm công SafeGate: React 18 + Vite 6, react-router 6, react-bootstrap (Bootstrap 5),
TanStack Query, axios. Mọi dữ liệu lấy từ backend FastAPI (thư mục gốc dự án) qua REST API, WebSocket `/ws/events` và
luồng hình MJPEG `/stream/gate`. Giao diện Jinja2 cũ vẫn giữ làm dự phòng ở `/cu/`.

## Hai cách chạy

**Chế độ phát triển** (sửa giao diện, tự tải lại khi lưu file): 2 cửa sổ lệnh

```bash
.\web                     # cửa sổ 1, ở thư mục gốc dự án: backend cổng 8000
cd frontend
npm install               # lần đầu
npm run dev               # cửa sổ 2: mở http://localhost:3000
```

Vite chuyển `/api`, `/ws` (WebSocket), `/stream`, `/docs`, `/openapi.json`, `/cu`, `/static` sang `http://127.0.0.1:8000`, nên
trình duyệt coi như cùng một địa chỉ: cookie phiên `safegate_session` dùng chung, không cần CORS. Backend ở địa chỉ khác:
đặt biến môi trường `SAFEGATE_BACKEND` trước khi `npm run dev`.

**Chế độ demo** (hôm thi, không cần Node): build một lần, rồi chỉ chạy backend

```bash
cd frontend
npm run build             # -> frontend/dist
cd ..
.\web                     # mở http://127.0.0.1:8000
```

FastAPI phục vụ `frontend/dist` ở `/` (đường dẫn của giao diện như `/cong-nhan/5` trả `index.html`), không che `/api`, `/ws`,
`/stream`, `/docs`, `/cu`. Mọi font (Be Vietnam Pro, gói `@fontsource/be-vietnam-pro`), icon (Lucide, gói `lucide-react`),
thư viện đều nằm trong bản build, không tải từ mạng.

## Hệ thống thiết kế (giao diện v2)

Biến màu, cỡ chữ và các thành phần dùng chung ở `src/styles/global.css` (màn hình cổng: `src/pages/GateScreen.css`).

- Trang quản lý nền sáng `#F4F6FA`, thẻ trắng viền `#E5E7EB` bo 12px; sidebar `#0F172A`. Màn hình cổng nền tối `#0B1220`.
- Màu chủ đạo vàng an toàn `#F59E0B`, chữ trên nút vàng màu `#1F2937`. Mỗi trang một nút chính; nút nguy hiểm chỉ ở trang chi
  tiết hoặc cửa sổ xác nhận.
- Badge trạng thái (`lib/labels.js`): xanh = đạt / đã ghi giờ / đang làm; đỏ = không đạt / thiếu giờ ra / nghỉ việc; vàng = không
  xác định / không nhận ra / đi muộn / ngoài ca; xanh dương = chấm thủ công; xám = chưa vào / không ghi công / bỏ qua trùng.
- Không hiện mã kỹ thuật (`KHONG_DAT`, `bo_qua_trung`...), luôn đổi sang câu tiếng Việt; không dùng emoji.
- Thành phần dùng chung (`components/common/ui.jsx`): `PageHead`, `Card`, `StatCard`, `StatusBadge`, `Pill`, `Person` (avatar
  ảnh mẫu mặt đầu tiên hoặc chữ cái đầu trên nền pastel), `RowMenu` (nút "⋯"), `Tabs`, `Segmented`, `Meter`, `Skeleton`,
  `EmptyState`, `LiveStream` (luồng hình, đóng kết nối khi gỡ khỏi trang).

## Các trang

| Đường dẫn | Trang |
|---|---|
| `/login` | Đăng nhập (giữ trang đang mở trong `?next=`) |
| `/` | Tổng quan hôm nay: số liệu, số lượt theo giờ, lượt mới nhất (trực tiếp), người đang có mặt, trạng thái cổng |
| `/man-hinh-cong` | Màn hình cổng toàn màn hình: hình camera dọc, kết quả xanh/đỏ/vàng, đọc thông báo tiếng Việt |
| `/cong-nhan`, `/cong-nhan/:id` | Danh sách công nhân; chi tiết: đồng ý, mẫu khuôn mặt (chụp từ camera cổng, tải ảnh lên), lịch sử, bảng công |
| `/to-doi` | Tổ đội |
| `/lich-su` | Lịch sử lượt kiểm tra (lọc, phân trang, ảnh, chi tiết lượt, đánh giá đúng / báo nhầm, chấm thủ công) |
| `/bang-cong`, `/bang-cong-thang` | Bảng công ngày (chấm công thủ công, bắt buộc lý do) / tháng (xuất Excel) |
| `/cau-hinh-ca` | Ca làm |
| `/cau-hinh-cong` | Nguồn camera, góc xoay, khởi động lại cổng, xem trước, vẽ vùng kiểm tra |

## Cấu trúc

```
src/
├── main.jsx              # Redux + QueryClient (toast lỗi chung) + Router
├── App.jsx               # định tuyến; /man-hinh-cong nằm ngoài khung quản lý (toàn màn hình)
├── api/client.js         # axios: gửi cookie, lỗi -> câu tiếng Việt, 401 -> về trang đăng nhập
├── api/endpoints.js      # mọi hàm gọi API + đường dẫn ảnh / luồng hình
├── lib/events.js         # 1 WebSocket /ws/events dùng chung, tự kết nối lại sau 2 giây
├── lib/format.js         # ngày dd/mm/yyyy, giờ 24 giờ theo giờ Việt Nam, ô giờ HH:MM
├── lib/labels.js         # nhãn + màu trạng thái (xanh = đạt/ghi công, đỏ = không đạt, vàng = không xác định)
├── lib/toast.js          # thông báo nhỏ dùng chung
├── hooks/useWebConfig.js # tham số từ settings.yaml qua /api/cau-hinh-web
├── components/           # khung quản lý (sidebar, thanh trên), logo, toast, hộp xác nhận, bảng + chi tiết lượt,
│                         # chấm công thủ công, thành phần dùng chung (ui.jsx)
└── pages/                # từng trang
tests/giao_dien.spec.js   # kiểm thử giao diện (Playwright)
```

## Kiểm thử giao diện

Cần backend đang chạy (chế độ demo ở cổng 8000, hoặc đặt `SAFEGATE_URL`). Chạy trên Microsoft Edge có sẵn trong máy.

```powershell
$env:SAFEGATE_PASSWORD = "<ADMIN_PASSWORD trong .env>"; npm run test:ui; Remove-Item Env:SAFEGATE_PASSWORD
```

## Lưu ý

- **Giọng đọc**: Web Speech API (giọng `vi`), ưu tiên giọng cài sẵn trong máy. Dùng **Microsoft Edge** (có giọng "Microsoft An").
  Trình duyệt chặn phát tiếng khi chưa bấm gì: bấm "Bật âm thanh" trên màn hình cổng. Không có giọng tiếng Việt thì phát tiếng bíp.
- **Hình camera**: luôn qua backend `/stream/gate`, không mở thẳng URL DroidCam (chỉ nhận 1 kết nối). Khi gỡ khỏi trang, thẻ ảnh
  được đổi sang ảnh trống để trình duyệt đóng luồng MJPEG (nếu không, chuyển trang vài lần sẽ hết 6 kết nối tới máy chủ).
