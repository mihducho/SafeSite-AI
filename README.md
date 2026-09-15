# LostLens — Hệ thống AI Multi-camera hỗ trợ tìm kiếm trẻ lạc

Đồ án tốt nghiệp. Hệ thống hỗ trợ tìm kiếm trẻ lạc qua nhiều camera bằng
Cross-camera Re-Identification kết hợp thuộc tính ngoại hình (attribute-augmented Re-ID),
tích hợp cảnh báo bất thường thời gian thực.

## Phạm vi

- Detection + single-camera tracking: YOLOv11 + BoT-SORT
- Cross-camera Re-ID cho trẻ em: appearance embedding + attribute (màu áo/quần, phụ kiện, tóc)
- Tìm kiếm theo ảnh hoặc theo mô tả thuộc tính
- Cảnh báo bất thường (rule-based): đứng một mình quá lâu, tách khỏi người lớn đi cùng
- Demo: 2-3 camera/video giả lập, không triển khai thực tế lên không gian công cộng

## Cấu trúc thư mục

```
src/
  detection/   # YOLO — fine-tune, inference
  tracking/    # BoT-SORT integration
  reid/        # Embedding model, training, evaluation (Rank-1/mAP)
  attribute/   # Attribute classification heads, joint loss
  search/      # Vector search (FAISS), re-ranking theo attribute
  utils/       # Video I/O, visualization, shared helpers
data/
  raw/         # Video/ảnh gốc (không commit — xem .gitignore)
  processed/   # Frame đã crop, dataset đã xử lý
  annotations/ # Nhãn bounding box + attribute
configs/       # File cấu hình training/inference (yaml)
notebooks/     # Thử nghiệm nhanh, phân tích kết quả
scripts/       # Script chạy training/eval/demo
docs/
  related_work/ # Tổng hợp paper khảo sát
tests/
```

## Môi trường

- Python 3.13, không có GPU rời trên máy dev — training các model nặng
  (Re-ID, attribute) thực hiện trên Google Colab/Kaggle, máy local dùng để
  phát triển và test tích hợp pipeline với model nhỏ (YOLOv11n).

## Trạng thái

- [x] Khảo sát related work, chốt phạm vi đề tài
- [ ] Phase 1: Detection + Tracking baseline chạy trên video mẫu
- [ ] Phase 2: Re-ID + Attribute training
- [ ] Phase 3: Tích hợp multi-camera + search + alert
- [ ] Phase 4: Đánh giá, viết luận văn
