import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { CalendarSearch, CircleCheckBig, ClipboardList, DoorClosed, ShieldX } from 'lucide-react'
import { layViecCanXuLy, xacNhanKhongPhep } from '../api/endpoints.js'
import LeaveModal from '../components/common/LeaveModal.jsx'
import ManualAttendanceModal from '../components/common/ManualAttendanceModal.jsx'
import ReasonModal from '../components/common/ReasonModal.jsx'
import { Card, EmptyRow, PageHead, Person, Pill, Segmented, SkeletonRows } from '../components/common/ui.jsx'
import { useLamMoiCong } from '../hooks/useLamMoiCong.js'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents } from '../lib/events.js'
import { thuNgay } from '../lib/format.js'
import { VIEC } from '../lib/labels.js'
import { toast } from '../lib/toast.js'

const LOC = ['thieu_gio_ra', 'di_muon_khong_phep', 've_som_khong_phep']

/**
 * Việc cần xử lý (Q9, Q14, Q21): ngày thiếu giờ ra; ngày đi muộn / về sớm chưa có phép quá ngưỡng. Mỗi mục có nút xử lý
 * nhanh; xử lý xong (nhập giờ ra, thêm phép, xác nhận không phép) thì backend không còn trả mục đó -> tự biến mất.
 */
export default function TodoPage() {
  const navigate = useNavigate()
  const cfg = useWebConfig()
  const lamMoi = useLamMoiCong()
  const [loc, setLoc] = useState('')
  const [dayModal, setDayModal] = useState(null)   // { item }
  const [leave, setLeave] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const { data, isLoading } = useQuery({ queryKey: ['viec-can-xu-ly'], queryFn: layViecCanXuLy, refetchInterval: 60_000 })
  useGateEvents((ev) => { if (ev.loai === 'luot' && ev.ghi_cong) lamMoi() })

  const ds = data?.ds ?? []
  const rows = loc ? ds.filter((x) => x.loai === loc) : ds
  const dem = (k) => ds.filter((x) => x.loai === k).length
  const worker = (x) => ({ id: x.worker_id, ma: x.ma, ten: x.ho_ten })
  const moNgay = (x) => navigate(`/bang-cong?ngay=${x.ngay}&cn=${x.worker_id}`)

  return (
    <div className="page">
      <PageHead title="Việc cần xử lý" sub={data ? `${ds.length} việc` : ' '} />
      <div className="d-flex align-items-center gap-2 flex-wrap mb-3">
        <Segmented ariaLabel="Lọc theo loại" value={loc} onChange={setLoc} options={[
          { value: '', label: `Tất cả (${ds.length})` },
          ...LOC.map((k) => ({ value: k, label: `${VIEC[k][0]} (${dem(k)})` })),
        ]} />
      </div>
      <Card flush>
        <div className="table-wrap">
          <table className="sg-table">
            <thead><tr><th>Loại</th><th>Công nhân</th><th>Ngày</th><th>Nội dung</th><th className="right shrink">Xử lý</th></tr></thead>
            <tbody>
              {isLoading ? <SkeletonRows cols={5} rows={4} />
                : !rows.length ? (
                  <EmptyRow colSpan={5} icon={CircleCheckBig} title="Không có việc nào cần xử lý"
                    text="Ngày thiếu giờ ra và ngày đi muộn / về sớm chưa có phép sẽ hiện ở đây." />
                ) : rows.map((x) => {
                  const [ten, tone] = VIEC[x.loai] ?? [x.ten_loai, 'neutral']
                  return (
                    <tr key={`${x.loai}-${x.attendance_id}`}>
                      <td className="nowrap"><Pill tone={tone}>{ten}</Pill></td>
                      <td><Person name={x.ho_ten} code={x.ma} workerId={x.worker_id} to={`/cong-nhan/${x.worker_id}`} /></td>
                      <td className="nowrap num">{thuNgay(x.ngay)}</td>
                      <td>{x.mo_ta}</td>
                      <td className="right shrink">
                        <div className="d-inline-flex gap-2 align-items-center justify-content-end">
                          {x.loai === 'thieu_gio_ra' ? (
                            <Button size="sm" onClick={() => setDayModal(x)}><DoorClosed size={15} />Nhập giờ ra</Button>
                          ) : (
                            <>
                              <Button size="sm" onClick={() => setLeave(x)}><ClipboardList size={15} />Thêm phép</Button>
                              <Button size="sm" variant="secondary" onClick={() => setConfirm(x)}><ShieldX size={15} />Xác nhận không phép</Button>
                            </>
                          )}
                          <Button size="sm" variant="secondary" className="btn-icon" title="Mở ngày công" aria-label="Mở ngày công"
                            onClick={() => moNgay(x)}><CalendarSearch size={15} /></Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
        <div className="sg-card__foot"><span>Đi muộn / về sớm chưa có phép chỉ hiện khi quá {cfg.nguongGiaiTrinh} phút; về sớm chỉ xét khi ca của ngày đó đã kết thúc.</span></div>
      </Card>

      {dayModal && (
        <ManualAttendanceModal worker={worker(dayModal)} ngay={dayModal.ngay} focusSegmentId={dayModal.segment_id}
          onClose={() => setDayModal(null)} />
      )}
      {leave && (
        <LeaveModal worker={worker(leave)} onClose={() => setLeave(null)} defaults={leave.loai === 'di_muon_khong_phep'
          ? { loai: 'di_muon', ngay: leave.ngay, den_gio: leave.gio_vao ?? '' }
          : { loai: 've_som', ngay: leave.ngay, tu_gio: leave.gio_ra ?? '' }} />
      )}
      {confirm && (
        <ReasonModal title={`Xác nhận ${confirm.ho_ten} không có phép?`} required={false} confirmLabel="Xác nhận không phép"
          message={<>{confirm.mo_ta} ({thuNgay(confirm.ngay)}). Ngày này rời khỏi danh sách Việc cần xử lý, vẫn tính là đi muộn / về sớm không phép và ghi vào nhật ký.</>}
          placeholder="vd Đã nhắc nhở, không có giấy phép"
          onConfirm={async (lyDo) => { await xacNhanKhongPhep(confirm.attendance_id, lyDo); toast.success('Đã xác nhận không phép'); lamMoi() }}
          onClose={() => setConfirm(null)} />
      )}
    </div>
  )
}
