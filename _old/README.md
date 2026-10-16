# _old/: file của hướng cũ (không dùng nữa)

Chuyển vào đây ở Giai đoạn 1a (2026-10-17), theo `docs/RA_SOAT.md` mục G và `DE_TAI.md` mục 10, 12.
Không xóa để còn tham khảo khi viết luận văn (phần "Vì sao đổi hướng"). Các script ở đây **không còn chạy được**
nếu không sửa đường dẫn import, vì đã rời khỏi `scripts/`.

| File | Lý do |
|---|---|
| `scripts/run_tracking_demo.py` | Demo Phase 1 hướng cũ (model COCO, lọc người nhầm xe máy) |
| `scripts/sanity_check.py` | Kiểm tra cài đặt bằng model COCO |
| `configs/botsort_tracking_reid.yaml` | `PersonTracker` không hỗ trợ ReID; thí nghiệm ReID không cải thiện |
| `configs/zones.yaml` | Vùng cấm (tọa độ pixel) của các video công trường thử nghiệm |
| `yolo11n.pt`, `yolo11m.pt` | Model COCO chỉ dùng cho demo và thí nghiệm hướng cũ (không nằm trong git) |
