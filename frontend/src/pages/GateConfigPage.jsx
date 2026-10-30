import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Spinner } from 'react-bootstrap'
import { Camera, CircleAlert, Eraser, HardHat, Maximize2, RotateCw, Save, Shirt, Undo2 } from 'lucide-react'
import {
  capNhatCauHinhCong, getUrlAnhHienTai, khoiDongLaiCong, layCauHinhCong, layTrangThaiCong, STREAM_URL,
} from '../api/endpoints.js'
import { Card, LiveStream, PageHead, Pill, Segmented, Skeleton } from '../components/common/ui.jsx'
import { useWsState } from '../lib/events.js'
import { DO_BAO_HO_TEN, trangThaiCong } from '../lib/labels.js'
import { toast } from '../lib/toast.js'

/**
 * Cấu hình cổng: nguồn camera (webcam, URL điện thoại DroidCam, file video), góc xoay, khởi động lại, xem trước,
 * vẽ vùng kiểm tra. Mọi hình lấy qua backend (/stream/gate, /api/cong/anh-hien-tai), KHÔNG mở thẳng URL camera
 * (DroidCam chỉ cho 1 kết nối). Vùng lưu dạng tỉ lệ 0–1 trên hình ĐÃ xoay.
 */
const ROT = [0, 90, 180, 270]
const FULL = [[0, 0], [1, 0], [1, 1], [0, 1]]
const fmtPts = (pts) => (pts ?? []).map(([x, y]) => `${x},${y}`).join(' ')
const PPE_ICON = { hardhat: HardHat, vest: Shirt }

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
    <Card title="Vùng kiểm tra" sub="chỗ người đứng trước camera">
      <div className="d-flex gap-4 flex-wrap">
        <div>
          <div className="zone-edit" onClick={onClick}>
            <img ref={imgRef} src={snap} alt="Khung hình hiện tại" onError={() => setSnapError(true)} onLoad={() => setSnapError(false)} />
            <svg viewBox="0 0 1 1" preserveAspectRatio="none">
              <polygon className="zone-saved" points={fmtPts(gate?.zone)} />
              <polygon className="zone-new" points={fmtPts(points)} />
              {points.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="0.012" className="zone-dot" />)}
            </svg>
          </div>
        </div>
        <div style={{ flex: "1 1 260px", minWidth: 260, maxWidth: 520 }}>
          <p className="muted" style={{ fontSize: 14 }}>
            Bấm lên ảnh để thêm từng đỉnh của vùng (ít nhất 3 điểm), bao quanh <b style={{ color: 'var(--text)' }}>chỗ người đứng</b>.
            Hệ thống xét <b style={{ color: 'var(--text)' }}>điểm chân</b> của người có nằm trong vùng không, nên người đứng trong vùng phải
            thấy được từ đầu đến chân.
          </p>
          <div className="legend mb-3">
            <span><i style={{ background: '#F59E0B' }} />Vùng đang dùng ({gate?.zone?.length ?? 0} điểm)</span>
            <span><i style={{ background: '#2563EB' }} />Vùng mới ({points.length} điểm)</span>
          </div>
          <div className="d-flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" onClick={refresh}><Camera size={16} />Lấy ảnh mới</Button>
            <Button variant="secondary" size="sm" onClick={() => setPoints((p) => p.slice(0, -1))} disabled={!points.length}><Undo2 size={16} />Xoá điểm cuối</Button>
            <Button variant="secondary" size="sm" onClick={() => setPoints([])} disabled={!points.length}><Eraser size={16} />Xoá hết</Button>
            <Button variant="secondary" size="sm" onClick={() => setPoints(FULL)}><Maximize2 size={16} />Cả khung</Button>
          </div>
          <Button variant="success" className="mt-3" disabled={points.length < 3 || save.isPending} onClick={() => save.mutate(points)}>
            {save.isPending ? <Spinner size="sm" /> : <Save size={17} />}Lưu vùng kiểm tra
          </Button>
          {points.length > 0 && points.length < 3 && <div className="small text-warn mt-2">Cần ít nhất 3 điểm.</div>}
          {snapError && <div className="note warn mt-3"><CircleAlert size={18} />Chưa có hình từ camera cổng. Bấm "Lấy ảnh mới" sau khi camera chạy.</div>}
        </div>
      </div>
    </Card>
  )
}

export default function GateConfigPage() {
  const qc = useQueryClient()
  const ws = useWsState()
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
      if (r.ghi_chu) toast.warning(`Đã lưu, đang khởi động lại cổng. ${r.ghi_chu}`)
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
  // trạng thái lấy định kỳ qua API (không phụ thuộc WebSocket); chỉ báo mất máy chủ khi WebSocket cũng mất
  const [, sentence, tone] = trangThaiCong(st ?? null, ws === 'mat' ? 'mat' : st ? 'mo' : 'dang_ket_noi')
  const ppe = gate?.required_ppe

  const statusRows = [
    ['Nguồn đang chạy', st?.nguon],
    ['Góc xoay', st?.xoay != null ? `${st.xoay}°` : ''],
    ['Độ phân giải sau xoay', st?.do_phan_giai ? st.do_phan_giai.replace('x', ' × ') : ''],
    ['Số khung hình mỗi giây', st?.khung_giay != null ? String(st.khung_giay).replace('.', ',') : ''],
    ['Số lượt từ lúc khởi động', st?.so_luot ?? 0],
  ]

  return (
    <div className="page">
      <PageHead title="Cấu hình cổng" sub={gate ? gate.name : ' '} />
      {gate?.ghi_de_boi_env && (
        <div className="note warn mb-3"><CircleAlert size={18} />
          <div>Nguồn hình đang được đặt bằng <code>GATE_SOURCE</code> trong file <code>.env</code> ({gate.nguon_env}). Muốn dùng nguồn ở
            đây thì xoá dòng đó trong <code>.env</code> rồi khởi động lại ứng dụng.</div>
        </div>
      )}
      {isLoading ? <Card><Skeleton height={300} /></Card> : (
        <div className="stack">
          <div className="grid gate-cfg">
            <Card title="Camera cổng">
              <Form id="gate-form" onSubmit={submit}>
                <Form.Group className="mb-3">
                  <Form.Label htmlFor="g-name">Tên cổng</Form.Label>
                  <Form.Control id="g-name" maxLength={50} value={form.name} onChange={set('name')} />
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label htmlFor="g-source">Nguồn camera</Form.Label>
                  <Form.Control id="g-source" maxLength={500} value={form.camera_source} onChange={set('camera_source')}
                    placeholder="0 hoặc http://IP:4747/video/force/1280x720" />
                  <Form.Text>Số webcam (0), địa chỉ camera điện thoại (DroidCam) hoặc đường dẫn file video (demo dự phòng, tự lặp lại).
                    DroidCam chỉ cho một kết nối: không mở địa chỉ này ở trình duyệt hay chương trình khác khi ứng dụng đang chạy.</Form.Text>
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label as="div">Xoay hình (theo chiều kim đồng hồ)</Form.Label>
                  <div><Segmented ariaLabel="Góc xoay" value={Number(form.rotate)} onChange={(v) => setForm((f) => ({ ...f, rotate: v }))}
                    options={ROT.map((r) => ({ value: r, label: `${r}°` }))} /></div>
                  <Form.Text>Điện thoại kẹp dọc mà hình nhận về nằm ngang thì chọn 90°; người bị lộn ngược thì chọn 270°. Đổi góc xoay thì
                    vùng kiểm tra đặt lại thành cả khung, cần vẽ lại.</Form.Text>
                </Form.Group>
                <Form.Group className="mb-4">
                  <Form.Label as="div">Đồ bảo hộ bắt buộc</Form.Label>
                  <div className="d-flex gap-2 flex-wrap">
                    {Array.isArray(ppe) && ppe.length
                      ? ppe.map((k) => <Pill key={k} tone="neutral" icon={PPE_ICON[k] ?? HardHat}>{DO_BAO_HO_TEN[k] ?? k}</Pill>)
                      : <><Pill tone="neutral" icon={HardHat}>Mũ bảo hộ</Pill><Pill tone="neutral" icon={Shirt}>Áo phản quang</Pill></>}
                  </div>
                  <Form.Text>{Array.isArray(ppe) && ppe.length ? 'Theo cấu hình riêng của cổng.' : 'Theo cấu hình chung của hệ thống.'}</Form.Text>
                </Form.Group>
                {error && <div className="note bad mb-3"><CircleAlert size={18} />{error}</div>}
                <div className="d-flex gap-2 flex-wrap">
                  <Button type="submit" disabled={save.isPending}>{save.isPending ? <Spinner size="sm" /> : <Save size={18} />}Lưu và khởi động lại cổng</Button>
                  <Button variant="secondary" onClick={() => restart.mutate()} disabled={restart.isPending}>
                    {restart.isPending ? <Spinner size="sm" /> : <RotateCw size={17} />}Chỉ khởi động lại
                  </Button>
                </div>
              </Form>
            </Card>
            <Card title="Xem trước" sub="hình sau khi xoay">
              <div className="d-flex gap-4 flex-wrap">
                <LiveStream key={liveKey} className="portrait" src={`${STREAM_URL}?t=${liveKey}`} alt="Hình trực tiếp camera cổng"
                  style={{ height: 'min(56vh, 560px)', width: 'calc(min(56vh, 560px) * 0.5625)', margin: 0 }} />
                <div style={{ flex: "1 1 220px", minWidth: 220 }}>
                  <div className={`note ${tone === 'ok' ? 'ok' : tone === 'bad' ? 'bad' : 'warn'} mb-3`} style={{ fontWeight: 600 }}>{sentence}</div>
                  <table className="kv"><tbody>
                    {statusRows.map(([k, v]) => <tr key={k}><th>{k}</th><td className="num" style={{ wordBreak: 'break-all' }}>{v}</td></tr>)}
                  </tbody></table>
                </div>
              </div>
            </Card>
          </div>
          <ZoneEditor gate={gate} onSaved={afterRestart} />
        </div>
      )}
    </div>
  )
}
