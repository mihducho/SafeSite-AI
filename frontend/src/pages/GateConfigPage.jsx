import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap'
import {
  capNhatCauHinhCong, getUrlAnhHienTai, khoiDongLaiCong, layCauHinhCong, layTrangThaiCong, STREAM_URL,
} from '../api/endpoints.js'
import { LiveStream } from '../components/common/ui.jsx'
import { toast } from '../lib/toast.js'

/**
 * Cấu hình cổng: nguồn camera (webcam, URL điện thoại DroidCam, file video), góc xoay, khởi động lại, xem trước,
 * vẽ vùng kiểm tra. Mọi hình lấy qua backend (/stream/gate, /api/cong/anh-hien-tai), KHÔNG mở thẳng URL camera
 * (DroidCam chỉ cho 1 kết nối). Vùng lưu dạng tỉ lệ 0–1 trên hình ĐÃ xoay.
 */
const ROT = [0, 90, 180, 270]
const FULL = [[0, 0], [1, 0], [1, 1], [0, 1]]
const fmtPts = (pts) => (pts ?? []).map(([x, y]) => `${x},${y}`).join(' ')

function gateText(st) {
  if (!st) return 'Đang tải…'
  if (st.mat_camera) return 'Mất kết nối camera, đang thử lại'
  if (st.trang_thai === 'dang_chay' && !st.loi) return `Đang chạy${st.pha === 'KIEM_TRA' ? ' · đang kiểm tra' : ''}`
  if (st.trang_thai === 'dang_khoi_dong') return 'Đang khởi động'
  if (st.trang_thai === 'tat') return 'Đang tắt'
  return `Lỗi${st.loi ? ` – ${st.loi}` : ''}`
}

function ZoneEditor({ gate, onSaved }) {
  const imgRef = useRef(null)
  const [snap, setSnap] = useState(getUrlAnhHienTai())
  const [snapError, setSnapError] = useState(false)
  const [points, setPoints] = useState([])
  const save = useMutation({
    mutationFn: (zone) => capNhatCauHinhCong({ zone }),
    onSuccess: (r) => { toast.success('Đã lưu vùng kiểm tra, cổng đang khởi động lại'); setPoints([]); onSaved(r) },
  })

  const refresh = () => { setSnapError(false); setSnap(getUrlAnhHienTai()) }
  const onClick = (e) => {
    const im = imgRef.current
    if (!im?.naturalWidth) return
    const r = im.getBoundingClientRect()
    if (e.clientX < r.left || e.clientY < r.top || e.clientX > r.right || e.clientY > r.bottom) return
    const round = (v) => Math.round(Math.min(1, Math.max(0, v)) * 10000) / 10000
    setPoints((p) => [...p, [round((e.clientX - r.left) / r.width), round((e.clientY - r.top) / r.height)]])
  }

  return (
    <Card className="h-100">
      <Card.Header>Vùng kiểm tra</Card.Header>
      <Card.Body>
        <p className="small mb-2" style={{ color: 'var(--text-secondary)' }}>
          Bấm lên ảnh để thêm từng đỉnh của vùng (ít nhất 3 điểm), bao <b>chỗ người đứng</b>: hệ thống xét <b>điểm chân</b> của
          người có nằm trong vùng không. Người đứng trong vùng phải thấy từ đầu đến chân.
        </p>
        <div className="sg-zone" onClick={onClick}>
          <img ref={imgRef} src={snap} alt="Khung hình hiện tại" onError={() => setSnapError(true)} onLoad={() => setSnapError(false)} />
          <svg viewBox="0 0 1 1" preserveAspectRatio="none">
            <polygon className="sg-zone__saved" points={fmtPts(gate?.zone)} />
            <polygon className="sg-zone__new" points={fmtPts(points)} />
            {points.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="0.012" className="sg-zone__dot" />)}
          </svg>
        </div>
        {snapError && <div className="small text-danger mt-1">Chưa có hình từ camera cổng (xem Trạng thái), bấm "Lấy ảnh mới" sau khi camera chạy.</div>}
        <div className="d-flex flex-wrap gap-2 mt-2">
          <Button size="sm" variant="outline-secondary" onClick={refresh}>📷 Lấy ảnh mới</Button>
          <Button size="sm" variant="outline-secondary" onClick={() => setPoints((p) => p.slice(0, -1))} disabled={!points.length}>↶ Xoá điểm cuối</Button>
          <Button size="sm" variant="outline-secondary" onClick={() => setPoints([])} disabled={!points.length}>Xoá hết</Button>
          <Button size="sm" variant="outline-secondary" onClick={() => setPoints(FULL)}>Cả khung</Button>
          <Button size="sm" variant="success" className="ms-auto" disabled={points.length < 3 || save.isPending}
            onClick={() => save.mutate(points)}>
            {save.isPending ? <Spinner size="sm" /> : 'Lưu vùng'}
          </Button>
        </div>
        <div className="small mt-2" style={{ color: 'var(--text-secondary)' }}>
          {points.length
            ? `Vùng mới: ${points.length} điểm${points.length < 3 ? ' (cần ít nhất 3)' : ''}. Bấm "Lưu vùng" để áp dụng.`
            : <><span style={{ color: '#ffc800' }}>■</span> vùng đang dùng ({gate?.zone?.length ?? 0} điểm). Bấm lên ảnh để vẽ vùng mới.</>}
        </div>
      </Card.Body>
    </Card>
  )
}

export default function GateConfigPage() {
  const qc = useQueryClient()
  const { data: gate, isLoading } = useQuery({ queryKey: ['cong'], queryFn: layCauHinhCong })
  const { data: st } = useQuery({ queryKey: ['cong-trang-thai'], queryFn: layTrangThaiCong, refetchInterval: 2000, meta: { silent: true } })
  const [form, setForm] = useState({ name: '', camera_source: '', rotate: 0 })
  const [error, setError] = useState('')
  const [liveKey, setLiveKey] = useState(0)

  useEffect(() => {
    if (gate) setForm({ name: gate.name ?? '', camera_source: gate.camera_source ?? '', rotate: gate.rotate ?? 0 })
  }, [gate])

  const afterRestart = (r) => {
    if (r) qc.setQueryData(['cong'], (old) => ({ ...old, ...r }))
    qc.invalidateQueries({ queryKey: ['cong'] })
    setTimeout(() => setLiveKey((k) => k + 1), 2500)   // chờ cổng mở lại camera rồi tải lại hình xem trước
  }

  const save = useMutation({
    mutationFn: (body) => capNhatCauHinhCong(body),
    meta: { silent: true },
    onSuccess: (r) => {
      setError('')
      if (r.ghi_chu) toast.warning(`Đã lưu, đang khởi động lại cổng – ${r.ghi_chu}`)
      else toast.success('Đã lưu, đang khởi động lại cổng')
      afterRestart(r)
    },
    onError: (err) => setError(err.message),
  })
  const restart = useMutation({
    mutationFn: khoiDongLaiCong,
    onSuccess: () => { toast.success('Đang khởi động lại cổng'); afterRestart() },
  })

  const submit = (e) => {
    e.preventDefault()
    save.mutate({ name: form.name.trim() || null, camera_source: form.camera_source.trim() || null, rotate: Number(form.rotate) })
  }
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const statusRows = [
    ['Trạng thái', gateText(st)],
    ['Nguồn đang chạy', st?.nguon ?? '—'],
    ['Góc xoay', st?.xoay != null ? `${st.xoay}°` : '—'],
    ['Độ phân giải (sau xoay)', st?.do_phan_giai ? st.do_phan_giai.replace('x', ' × ') : '—'],
    ['Số khung/giây nhận được', st?.khung_giay ?? '—'],
    ['Số lượt từ lúc khởi động', st?.so_luot ?? 0],
  ]

  return (
    <div className="sg-page">
      <div className="section-header"><h1 className="section-title">Cấu hình cổng</h1></div>
      {gate?.ghi_de_boi_env && (
        <Alert variant="warning" className="py-2">
          Nguồn hình đang bị ghi đè bởi <code>GATE_SOURCE</code> trong file <code>.env</code> ({gate.nguon_env}). Xoá dòng đó
          trong <code>.env</code> rồi khởi động lại ứng dụng nếu muốn dùng nguồn ở đây.
        </Alert>
      )}
      {isLoading ? <div className="text-center py-5"><Spinner animation="border" /></div> : (
        <Row className="g-3">
          <Col xl={4}>
            <Card className="mb-3">
              <Card.Header>Camera cổng</Card.Header>
              <Form onSubmit={submit}>
                <Card.Body>
                  <Form.Group className="mb-3">
                    <Form.Label htmlFor="g-name">Tên cổng</Form.Label>
                    <Form.Control id="g-name" maxLength={50} value={form.name} onChange={set('name')} />
                  </Form.Group>
                  <Form.Group className="mb-3">
                    <Form.Label htmlFor="g-source">Nguồn hình</Form.Label>
                    <Form.Control id="g-source" maxLength={500} value={form.camera_source} onChange={set('camera_source')}
                      placeholder="0 hoặc http://IP:4747/video/force/1280x720" />
                    <Form.Text>Số webcam (0), URL camera điện thoại (DroidCam), hoặc đường dẫn file video (demo dự phòng, tự lặp lại).
                      DroidCam chỉ cho <b>một</b> kết nối: đừng mở URL này ở trình duyệt hay chương trình khác khi ứng dụng đang chạy.</Form.Text>
                  </Form.Group>
                  <Form.Group>
                    <Form.Label htmlFor="g-rotate">Xoay hình (theo chiều kim đồng hồ)</Form.Label>
                    <Form.Select id="g-rotate" value={form.rotate} onChange={set('rotate')}>
                      {ROT.map((r) => <option key={r} value={r}>{r}°{r === 0 ? ' (giữ nguyên)' : ''}</option>)}
                    </Form.Select>
                    <Form.Text>Điện thoại kẹp dọc mà hình nhận về nằm ngang: chọn 90°, nếu người bị lộn ngược thì chọn 270°.
                      Đổi góc xoay thì vùng kiểm tra đặt lại thành cả khung, cần vẽ lại.</Form.Text>
                  </Form.Group>
                  {error && <Alert variant="danger" className="mt-3 mb-0 py-2">{error}</Alert>}
                </Card.Body>
                <Card.Footer className="d-flex gap-2 flex-wrap">
                  <Button type="submit" disabled={save.isPending}>{save.isPending ? <Spinner size="sm" /> : 'Lưu và khởi động lại cổng'}</Button>
                  <Button variant="secondary" onClick={() => restart.mutate()} disabled={restart.isPending}>
                    {restart.isPending ? <Spinner size="sm" /> : '⟳ Khởi động lại'}
                  </Button>
                </Card.Footer>
              </Form>
            </Card>
            <Card>
              <Card.Header>Trạng thái</Card.Header>
              <Table size="sm" className="mb-0 sg-table">
                <tbody>{statusRows.map(([k, v]) => <tr key={k}><th className="text-nowrap">{k}</th><td>{v}</td></tr>)}</tbody>
              </Table>
            </Card>
          </Col>
          <Col xl={4}>
            <Card className="h-100">
              <Card.Header>Xem trực tiếp (sau khi xoay)</Card.Header>
              <Card.Body className="text-center">
                <LiveStream key={liveKey} className="sg-preview-portrait" src={`${STREAM_URL}?t=${liveKey}`} alt="Hình trực tiếp camera cổng" />
              </Card.Body>
            </Card>
          </Col>
          <Col xl={4}>
            <ZoneEditor gate={gate} onSaved={afterRestart} />
          </Col>
        </Row>
      )}
    </div>
  )
}
