import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap'
import { capNhatCaLam, layCaLam } from '../api/endpoints.js'
import { TimeInput } from '../components/common/ui.jsx'
import { hhmm } from '../lib/format.js'
import { toast } from '../lib/toast.js'

const toForm = (ca) => ({
  name: ca?.name ?? '', start_time: ca?.start_time ?? '', end_time: ca?.end_time ?? '', break_start: ca?.break_start ?? '',
  break_minutes: ca?.break_minutes ?? 0, grace_minutes: ca?.grace_minutes ?? 0, early_checkin_minutes: ca?.early_checkin_minutes ?? 0,
})

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
      qc.invalidateQueries({ queryKey: ['bang-cong-ngay'] })
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
        break_start: hhmm(form.break_start, 'Giờ bắt đầu nghỉ trưa'),
        break_minutes: num(form.break_minutes),
        grace_minutes: num(form.grace_minutes),
        early_checkin_minutes: num(form.early_checkin_minutes),
      })
    } catch (err) { setError(err.message) }
  }
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: typeof v === 'string' ? v : v.target.value }))

  return (
    <div className="sg-page" style={{ maxWidth: 820 }}>
      <div className="section-header"><h1 className="section-title mb-0">Ca làm</h1></div>
      {isLoading ? <div className="text-center py-5"><Spinner animation="border" /></div> : (
        <Card>
          <Card.Header>Ca mặc định (bản demo có 1 ca)</Card.Header>
          <Form onSubmit={submit} noValidate>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label htmlFor="s-name">Tên ca</Form.Label>
                <Form.Control id="s-name" maxLength={50} value={form.name} onChange={set('name')} />
              </Form.Group>
              <Row className="g-3">
                <Col sm={6}><Form.Label htmlFor="s-start">Giờ bắt đầu</Form.Label><TimeInput id="s-start" value={form.start_time} onChange={set('start_time')} /></Col>
                <Col sm={6}><Form.Label htmlFor="s-end">Giờ kết thúc</Form.Label><TimeInput id="s-end" value={form.end_time} onChange={set('end_time')} /></Col>
                <Col sm={6}><Form.Label htmlFor="s-break-start">Giờ bắt đầu nghỉ trưa</Form.Label><TimeInput id="s-break-start" value={form.break_start} onChange={set('break_start')} /></Col>
                <Col sm={6}><Form.Label htmlFor="s-break">Số phút nghỉ</Form.Label>
                  <Form.Control id="s-break" type="number" min={0} max={240} value={form.break_minutes} onChange={set('break_minutes')} /></Col>
                <Col sm={6}><Form.Label htmlFor="s-grace">Ân hạn đi muộn (phút)</Form.Label>
                  <Form.Control id="s-grace" type="number" min={0} max={120} value={form.grace_minutes} onChange={set('grace_minutes')} /></Col>
                <Col sm={6}><Form.Label htmlFor="s-early">Cho vào sớm (phút)</Form.Label>
                  <Form.Control id="s-early" type="number" min={0} max={240} value={form.early_checkin_minutes} onChange={set('early_checkin_minutes')} /></Col>
              </Row>
              <ul className="small mt-3 mb-0" style={{ color: 'var(--text-secondary)', paddingLeft: '1.1rem' }}>
                <li>Giờ nhập dạng 24 giờ HH:MM, ví dụ 07:00, 17:00.</li>
                <li>Đi muộn quá số phút ân hạn thì tính toàn bộ số phút từ giờ bắt đầu ca.</li>
                <li>Số giờ làm chỉ trừ phần giờ nghỉ trưa nằm trong khoảng từ giờ vào đến giờ ra.</li>
                <li>Vào trước giờ bắt đầu quá số phút cho vào sớm, hoặc sau giờ kết thúc: trạng thái "ngoài ca".</li>
                <li>Lưu xong, bảng công <b>hôm nay</b> được tính lại theo ca mới; các ngày trước giữ nguyên.</li>
              </ul>
              {error && <Alert variant="danger" className="mt-3 mb-0 py-2">{error}</Alert>}
            </Card.Body>
            <Card.Footer className="d-flex gap-2">
              <Button type="submit" disabled={save.isPending}>{save.isPending ? <Spinner size="sm" /> : 'Lưu ca làm'}</Button>
              <Button variant="secondary" onClick={() => { setForm(toForm(ca)); setError('') }} disabled={save.isPending}>Hoàn tác</Button>
            </Card.Footer>
          </Form>
        </Card>
      )}
    </div>
  )
}
