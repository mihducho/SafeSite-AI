import { useEffect, useRef, useState } from 'react'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Spinner } from 'react-bootstrap'
import { useSearchParams } from 'react-router-dom'
import { FilterX } from 'lucide-react'
import { layDanhSachCongNhan, layLichSuLuot } from '../api/endpoints.js'
import CheckDetailModal from '../components/common/CheckDetailModal.jsx'
import CheckTable from '../components/common/CheckTable.jsx'
import ManualAttendanceModal from '../components/common/ManualAttendanceModal.jsx'
import { Card, PageHead, Pager, Segmented } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents } from '../lib/events.js'
import { doiNgay, gio, thuNgay } from '../lib/format.js'
import { HANH_DONG, KET_QUA } from '../lib/labels.js'

export default function HistoryPage() {
  const cfg = useWebConfig()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [checkId, setCheckId] = useState(null)
  const [manual, setManual] = useState(null)
  const reloadTimer = useRef(null)

  // Bộ lọc nằm trên địa chỉ trang (?ngay=...&cong_nhan_id=...) để tải lại / gửi link vẫn giữ.
  // Mở từ trang công nhân (?cong_nhan_id=) -> mặc định mọi ngày; còn lại mặc định hôm nay. "ngay=" (rỗng) = mọi ngày.
  const filter = {
    ngay: params.has('ngay') ? params.get('ngay') : (params.has('cong_nhan_id') ? '' : cfg.today),
    cong_nhan_id: params.get('cong_nhan_id') ?? '',
    ket_qua: params.get('ket_qua') ?? '',
    hanh_dong: params.get('hanh_dong') ?? '',
    trang: Number(params.get('trang') || 1),
  }
  const setFilter = (patch) => {
    const next = { ...filter, trang: 1, ...patch }
    const p = new URLSearchParams()
    p.set('ngay', next.ngay)
    for (const k of ['cong_nhan_id', 'ket_qua', 'hanh_dong']) if (next[k]) p.set(k, next[k])
    if (next.trang > 1) p.set('trang', next.trang)
    setParams(p, { replace: true })
  }

  const query = {
    ngay: filter.ngay || undefined, cong_nhan_id: filter.cong_nhan_id || undefined, ket_qua: filter.ket_qua || undefined,
    hanh_dong: filter.hanh_dong || undefined, trang: filter.trang, so_dong: cfg.pageSize,
  }
  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['lich-su-luot', query], queryFn: () => layLichSuLuot(query), placeholderData: keepPreviousData,
  })
  const { data: workers } = useQuery({ queryKey: ['cong-nhan', {}], queryFn: () => layDanhSachCongNhan() })

  // Lượt mới khi đang xem trang 1 -> tải lại
  useGateEvents((ev) => {
    if (ev.loai !== 'luot' || filter.trang !== 1) return
    clearTimeout(reloadTimer.current)
    reloadTimer.current = setTimeout(() => qc.invalidateQueries({ queryKey: ['lich-su-luot'] }), 300)
  })
  useEffect(() => () => clearTimeout(reloadTimer.current), [])

  const yesterday = doiNgay(cfg.today, -1)
  const quick = filter.ngay === cfg.today ? 'hom_nay' : filter.ngay === yesterday ? 'hom_qua' : filter.ngay === '' ? 'tat_ca' : null
  const filtered = !!(filter.cong_nhan_id || filter.ket_qua || filter.hanh_dong || filter.ngay !== cfg.today)
  const sub = data ? `${data.tong} lượt${filter.ngay ? ` · ${thuNgay(filter.ngay)}` : ' · mọi ngày'}` : ' '

  return (
    <div className="page">
      <PageHead title="Lịch sử kiểm tra" sub={sub}>{isFetching && !isLoading && <Spinner size="sm" />}</PageHead>

      <Card flush>
        <div className="filters">
          <Segmented ariaLabel="Chọn nhanh ngày" value={quick} onChange={(v) => setFilter({ ngay: v === 'hom_nay' ? cfg.today : v === 'hom_qua' ? yesterday : '' })}
            options={[{ value: 'hom_nay', label: 'Hôm nay' }, { value: 'hom_qua', label: 'Hôm qua' }, { value: 'tat_ca', label: 'Mọi ngày' }]} />
          <Form.Control type="date" value={filter.ngay} onChange={(e) => setFilter({ ngay: e.target.value })} aria-label="Ngày" style={{ width: 150 }} />
          <Form.Select value={filter.cong_nhan_id} onChange={(e) => setFilter({ cong_nhan_id: e.target.value })} aria-label="Công nhân" style={{ width: 180 }}>
            <option value="">Tất cả công nhân</option>
            {(workers?.ds ?? []).map((w) => <option key={w.id} value={w.id}>{w.full_name} ({w.code})</option>)}
          </Form.Select>
          <Form.Select value={filter.ket_qua} onChange={(e) => setFilter({ ket_qua: e.target.value })} aria-label="Kết quả" style={{ width: 145 }}>
            <option value="">Mọi kết quả</option>
            {Object.entries(KET_QUA).map(([k, [t]]) => <option key={k} value={k}>{t}</option>)}
          </Form.Select>
          <Form.Select value={filter.hanh_dong} onChange={(e) => setFilter({ hanh_dong: e.target.value })} aria-label="Chấm công" style={{ width: 175 }}>
            <option value="">Mọi kiểu chấm công</option>
            {Object.entries(HANH_DONG).map(([k, [t]]) => <option key={k} value={k}>{t}</option>)}
          </Form.Select>
          {filtered && (
            <Button variant="text" className="btn-text" onClick={() => setParams(new URLSearchParams({ ngay: cfg.today }), { replace: true })}>
              <FilterX size={16} />Bỏ lọc
            </Button>
          )}
        </div>
        <div className="table-wrap">
          <CheckTable ds={data?.ds} loading={isLoading} onOpen={setCheckId} onManual={setManual}
            dayTotals={filter.ngay && data ? { [filter.ngay]: data.tong } : undefined}
            emptyTitle={filtered ? 'Không có lượt nào khớp bộ lọc' : 'Hôm nay chưa có lượt kiểm tra nào'}
            emptyText={filtered ? 'Thử chọn ngày khác hoặc bỏ lọc.' : 'Lượt kiểm tra ở cổng sẽ hiện ở đây ngay khi có người đứng vào.'} />
        </div>
        {(data?.so_trang ?? 1) > 1 && (
          <div className="sg-card__foot">
            <span>Trang {data.trang}/{data.so_trang}</span>
            <Pager page={filter.trang} pages={data.so_trang} onChange={(p) => setFilter({ trang: p })} />
          </div>
        )}
      </Card>

      <CheckDetailModal id={checkId} onHide={() => setCheckId(null)} />
      {manual && (
        <ManualAttendanceModal worker={manual.cong_nhan} ngay={manual.thoi_diem.slice(0, 10)}
          gioVao={manual.huong !== 'ra' ? gio(manual.thoi_diem) : ''} gioRa={manual.huong === 'ra' ? gio(manual.thoi_diem) : ''}
          note={`từ lượt lúc ${gio(manual.thoi_diem, true)}`} onClose={() => setManual(null)} />
      )}
    </div>
  )
}
