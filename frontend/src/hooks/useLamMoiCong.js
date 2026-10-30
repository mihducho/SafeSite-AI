import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'

/**
 * Sau mỗi thao tác chấm công (phiên, phép, xác nhận không phép): tải lại mọi bảng có thể đổi số liệu:
 * ngày công đang mở, bảng công ngày / tháng, bảng công của công nhân, danh sách phép, Việc cần xử lý, Tổng quan.
 */
export function useLamMoiCong() {
  const qc = useQueryClient()
  return useCallback(() => {
    for (const key of ['ngay-cong', 'bang-cong-ngay', 'bang-cong-thang', 'bang-cong-cn', 'phep', 'viec-can-xu-ly', 'tong-quan']) {
      qc.invalidateQueries({ queryKey: [key] })
    }
  }, [qc])
}
