import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Card, Col, Form, ProgressBar, Row, Spinner, Tab, Table, Tabs } from 'react-bootstrap'
import { Link, useParams } from 'react-router-dom'
import {
  capNhatCongNhan, chupMauMat, diLamLai, ghiNhanDongY, layBangCongCongNhan, layCaLam, layChiTietCongNhan,
  layDanhSachMauMat, layDanhSachToDoi, layLichSuLuot, layNoiDungDongY, nghiViec, taiLenMauMat,
  xoaMauMat, xoaTatCaMauMat,
} from '../api/endpoints.js'
import CheckDetailModal from '../components/common/CheckDetailModal.jsx'
import ConfirmModal from '../components/common/ConfirmModal.jsx'
import { Avatar, EmptyRow, LiveStream, StatusBadge } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents } from '../lib/events.js'
import { gio, ngay, ngayGio, phut } from '../lib/format.js'
import { CHAM_CONG, CONG_NHAN, HANH_DONG, KET_QUA, thieuText } from '../lib/labels.js'
import { toast } from '../lib/toast.js'

// ─── Thông tin cá nhân ─────────────────────────────────────────────────────────
function ProfileCard({ worker, teams }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})
  const { data: shift } = useQuery({ queryKey: ['ca-lam'], queryFn: layCaLam, staleTime: 60_000 })

  const startEdit = () => {
    setForm({ code: worker.code, full_name: worker.full_name, phone: worker.phone ?? '', trade: worker.trade ?? '', team_id: worker.team_id ?? '' })
    setEditing(true)
  }
  const save = useMutation({
    mutationFn: (body) => capNhatCongNhan(worker.id, body),
    onSuccess: () => {
      toast.success('Đã lưu thông tin')
      qc.invalidateQueries({ queryKey: ['worker', worker.id] })
      qc.invalidateQueries({ queryKey: ['cong-nhan'] })
      setEditing(false)
    },
  })
  const set = (f) => (e) => setForm((p) => ({ ...p, [f]: e.target.value }))
  const submit = (e) => {
    e.preventDefault()
    save.mutate({
      code: form.code.trim(), full_name: form.full_name.trim(), phone: form.phone.trim() || null,
      trade: form.trade.trim() || null, team_id: form.team_id ? Number(form.team_id) : null,
    })
  }

  const field = (label, value) => (
    <div className="mb-2"><div className="sg-sub">{label}</div><div style={{ fontWeight: 500 }}>{value || '—'}</div></div>
  )

  return (
    <Card className="mb-3">
      <Card.Body>
        <div className="d-flex flex-column align-items-center text-center mb-3">
          <Avatar name={worker.full_name} workerId={worker.id} size={96} face />
          <h2 className="h4 mt-2 mb-0">{worker.full_name}</h2>
          <div className="sg-sub">Mã {worker.code}</div>
          <div className="mt-1"><StatusBadge map={CONG_NHAN} value={worker.status} /></div>
        </div>
        {!editing ? (
          <>
            {field('Tổ đội', worker.team_name)}
            {field('Nghề', worker.trade)}
            {field('Điện thoại', worker.phone)}
            {field('Ca làm', shift ? `${shift.name}: ${shift.start_time}–${shift.end_time} (nghỉ trưa ${shift.break_start}, ${shift.break_minutes} phút)` : null)}
            {field('Ngày thêm', worker.created_at ? ngay(worker.created_at) : null)}
            <Button variant="outline-primary" size="sm" className="mt-1" onClick={startEdit}>✏️ Sửa thông tin</Button>
          </>
        ) : (
          <Form onSubmit={submit}>
            <Row className="g-2">
              <Col xs={5}><Form.Label htmlFor="i-code">Mã *</Form.Label>
                <Form.Control id="i-code" maxLength={20} required value={form.code} onChange={set('code')} /></Col>
              <Col xs={7}><Form.Label htmlFor="i-name">Họ tên *</Form.Label>
                <Form.Control id="i-name" maxLength={100} required value={form.full_name} onChange={set('full_name')} /></Col>
              <Col xs={6}><Form.Label htmlFor="i-phone">Điện thoại</Form.Label>
                <Form.Control id="i-phone" maxLength={20} value={form.phone} onChange={set('phone')} /></Col>
              <Col xs={6}><Form.Label htmlFor="i-trade">Nghề</Form.Label>
                <Form.Control id="i-trade" maxLength={50} value={form.trade} onChange={set('trade')} /></Col>
              <Col xs={12}><Form.Label htmlFor="i-team">Tổ đội</Form.Label>
                <Form.Select id="i-team" value={form.team_id} onChange={set('team_id')}>
                  <option value="">(chưa xếp tổ)</option>
                  {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </Form.Select></Col>
            </Row>
            <div className="d-flex gap-2 mt-3">
              <Button type="submit" size="sm" disabled={save.isPending || !form.code?.trim() || !form.full_name?.trim()}>
                {save.isPending ? <Spinner size="sm" /> : 'Lưu'}
              </Button>
              <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>Huỷ</Button>
            </div>
          </Form>
        )}
      </Card.Body>
    </Card>
  )
}

// ─── Đồng ý + mẫu khuôn mặt ────────────────────────────────────────────────────
function FaceCard({ worker }) {
  const qc = useQueryClient()
  const cfg = useWebConfig()
  const fileRef = useRef(null)
  const [agree, setAgree] = useState(false)
  const [captureMsg, setCaptureMsg] = useState(null)   // { ok, text }
  const [uploadMsg, setUploadMsg] = useState([])
  const [confirm, setConfirm] = useState(null)         // { kind: 'one', id } | { kind: 'all' }

  const { data: consentText } = useQuery({ queryKey: ['dong-y-noi-dung'], queryFn: layNoiDungDongY, staleTime: Infinity })
  const { data: mau } = useQuery({ queryKey: ['mau-mat', worker.id], queryFn: () => layDanhSachMauMat(worker.id) })

  const samples = mau?.ds ?? []
  const count = mau?.so_mau ?? 0
  const MIN = mau?.toi_thieu ?? cfg.minSamples
  const MAX = mau?.toi_da ?? cfg.maxSamples
  const active = worker.status === 'dang_lam'
  const consented = !!worker.consent_at
  const canEnroll = active && consented
  const full = count >= MAX

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['mau-mat', worker.id] })
    qc.invalidateQueries({ queryKey: ['worker', worker.id] })
    qc.invalidateQueries({ queryKey: ['cong-nhan'] })
  }

  const consent = useMutation({
    mutationFn: () => ghiNhanDongY(worker.id),
    onSuccess: () => { toast.success('Đã ghi nhận đồng ý đăng ký khuôn mặt'); refresh() },
  })
  const capture = useMutation({
    mutationFn: () => chupMauMat(worker.id),
    meta: { silent: true },                         // lỗi hiện ngay dưới nút chụp (rõ hơn toast)
    onSuccess: (r) => { setCaptureMsg({ ok: true, text: `Đã chụp mẫu (chất lượng ${r.mau.quality.toFixed(2)}). Tổng ${r.so_mau} mẫu.` }); refresh() },
    onError: (err) => setCaptureMsg({ ok: false, text: err.message }),
  })
  const upload = useMutation({
    mutationFn: (files) => {
      const fd = new FormData()
      files.forEach((f) => fd.append('files', f))
      return taiLenMauMat(worker.id, fd)
    },
    meta: { silent: true },
    onSuccess: (r) => { setUploadMsg(r.ket_qua); refresh() },
    onError: (err) => setUploadMsg([{ ten: 'Tải lên', ok: false, ly_do: err.message }]),
  })
  const remove = useMutation({
    mutationFn: (c) => (c.kind === 'all' ? xoaTatCaMauMat(worker.id) : xoaMauMat(c.id)),
    onSuccess: (r, c) => {
      toast.success(c.kind === 'all' ? `Đã xoá ${r.so_mau_da_xoa ?? ''} mẫu khuôn mặt` : 'Đã xoá mẫu')
      setConfirm(null)
      refresh()
    },
    onError: () => setConfirm(null),
  })

  const onFiles = (e) => {
    const files = Array.from(e.target.files)
    e.target.value = ''
    if (files.length) upload.mutate(files)
  }

  return (
    <Card className="mb-3">
      <Card.Header className="d-flex align-items-center gap-2 flex-wrap">
        <span>🧑‍💻 Mẫu khuôn mặt</span>
        <Badge bg={count >= MIN ? 'success' : 'warning'} text={count >= MIN ? undefined : 'dark'}>
          {count}/{MAX} mẫu · {count >= MIN ? 'đủ để nhận diện' : `cần ít nhất ${MIN}`}
        </Badge>
        {count > 0 && (
          <Button variant="outline-danger" size="sm" className="ms-auto" onClick={() => setConfirm({ kind: 'all' })}>🗑 Xoá tất cả</Button>
        )}
      </Card.Header>
      <Card.Body>
        {!active && <Alert variant="secondary" className="py-2">Công nhân đã nghỉ việc: không đăng ký khuôn mặt.</Alert>}

        {/* Đồng ý bắt buộc trước khi lấy dữ liệu sinh trắc học */}
        <div className="p-3 mb-3 rounded" style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-color)' }}>
          <div className="fw-semibold mb-1">Đồng ý đăng ký khuôn mặt</div>
          <p className="small mb-2" style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-line' }}>{consentText?.noi_dung ?? '…'}</p>
          {consented ? (
            <Alert variant="success" className="py-2 mb-0">
              ✔ Đã ghi nhận đồng ý lúc <b>{gio(worker.consent_at)} {ngay(worker.consent_at)}</b>
              {worker.consent_by_name && <> bởi <b>{worker.consent_by_name}</b></>}
            </Alert>
          ) : active && (
            <div className="d-flex align-items-center gap-3 flex-wrap">
              <Form.Check id="consent-check" checked={agree} onChange={(e) => setAgree(e.target.checked)}
                label="Công nhân đã đọc và đồng ý với nội dung trên" />
              <Button variant="success" size="sm" disabled={!agree || consent.isPending} onClick={() => consent.mutate()}>
                {consent.isPending ? <Spinner size="sm" /> : 'Ghi nhận đồng ý'}
              </Button>
            </div>
          )}
        </div>

        {active && !consented && (
          <Alert variant="warning" className="py-2">Cần ghi nhận đồng ý của công nhân trước khi đăng ký khuôn mặt.</Alert>
        )}

        {canEnroll && (
          <Row className="g-3 mb-2">
            <Col md={6}>
              <div className="fw-semibold mb-1">Chụp từ camera cổng</div>
              {!full ? (
                <LiveStream className="sg-preview-portrait" style={{ maxHeight: '52vh', width: '100%' }} alt="Hình trực tiếp camera cổng" />
              ) : <div className="sg-muted small">Đã đủ {MAX} mẫu.</div>}
              <div className="small mt-1" style={{ color: 'var(--text-secondary)' }}>
                Công nhân đứng vào vùng kiểm tra, nhìn thẳng camera; mỗi lần chụp đổi góc mặt một chút (có / không đội mũ).
              </div>
              <Button className="mt-2" disabled={full || capture.isPending} onClick={() => { setCaptureMsg(null); capture.mutate() }}>
                {capture.isPending ? <><Spinner size="sm" className="me-1" />Đang chụp…</> : '📷 Chụp mẫu'}
              </Button>
              {captureMsg && (
                <Alert variant={captureMsg.ok ? 'success' : 'danger'} className="py-2 mt-2 mb-0">{captureMsg.text}</Alert>
              )}
            </Col>
            <Col md={6}>
              <div className="fw-semibold mb-1">Hoặc tải ảnh lên</div>
              <div className="small mb-2" style={{ color: 'var(--text-secondary)' }}>
                Mỗi ảnh đúng 1 khuôn mặt, rõ, đủ sáng (tối đa {cfg.maxUploadMb} MB). Chỉ lưu vector và ảnh mặt 112×112, không lưu ảnh gốc.
              </div>
              <Button variant="outline-primary" disabled={full || upload.isPending} onClick={() => fileRef.current?.click()}>
                {upload.isPending ? <><Spinner size="sm" className="me-1" />Đang tải…</> : '⬆ Chọn ảnh và tải lên'}
              </Button>
              <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={onFiles} />
              {uploadMsg.length > 0 && (
                <ul className="list-unstyled small mt-2 mb-0">
                  {uploadMsg.map((x, i) => (
                    <li key={i} className={x.ok ? 'text-success' : 'text-danger'}>{x.ok ? '✔' : '✕'} {x.ten}{x.ok ? '' : `: ${x.ly_do}`}</li>
                  ))}
                </ul>
              )}
            </Col>
          </Row>
        )}

        <div className="mb-3">
          <ProgressBar now={(count / MAX) * 100} variant={count >= MIN ? 'success' : 'warning'} style={{ height: 8 }} />
        </div>
        {samples.length ? (
          <div className="sg-face-grid">
            {samples.map((s) => (
              <div key={s.id} className="sg-face">
                <img src={s.anh} alt={`Mẫu ${s.id}`} />
                <button type="button" title="Xoá mẫu này" onClick={() => setConfirm({ kind: 'one', id: s.id })}>×</button>
                <small>{s.source === 'camera' ? 'camera' : 'tải lên'} · {s.quality.toFixed(2)}</small>
              </div>
            ))}
          </div>
        ) : <div className="sg-muted">Chưa có mẫu khuôn mặt nào.</div>}
      </Card.Body>

      <ConfirmModal
        show={!!confirm}
        title={confirm?.kind === 'all' ? 'Xoá dữ liệu khuôn mặt' : 'Xoá mẫu khuôn mặt'}
        message={confirm?.kind === 'all'
          ? <>Xoá <b>toàn bộ</b> mẫu khuôn mặt (vector và ảnh mẫu) của <b>{worker.full_name}</b>? Sau khi xoá, công nhân không
              được nhận diện ở cổng cho tới khi đăng ký lại.</>
          : 'Xoá mẫu khuôn mặt này?'}
        variant="danger"
        confirmLabel="Xoá"
        loading={remove.isPending}
        onConfirm={() => remove.mutate(confirm)}
        onCancel={() => setConfirm(null)}
      />
    </Card>
  )
}

// ─── Lịch sử kiểm tra + bảng công của người này ───────────────────────────────
function HistoryTabs({ workerId }) {
  const qc = useQueryClient()
  const [checkId, setCheckId] = useState(null)
  const { data: checks, isLoading: l1 } = useQuery({
    queryKey: ['lich-su-luot', { cong_nhan_id: workerId, so_dong: 10 }],
    queryFn: () => layLichSuLuot({ cong_nhan_id: workerId, so_dong: 10 }),
  })
  const { data: sheet, isLoading: l2 } = useQuery({
    queryKey: ['bang-cong-cn', workerId], queryFn: () => layBangCongCongNhan(workerId, 14),
  })
  useGateEvents((ev) => {
    if (ev.loai === 'luot' && ev.cong_nhan?.id === workerId) {
      qc.invalidateQueries({ queryKey: ['lich-su-luot'] })
      qc.invalidateQueries({ queryKey: ['bang-cong-cn', workerId] })
    }
  })

  return (
    <Card>
      <Card.Body className="pt-2">
        <Tabs defaultActiveKey="luot" className="mb-2">
          <Tab eventKey="luot" title={`Lịch sử kiểm tra${checks ? ` (${checks.tong})` : ''}`}>
            <div className="table-responsive">
              <Table hover size="sm" className="mb-1 sg-table">
                <thead><tr><th>Ảnh</th><th>Thời điểm</th><th>Kết quả</th><th>Điểm</th><th>Hành động</th></tr></thead>
                <tbody>
                  {l1 ? <EmptyRow colSpan={5}><Spinner size="sm" /></EmptyRow>
                    : !checks?.ds.length ? <EmptyRow colSpan={5}>Chưa có lượt nào.</EmptyRow>
                      : checks.ds.map((c) => (
                        <tr key={c.id}>
                          <td>{c.anh ? <img className="sg-thumb" src={c.anh} alt="" loading="lazy" onClick={() => setCheckId(c.id)} />
                            : <span className="sg-thumb sg-thumb--empty" />}</td>
                          <td className="text-nowrap">{ngayGio(c.thoi_diem, true)}</td>
                          <td><StatusBadge map={KET_QUA} value={c.ket_qua} />
                            {c.thieu.length > 0 && <div className="small text-danger">{thieuText(c.thieu)}</div>}</td>
                          <td>{c.diem != null ? c.diem.toFixed(2) : '—'}</td>
                          <td><StatusBadge map={HANH_DONG} value={c.hanh_dong} /></td>
                        </tr>
                      ))}
                </tbody>
              </Table>
            </div>
            <Link to={`/lich-su?cong_nhan_id=${workerId}`} className="small">Xem tất cả lượt của người này →</Link>
          </Tab>
          <Tab eventKey="cong" title="Bảng công 14 ngày">
            <div className="table-responsive">
              <Table hover size="sm" className="mb-0 sg-table">
                <thead><tr><th>Ngày</th><th>Vào</th><th>Ra</th><th>Đi muộn</th><th>Giờ làm</th><th>Trạng thái</th></tr></thead>
                <tbody>
                  {l2 ? <EmptyRow colSpan={6}><Spinner size="sm" /></EmptyRow>
                    : !sheet?.ds.length ? <EmptyRow colSpan={6}>Chưa có ngày công nào.</EmptyRow>
                      : sheet.ds.map((r) => (
                        <tr key={r.ngay}>
                          <td className="text-nowrap">{ngay(r.ngay)}</td>
                          <td>{r.gio_vao ?? '—'}</td>
                          <td>{r.gio_ra ?? (r.thieu_gio_ra ? <span className="text-danger">thiếu</span> : '—')}</td>
                          <td>{r.di_muon_phut ? <span className="text-warning">{r.di_muon_phut} phút</span> : '—'}</td>
                          <td>{r.gio_ra ? phut(r.so_phut_lam) : '—'}</td>
                          <td><StatusBadge map={CHAM_CONG} value={r.trang_thai} /></td>
                        </tr>
                      ))}
                </tbody>
              </Table>
            </div>
          </Tab>
        </Tabs>
      </Card.Body>
      <CheckDetailModal id={checkId} onHide={() => setCheckId(null)} />
    </Card>
  )
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function WorkerDetailPage() {
  const { id } = useParams()
  const workerId = Number(id)
  const qc = useQueryClient()
  const [confirm, setConfirm] = useState(null)   // 'nghi' | 'lai'

  const { data: worker, isLoading, isError } = useQuery({
    queryKey: ['worker', workerId], queryFn: () => layChiTietCongNhan(workerId), enabled: !!workerId,
  })
  const { data: teamData } = useQuery({ queryKey: ['to-doi'], queryFn: layDanhSachToDoi, staleTime: 60_000 })
  useEffect(() => { document.title = worker ? `${worker.code} - ${worker.full_name} · SafeGate` : 'SafeGate' }, [worker])

  const action = useMutation({
    mutationFn: (kind) => (kind === 'nghi' ? nghiViec(workerId) : diLamLai(workerId)),
    onSuccess: (r, kind) => {
      toast.success(kind === 'nghi' ? `Đã cho nghỉ việc, xoá ${r.so_mau_da_xoa ?? 0} mẫu khuôn mặt`
        : 'Đã nhận lại công nhân. Cần ghi nhận đồng ý và đăng ký khuôn mặt lại.')
      setConfirm(null)
      qc.invalidateQueries({ queryKey: ['worker', workerId] })
      qc.invalidateQueries({ queryKey: ['mau-mat', workerId] })
      qc.invalidateQueries({ queryKey: ['cong-nhan'] })
    },
    onError: () => setConfirm(null),
  })

  if (isLoading) return <div className="text-center py-5"><Spinner animation="border" /></div>
  if (isError || !worker) {
    return (
      <div className="sg-page">
        <Alert variant="danger">Không tìm thấy công nhân. <Link to="/cong-nhan">← Danh sách công nhân</Link></Alert>
      </div>
    )
  }
  const active = worker.status === 'dang_lam'

  return (
    <div className="sg-page">
      <div className="section-header">
        <div className="d-flex align-items-center gap-3 flex-wrap">
          <Link to="/cong-nhan" className="btn btn-secondary btn-sm">← Danh sách</Link>
          <h1 className="section-title mb-0">{worker.full_name}</h1>
          <span className="sg-sub">{worker.code}</span>
        </div>
        {active
          ? <Button variant="outline-danger" onClick={() => setConfirm('nghi')}>Cho nghỉ việc</Button>
          : <Button variant="outline-success" onClick={() => setConfirm('lai')}>Cho đi làm lại</Button>}
      </div>

      <Row className="g-3">
        <Col xl={4}><ProfileCard key={worker.id} worker={worker} teams={teamData?.ds ?? []} /></Col>
        <Col xl={8}>
          <FaceCard worker={worker} />
          <HistoryTabs workerId={workerId} />
        </Col>
      </Row>

      <ConfirmModal
        show={!!confirm}
        title={confirm === 'nghi' ? 'Cho nghỉ việc' : 'Cho đi làm lại'}
        message={confirm === 'nghi'
          ? <>Cho <b>{worker.full_name}</b> nghỉ việc?<br /><br />Hệ thống sẽ <b>xoá toàn bộ dữ liệu khuôn mặt</b> (vector và ảnh
              mẫu) của người này và không nhận diện người này ở cổng nữa. Lịch sử kiểm tra và bảng công vẫn được giữ.</>
          : <>Nhận lại <b>{worker.full_name}</b>? Cần ghi nhận đồng ý và đăng ký khuôn mặt lại từ đầu.</>}
        variant={confirm === 'nghi' ? 'danger' : 'success'}
        confirmLabel={confirm === 'nghi' ? 'Cho nghỉ việc' : 'Cho đi làm lại'}
        loading={action.isPending}
        onConfirm={() => action.mutate(confirm)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  )
}
