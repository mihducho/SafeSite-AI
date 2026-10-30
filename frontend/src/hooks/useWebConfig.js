import { useQuery } from '@tanstack/react-query'
import { layCauHinhWeb } from '../api/endpoints.js'
import { homNay, MUI_GIO_MAC_DINH } from '../lib/format.js'

/**
 * Tham số giao diện lấy từ backend (settings.yaml qua /api/cau-hinh-web). Trong lúc chờ tải, dùng giá trị tạm
 * (loaded = false) để trang vẫn vẽ được.
 */
export function useWebConfig() {
  const { data } = useQuery({ queryKey: ['cau-hinh-web'], queryFn: layCauHinhWeb, staleTime: 5 * 60_000 })
  const tz = data?.mui_gio ?? MUI_GIO_MAC_DINH
  return {
    loaded: !!data,
    tz,
    today: homNay(tz),                                  // tính lại mỗi lần vẽ: qua nửa đêm vẫn đúng ngày
    minSamples: data?.mau_toi_thieu ?? 3,
    maxSamples: data?.mau_toi_da ?? 10,
    resultSeconds: data?.giay_hien_ket_qua ?? 5,
    pageSize: data?.so_dong_trang ?? 20,
    maxUploadMb: data?.tai_len_toi_da_mb ?? 10,
    nguongGiaiTrinh: data?.nguong_giai_trinh_phut ?? 15,   // đi muộn / về sớm không phép quá số phút này -> Việc cần xử lý
  }
}
