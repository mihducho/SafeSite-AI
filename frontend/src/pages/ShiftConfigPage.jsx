import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Spinner } from 'react-bootstrap'
import { CalendarOff, CircleAlert, Clock, Coffee, Info, Repeat, ShieldCheck } from 'lucide-react'
import { capNhatCaLam, layCaLam } from '../api/endpoints.js'
import { Card, PageHead, Skeleton, TimeInput } from '../components/common/ui.jsx'
import { hhmm } from '../lib/format.js'
import { THU_TUAN } from '../lib/labels.js'
import { toast } from '../lib/toast.js'

const toForm = (ca) => ({
  name: ca?.name ?? '', start_time: ca?.start_time ?? '', end_time: ca?.end_time ?? '', break_start: ca?.break_start ?? '',
  break_minutes: ca?.break_minutes ?? 0, grace_minutes: ca?.grace_minutes ?? 0, early_checkin_minutes: ca?.early_checkin_minutes ?? 0,
  phut_chong_trung: ca?.phut_chong_trung ?? 10, ngay_nghi_tuan: ca?.ngay_nghi_tuan ?? ['chu_nhat'],
})

/** "07:30" -> 450 phút (sai dạng -> null), dùng cho thanh thời gian minh hoạ */
function toMin(v) {
  try { const s = hhmm(v, ''); if (!s) return null; const [h, m] = s.split(':').map(Number); return h * 60 + m } catch { return null }
}
const fmt = (m) => `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

/** Thanh thời gian 0–24 giờ: cho vào sớm, giờ làm (kèm ân hạn), nghỉ giữa ca */
function ShiftTimeline({ form }) {
  const s = toMin(form.start_time)
  const e = toMin(form.end_time)
  const b = toMin(form.break_start)
  if (s == null || e == null || e <= s) return <div className="small muted">Nhập giờ bắt đầu và kết thúc hợp lệ để xem minh hoạ.</div>
  const pct = (m) => `${(Math.max(0, Math.min(1440, m)) / 1440) * 100}%`
  const width = (a, z) => `${((Math.max(0, Math.min(1440, z)) - Math.max(0, Math.min(1440, a))) / 1440) * 100}%`
  const early = Number(form.early_checkin_minutes) || 0
  const grace = Number(form.grace_minutes) || 0
  const brk = Number(form.break_minutes) || 0
  return (
    <div>
      <div className="d-flex gap-4 flex-wrap mb-3" style={{ fontSize: 13 }}>
        <span>Giờ làm <b className="num mono-meta">{fmt(s)} – {fmt(e)}</b></span>
        {b != null && brk > 0 && <span>Nghỉ giữa ca <b className="num mono-meta">{fmt(b)} – {fmt(b + brk)}</b></span>}
        {early > 0 && <span>Cho vào từ <b className="num mono-meta">{fmt(Math.max(0, s - early))}</b></span>}
        {grace > 0 && <span>Tính đi muộn sau <b className="num mono-meta">{fmt(s + grace)}</b></span>}
      </div>
      <div className="timeline" role="img" aria-label={`Ca ${fmt(s)} đến ${fmt(e)}`}>
        {early > 0 && <span className="timeline__seg early" style={{ left: pct(s - early), width: width(s - early, s) }} title={`Cho vào sớm từ ${fmt(s - early)}`} />}
        <span className="timeline__seg work" style={{ left: pct(s), width: width(s, e) }} title={`Giờ làm ${fmt(s)} – ${fmt(e)}`} />
        {grace > 0 && <span className="timeline__seg grace" style={{ left: pct(s), width: width(s, s + grace) }} title={`Ân hạn đi muộn tới ${fmt(s + grace)}`} />}
        {b != null && brk > 0 && <span className="timeline__seg break" style={{ left: pct(b), width: width(b, b + brk) }} title={`Nghỉ ${fmt(b)} – ${fmt(b + brk)}`} />}
      </div>
      <div className="timeline__ticks">{[0, 3, 6, 9, 12, 15, 18, 21, 24].map((h) => <span key={h} style={{ left: `${(h / 24) * 100}%` }}>{h}h</span>)}</div>
      <div className="legend mt-3">
        <span><i style={{ background: '#D4D4D8' }} />Giờ làm</span>
        <span><i style={{ background: '#FDE68A' }} />Ân hạn đi muộn ({grace} phút)</span>
        <span><i style={{ background: '#FFFFFF', border: '1px solid #D4D4D8' }} />Nghỉ giữa ca ({brk} phút)</span>
        <span><i style={{ background: '#F4F4F5', border: '1px dashed #A1A1AA' }} />Cho vào sớm ({early} phút)</span>
      </div>
    </div>
  )
}

/** Ca làm (bản demo có 1 ca mặc định). Lưu xong, bảng công HÔM NAY được tính lại theo ca mới. */
export default function ShiftConfigPage() {
  const qc = useQueryClient()
  const { data: ca, isLoading } = useQuery({ queryKey: ['ca-lam'], queryFn: layCaLam })
  const [form, setForm] = useState(toForm(null))
  const [error, setError] = useState('')
  useEffect(() => { if (ca) setForm(toForm(ca)) }, [ca])

  const save = useMutation({
    mutationFn: capNhatCaLam,
    meta: { silent: true },
    onSuccess: (r) => {
      setError('')
      toast.success(`Đã lưu ca làm${r.so_dong_tinh_lai ? `, tính lại ${r.so_dong_tinh_lai} dòng bảng công hôm nay` : ''}`)
      qc.setQueryData(['ca-lam'], r)
      for (const key of ['bang-cong-ngay', 'bang-cong-thang', 'bang-cong-cn', 'ngay-cong', 'viec-can-xu-ly']) qc.invalidateQueries({ queryKey: [key] })
    },
    onError: (err) => setError(err.message),
  })

  const submit = (e) => {
    e.preventDefault()
    try {
      const num = (v) => (String(v).trim() === '' ? null : Number(v))
      save.mutate({
        name: form.name.trim() || null,
        start_time: hhmm(form.start_time, 'Giờ bắt đầu'),
        end_time: hhmm(form.end_time, 'Giờ kết thúc'),
        break_start: hhmm(form.break_start, 'Giờ bắt đầu nghỉ'),
        break_minutes: num(form.break_minutes),
        grace_minutes: num(form.grace_minutes),
        early_checkin_minutes: num(form.early_checkin_minutes),
        phut_chong_trung: num(form.phut_chong_trung),
        ngay_nghi_tuan: form.ngay_nghi_tuan,
      })
    } catch (err) { setError(err.message) }
  }
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: typeof v === 'string' ? v : v.target.value }))
  const changed = ca && JSON.stringify(toForm(ca)) !== JSON.stringify(form)
  const toggleThu = (k) => setForm((f) => ({
    ...f, ngay_nghi_tuan: f.ngay_nghi_tuan.includes(k) ? f.ngay_nghi_tuan.filter((x) => x !== k) : [...f.ngay_nghi_tuan, k],
  }))

  return (
    <div className="page" style={{ maxWidth: 1100 }}>
      <PageHead title="Ca làm" sub="Bản demo có một ca mặc định. Lưu xong, bảng công hôm nay được tính lại theo ca mới; ngày cũ giữ giờ ca đã áp dụng.">
        <Button variant="secondary" onClick={() => { setForm(toForm(ca)); setError('') }} disabled={!changed || save.isPending}>Hoàn tác</Button>
        <Button type="submit" form="shift-form" disabled={save.isPending || !ca}>{save.isPending && <Spinner size="sm" />}Lưu ca làm</Button>
      </PageHead>
      {isLoading ? <Card><Skeleton height={260} /></Card> : (
        <div className="stack">
          <Card title="Minh hoạ ca trong ngày">
            <ShiftTimeline form={form} />
          </Card>
          <Card>
            <Form id="shift-form" onSubmit={submit} noValidate>
              <Form.Group className="mb-3" style={{ maxWidth: 420 }}>
                <Form.Label htmlFor="s-name">Tên ca</Form.Label>
                <Form.Control id="s-name" maxLength={50} value={form.name} onChange={set('name')} />
              </Form.Group>
              <div className="row g-3">
                <div className="col-lg-4">
                  <div className="form-group-title"><Clock size={16} strokeWidth={1.5} />Giờ làm</div>
                  <div className="row g-2">
                    <div className="col-6"><Form.Label htmlFor="s-start">Giờ bắt đầu</Form.Label><TimeInput id="s-start" value={form.start_time} onChange={set('start_time')} /></div>
                    <div className="col-6"><Form.Label htmlFor="s-end">Giờ kết thúc</Form.Label><TimeInput id="s-end" value={form.end_time} onChange={set('end_time')} /></div>
                  </div>
                </div>
                <div className="col-lg-4">
                  <div className="form-group-title"><Coffee size={16} strokeWidth={1.5} />Nghỉ giữa ca</div>
                  <div className="row g-2">
                    <div className="col-6"><Form.Label htmlFor="s-break-start">Giờ bắt đầu nghỉ</Form.Label><TimeInput id="s-break-start" value={form.break_start} onChange={set('break_start')} /></div>
                    <div className="col-6"><Form.Label htmlFor="s-break">Số phút nghỉ</Form.Label>
                      <Form.Control id="s-break" type="number" min={0} max={240} value={form.break_minutes} onChange={set('break_minutes')} /></div>
                  </div>
                </div>
                <div className="col-lg-4">
                  <div className="form-group-title"><ShieldCheck size={16} strokeWidth={1.5} />Quy định</div>
                  <div className="row g-2">
                    <div className="col-6"><Form.Label htmlFor="s-grace">Ân hạn đi muộn (phút)</Form.Label>
                      <Form.Control id="s-grace" type="number" min={0} max={120} value={form.grace_minutes} onChange={set('grace_minutes')} /></div>
                    <div className="col-6"><Form.Label htmlFor="s-early">Cho vào sớm (phút)</Form.Label>
                      <Form.Control id="s-early" type="number" min={0} max={240} value={form.early_checkin_minutes} onChange={set('early_checkin_minutes')} /></div>
                  </div>
                </div>
              </div>
              <div className="row g-3 mt-1">
                <div className="col-lg-4">
                  <div className="form-group-title"><Repeat size={16} strokeWidth={1.5} />Chống quét trùng</div>
                  <Form.Label htmlFor="s-dup">Chống quét trùng (phút)</Form.Label>
                  <Form.Control id="s-dup" type="number" min={1} max={120} value={form.phut_chong_trung} onChange={set('phut_chong_trung')} style={{ maxWidth: 160 }} />
                  <div className="small muted mt-1">Hai lần ghi công (vào / ra) của một người cách nhau ít hơn số phút này thì bỏ qua lần sau. Thường đặt 10; khi demo đặt 1.</div>
                </div>
                <div className="col-lg-8">
                  <div className="form-group-title"><CalendarOff size={16} strokeWidth={1.5} />Ngày nghỉ hằng tuần</div>
                  <div className="choice-row" role="group" aria-label="Ngày nghỉ hằng tuần">
                    {THU_TUAN.map(([k, ngan, ten]) => (
                      <button key={k} type="button" title={ten} aria-pressed={form.ngay_nghi_tuan.includes(k)}
                        className={`choice${form.ngay_nghi_tuan.includes(k) ? ' active' : ''}`} onClick={() => toggleThu(k)}>{ngan}</button>
                    ))}
                  </div>
                  <div className="small muted mt-1">Ngày nghỉ không có phiên thì là "Nghỉ tuần", không tính vắng. Đi làm vào ngày nghỉ vẫn được ghi công, có đánh dấu.</div>
                </div>
              </div>
              {error && <div className="note bad mt-3"><CircleAlert size={17} strokeWidth={1.5} />{error}</div>}
              <div className="note info mt-3">
                <Info size={17} strokeWidth={1.5} />
                <div>
                  Giờ nhập dạng 24 giờ HH:MM, ví dụ 07:00. Vào sau giờ bắt đầu + ân hạn (tính cả giây) là đi muộn, số phút tính từ giờ
                  bắt đầu ca. Chỉ ghi giờ vào trong khoảng từ (giờ bắt đầu − cho vào sớm) tới giờ kết thúc; ngoài khoảng đó màn hình cổng
                  báo "chưa đến giờ" / "đã hết giờ vào ca". Số giờ làm cộng các phiên vào – ra, trừ phần trùng giờ nghỉ.
                </div>
              </div>
            </Form>
          </Card>
        </div>
      )}
    </div>
  )
}
