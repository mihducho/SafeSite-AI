import { useEffect, useRef, useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Modal, Spinner } from 'react-bootstrap'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, CalendarDays, Camera, CircleAlert, CircleCheck, History, Images, Pencil, ScanFace, ShieldCheck, Trash2,
  Upload, UserRoundCheck, UserX, X,
} from 'lucide-react'
import {
  capNhatCongNhan, chupMauMat, diLamLai, ghiNhanDongY, layBangCongCongNhan, layCaLam, layChiTietCongNhan,
  layDanhSachMauMat, layDanhSachToDoi, layLichSuLuot, layNoiDungDongY, nghiViec, taiLenMauMat, xoaMauMat, xoaTatCaMauMat,
} from '../api/endpoints.js'
import CheckDetailModal from '../components/common/CheckDetailModal.jsx'
import CheckTable from '../components/common/CheckTable.jsx'
import ConfirmModal from '../components/common/ConfirmModal.jsx'
import ManualAttendanceModal from '../components/common/ManualAttendanceModal.jsx'
import {
  Avatar, Card, EmptyRow, EmptyState, LiveStream, Meter, Pager, Pill, Skeleton, SkeletonRows, StatusBadge, Tabs,
} from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents } from '../lib/events.js'
import { gio, gioPhutChu, ngay, soVN, thuNgay } from '../lib/format.js'
import { CONG_NHAN, trangThaiNgay } from '../lib/labels.js'
import { toast } from '../lib/toast.js'

// ─── Sửa thông tin (cửa sổ) ───────────────────────────────────────────────────
function EditModal({ worker, teams, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    code: worker.code, full_name: worker.full_name, phone: worker.phone ?? '', trade: worker.trade ?? '', team_id: worker.team_id ?? '',
  })
  const [error, setError] = useState('')
  const save = useMutation({
    mutationFn: (body) => capNhatCongNhan(worker.id, body),
    meta: { silent: true },
    onSuccess: () => {
      toast.success('Đã lưu thông tin')
      qc.invalidateQueries({ queryKey: ['worker', worker.id] })
      qc.invalidateQueries({ queryKey: ['cong-nhan'] })
      onClose()
    },
    onError: (err) => setError(err.message),
  })
  const set = (f) => (e) => setForm((p) => ({ ...p, [f]: e.target.value }))
  const submit = (e) => {
    e.preventDefault()
    if (!form.code.trim() || !form.full_name.trim()) { setError('Cần nhập mã công nhân và họ tên.'); return }
    save.mutate({
      code: form.code.trim(), full_name: form.full_name.trim(), phone: form.phone.trim() || null,
      trade: form.trade.trim() || null, team_id: form.team_id ? Number(form.team_id) : null,
    })
  }
  return (
    <Modal show onHide={onClose} centered>
      <Form onSubmit={submit} noValidate>
        <Modal.Header closeButton><Modal.Title>Sửa thông tin công nhân</Modal.Title></Modal.Header>
        <Modal.Body>
          <div className="row g-3">
            <div className="col-5"><Form.Label htmlFor="i-code">Mã công nhân</Form.Label>
              <Form.Control id="i-code" maxLength={20} value={form.code} onChange={set('code')} /></div>
            <div className="col-7"><Form.Label htmlFor="i-name">Họ tên</Form.Label>
              <Form.Control id="i-name" maxLength={100} value={form.full_name} onChange={set('full_name')} autoFocus /></div>
            <div className="col-6"><Form.Label htmlFor="i-phone">Điện thoại</Form.Label>
              <Form.Control id="i-phone" maxLength={20} value={form.phone} onChange={set('phone')} /></div>
            <div className="col-6"><Form.Label htmlFor="i-trade">Nghề</Form.Label>
              <Form.Control id="i-trade" maxLength={50} value={form.trade} onChange={set('trade')} /></div>
            <div className="col-12"><Form.Label htmlFor="i-team">Tổ đội</Form.Label>
              <Form.Select id="i-team" value={form.team_id} onChange={set('team_id')}>
                <option value="">Chưa xếp tổ</option>
                {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </Form.Select></div>
          </div>
          {error && <div className="note bad mt-3"><CircleAlert size={18} />{error}</div>}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onClose} disabled={save.isPending}>Huỷ</Button>
          <Button type="submit" disabled={save.isPending}>{save.isPending && <Spinner size="sm" />}Lưu thông tin</Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}

// ─── Thẻ hồ sơ ─────────────────────────────────────────────────────────────────
function ProfileCard({ worker, onEdit, onQuit, onRejoin }) {
  const { data: shift } = useQuery({ queryKey: ['ca-lam'], queryFn: layCaLam, staleTime: 60_000 })
  const active = worker.status === 'dang_lam'
  const rows = [
    ['Mã công nhân', worker.code],
    ['Tổ đội', worker.team_name],
    ['Nghề', worker.trade],
    ['Điện thoại', worker.phone],
    ['Ca làm', shift ? `${shift.name}, ${shift.start_time} – ${shift.end_time}` : ''],
    ['Ngày thêm', worker.created_at ? ngay(worker.created_at) : ''],
  ]
  return (
    <Card>
      <div className="d-flex flex-column align-items-center text-center pb-3 mb-2" style={{ borderBottom: '1px solid var(--line)' }}>
        <Avatar name={worker.full_name} workerId={worker.id} size={96} />
        <div style={{ fontSize: 20, fontWeight: 700, marginTop: 12 }}>{worker.full_name}</div>
        <div className="muted mb-2">{worker.code}</div>
        <StatusBadge map={CONG_NHAN} value={worker.status} />
      </div>
      <table className="kv"><tbody>
        {rows.map(([k, v]) => <tr key={k}><th>{k}</th><td>{v}</td></tr>)}
      </tbody></table>
      <div className="d-flex flex-column gap-2 mt-3">
        <Button variant="secondary" onClick={onEdit}><Pencil size={17} />Sửa thông tin</Button>
        {active
          ? <Button variant="text-danger" className="btn-text-danger" onClick={onQuit}><UserX size={17} />Cho nghỉ việc</Button>
          : <Button variant="secondary" onClick={onRejoin}><UserRoundCheck size={17} />Cho đi làm lại</Button>}
      </div>
    </Card>
  )
}

// ─── Tab Khuôn mặt: đồng ý + chụp / tải mẫu + lưới ảnh ────────────────────────
function FaceTab({ worker }) {
  const qc = useQueryClient()
  const cfg = useWebConfig()
  const fileRef = useRef(null)
  const [agree, setAgree] = useState(false)
  const [captureMsg, setCaptureMsg] = useState(null)   // { ok, text }
  const [uploadMsg, setUploadMsg] = useState([])
  const [confirm, setConfirm] = useState(null)         // { kind: 'one', id } | { kind: 'all' }

  const { data: consentText } = useQuery({ queryKey: ['dong-y-noi-dung'], queryFn: layNoiDungDongY, staleTime: Infinity })
  const { data: mau, isLoading } = useQuery({ queryKey: ['mau-mat', worker.id], queryFn: () => layDanhSachMauMat(worker.id) })

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
    meta: { silent: true },                         // lỗi hiện ngay dưới khung xem trước (rõ hơn toast)
    onSuccess: (r) => { setCaptureMsg({ ok: true, text: `Đã chụp mẫu, chất lượng ${soVN(r.mau.quality)}. Hiện có ${r.so_mau} mẫu.` }); refresh() },
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
    <div className="sg-card__body stack">
      {!active && <div className="note neutral"><CircleAlert size={18} />Công nhân đã nghỉ việc nên không đăng ký khuôn mặt. Cho đi làm lại để đăng ký từ đầu.</div>}

      {/* (1) Đồng ý: bắt buộc trước khi lấy dữ liệu sinh trắc học */}
      <section>
        <div className="d-flex align-items-center gap-2 mb-2">
          <ShieldCheck size={18} className="muted" /><b>Đồng ý đăng ký khuôn mặt</b>
          {consented && <Pill tone="ok" icon={CircleCheck}>Đã đồng ý</Pill>}
        </div>
        <div className="p-3 rounded small" style={{ background: 'var(--surface-soft)', border: '1px solid var(--line)', lineHeight: 1.65, whiteSpace: 'pre-line' }}>
          {consentText?.noi_dung ?? <Skeleton height={40} />}
        </div>
        {consented ? (
          <div className="small muted mt-2">
            Ghi nhận lúc <b className="num" style={{ color: 'var(--text)' }}>{gio(worker.consent_at)} {ngay(worker.consent_at)}</b>
            {worker.consent_by_name && <> bởi <b style={{ color: 'var(--text)' }}>{worker.consent_by_name}</b></>}
          </div>
        ) : active && (
          <div className="d-flex align-items-center gap-3 flex-wrap mt-2">
            <Form.Check id="consent-check" checked={agree} onChange={(e) => setAgree(e.target.checked)}
              label="Công nhân đã đọc và đồng ý với nội dung trên" />
            <Button variant="secondary" size="sm" disabled={!agree || consent.isPending} onClick={() => consent.mutate()}>
              {consent.isPending && <Spinner size="sm" />}Ghi nhận đồng ý
            </Button>
          </div>
        )}
      </section>

      {/* (2) Xem trước camera cổng + chụp / tải ảnh */}
      {canEnroll && (
        <section className="d-flex gap-4 flex-wrap">
          <div style={{ flex: '0 0 auto' }}>
            {!full ? <LiveStream className="portrait" style={{ height: 'min(46vh, 460px)', width: 'calc(min(46vh, 460px) * 0.5625)' }} alt="Hình trực tiếp camera cổng" />
              : <div className="portrait d-flex align-items-center justify-content-center" style={{ height: 260, width: 146, color: '#94A3B8' }}>Đã đủ {MAX} mẫu</div>}
          </div>
          <div style={{ flex: "1 1 240px", minWidth: 240 }}>
            <b>Chụp mẫu từ camera cổng</b>
            <p className="small muted mt-1">Công nhân đứng vào vùng kiểm tra, nhìn thẳng camera. Mỗi lần chụp đổi góc mặt một chút; nên có cả mẫu đội mũ và không đội mũ.</p>
            <div className="d-flex gap-2 flex-wrap">
              <Button disabled={full || capture.isPending} onClick={() => { setCaptureMsg(null); capture.mutate() }}>
                {capture.isPending ? <Spinner size="sm" /> : <Camera size={18} />}{capture.isPending ? 'Đang chụp…' : 'Chụp mẫu'}
              </Button>
              <Button variant="secondary" disabled={full || upload.isPending} onClick={() => fileRef.current?.click()}>
                {upload.isPending ? <Spinner size="sm" /> : <Upload size={18} />}Tải ảnh lên
              </Button>
              <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={onFiles} />
            </div>
            {captureMsg && (
              <div className={`note ${captureMsg.ok ? 'ok' : 'bad'} mt-3`}>
                {captureMsg.ok ? <CircleCheck size={18} /> : <CircleAlert size={18} />}{captureMsg.text}
              </div>
            )}
            {uploadMsg.length > 0 && (
              <ul className="list-unstyled small mt-3 mb-0 d-flex flex-column gap-1">
                {uploadMsg.map((x, i) => (
                  <li key={i} className={`d-flex gap-2 ${x.ok ? 'text-ok' : 'text-bad'}`}>
                    {x.ok ? <CircleCheck size={16} /> : <CircleAlert size={16} />}<span>{x.ten}{x.ok ? '' : `: ${x.ly_do}`}</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="small muted mt-3 mb-0">Ảnh tải lên: mỗi ảnh đúng 1 khuôn mặt, rõ, đủ sáng (tối đa {cfg.maxUploadMb} MB). Hệ thống chỉ lưu vector và ảnh mặt 112×112, không lưu ảnh gốc.</p>
          </div>
        </section>
      )}
      {active && !consented && <div className="note warn"><CircleAlert size={18} />Cần ghi nhận đồng ý của công nhân trước khi chụp hoặc tải ảnh khuôn mặt.</div>}

      {/* (3) Tiến độ + (4) lưới ảnh mẫu */}
      <section>
        <div className="d-flex align-items-center gap-3 mb-2">
          <b>Ảnh mẫu</b>
          <span className="small muted num">{count}/{MAX} mẫu, tối thiểu {MIN}</span>
          {count > 0 && (
            <Button variant="text-danger" size="sm" className="btn-text-danger ms-auto" onClick={() => setConfirm({ kind: 'all' })}>
              <Trash2 size={16} />Xoá tất cả
            </Button>
          )}
        </div>
        <Meter value={count} max={MAX} warn={count < MIN} style={{ marginBottom: 16 }} />
        {isLoading ? <Skeleton width={112} height={112} />
          : samples.length ? (
            <div className="face-grid">
              {samples.map((s) => (
                <figure key={s.id} className="face">
                  <img src={s.anh} alt={`Mẫu ${s.id}`} />
                  <button type="button" title="Xoá mẫu này" aria-label="Xoá mẫu này" onClick={() => setConfirm({ kind: 'one', id: s.id })}><X size={14} /></button>
                  <figcaption>{s.source === 'camera' ? 'Camera' : 'Tải lên'} · {soVN(s.quality)}</figcaption>
                </figure>
              ))}
            </div>
          ) : <EmptyState icon={Images} title="Chưa có ảnh mẫu" text={canEnroll ? 'Chụp từ camera cổng hoặc tải ảnh lên để đăng ký.' : undefined} />}
      </section>

      <ConfirmModal
        show={!!confirm}
        title={confirm?.kind === 'all' ? 'Xoá toàn bộ dữ liệu khuôn mặt?' : 'Xoá mẫu khuôn mặt này?'}
        message={confirm?.kind === 'all'
          ? <>Toàn bộ mẫu khuôn mặt (vector và ảnh mẫu) của <b>{worker.full_name}</b> sẽ bị xoá. Công nhân không được nhận diện ở cổng
              cho tới khi đăng ký lại.</>
          : 'Mẫu này sẽ bị xoá khỏi dữ liệu nhận diện.'}
        variant="danger"
        confirmLabel="Xoá"
        loading={remove.isPending}
        onConfirm={() => remove.mutate(confirm)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  )
}

// ─── Tab Lịch sử kiểm tra ──────────────────────────────────────────────────────
function HistoryTab({ workerId, onOpen, onManual }) {
  const cfg = useWebConfig()
  const [page, setPage] = useState(1)
  const query = { cong_nhan_id: workerId, trang: page, so_dong: cfg.pageSize }
  const { data, isLoading } = useQuery({
    queryKey: ['lich-su-luot', query], queryFn: () => layLichSuLuot(query), placeholderData: keepPreviousData,
  })
  return (
    <>
      <div className="table-wrap no-max"><CheckTable ds={data?.ds} loading={isLoading} onOpen={onOpen} onManual={onManual}
        emptyTitle="Chưa có lượt kiểm tra nào" emptyText="Lượt của công nhân này ở cổng sẽ hiện ở đây." /></div>
      {(data?.so_trang ?? 1) > 1 && (
        <div className="sg-card__foot"><span>{data.tong} lượt</span><Pager page={page} pages={data.so_trang} onChange={setPage} /></div>
      )}
    </>
  )
}

// ─── Tab Bảng công 30 ngày ─────────────────────────────────────────────────────
function SheetTab({ workerId }) {
  const { data, isLoading } = useQuery({ queryKey: ['bang-cong-cn', workerId, 30], queryFn: () => layBangCongCongNhan(workerId, 30) })
  return (
    <div className="table-wrap no-max">
      <table className="sg-table">
        <thead><tr><th>Ngày</th><th>Giờ vào</th><th>Giờ ra</th><th>Đi muộn</th><th>Giờ làm</th><th>Trạng thái</th></tr></thead>
        <tbody>
          {isLoading ? <SkeletonRows cols={6} />
            : !data?.ds.length ? <EmptyRow colSpan={6} icon={CalendarDays} title="Chưa có ngày công nào trong 30 ngày gần nhất" />
              : data.ds.map((r) => {
                const [text, tone] = trangThaiNgay(r)
                return (
                  <tr key={r.ngay}>
                    <td className="nowrap" style={{ fontWeight: 600 }}>{thuNgay(r.ngay)}</td>
                    <td className="num">{r.gio_vao}</td>
                    <td className="num">{r.gio_ra}</td>
                    <td>{r.di_muon_phut > 0 && <Pill tone="warn">+{r.di_muon_phut} phút</Pill>}</td>
                    <td className="nowrap">{r.gio_ra ? gioPhutChu(r.so_phut_lam) : ''}</td>
                    <td><Pill tone={tone}>{text}</Pill></td>
                  </tr>
                )
              })}
        </tbody>
      </table>
    </div>
  )
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function WorkerDetailPage() {
  const { id } = useParams()
  const workerId = Number(id)
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [tab, setTab] = useState('mat')
  const [confirm, setConfirm] = useState(null)   // 'nghi' | 'lai'
  const [checkId, setCheckId] = useState(null)
  const [manual, setManual] = useState(null)
  const editing = params.get('sua') === '1'      // từ danh sách: menu "Sửa thông tin"

  const { data: worker, isLoading, isError } = useQuery({
    queryKey: ['worker', workerId], queryFn: () => layChiTietCongNhan(workerId), enabled: !!workerId,
  })
  const { data: teamData } = useQuery({ queryKey: ['to-doi'], queryFn: layDanhSachToDoi, staleTime: 60_000 })
  const { data: checkCount } = useQuery({
    queryKey: ['lich-su-luot', { cong_nhan_id: workerId, so_dong: 1 }], queryFn: () => layLichSuLuot({ cong_nhan_id: workerId, so_dong: 1 }),
  })
  useGateEvents((ev) => {
    if (ev.loai === 'luot' && ev.cong_nhan?.id === workerId) {
      qc.invalidateQueries({ queryKey: ['lich-su-luot'] })
      qc.invalidateQueries({ queryKey: ['bang-cong-cn', workerId] })
    }
  })
  useEffect(() => { if (worker) document.title = `${worker.full_name} · SafeGate` }, [worker])

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
  const closeEdit = () => { const p = new URLSearchParams(params); p.delete('sua'); setParams(p, { replace: true }) }

  if (isError) {
    return (
      <div className="page">
        <Card><EmptyState icon={ScanFace} title="Không tìm thấy công nhân" action={<Link to="/cong-nhan" className="btn btn-secondary"><ArrowLeft size={17} />Về danh sách</Link>} /></Card>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <Link to="/cong-nhan" className="btn btn-text btn-sm mb-2" style={{ marginLeft: -8 }}><ArrowLeft size={16} />Danh sách công nhân</Link>
          <h1>{worker ? worker.full_name : <Skeleton width={240} height={28} />}</h1>
          <p>{worker ? `${worker.code}${worker.team_name ? ` · ${worker.team_name}` : ''}` : ' '}</p>
        </div>
      </div>

      <div className="grid grid-1-2" style={{ alignItems: 'start' }}>
        {isLoading || !worker ? <Card><Skeleton height={320} /></Card>
          : <ProfileCard worker={worker} onEdit={() => setParams({ sua: '1' }, { replace: true })}
              onQuit={() => setConfirm('nghi')} onRejoin={() => setConfirm('lai')} />}
        <section className="sg-card">
          <Tabs active={tab} onChange={setTab} tabs={[
            { key: 'mat', label: 'Khuôn mặt', icon: ScanFace },
            { key: 'luot', label: 'Lịch sử kiểm tra', icon: History, count: checkCount?.tong },
            { key: 'cong', label: 'Bảng công', icon: CalendarDays },
          ]} />
          {!worker ? <div className="sg-card__body"><Skeleton height={300} /></div>
            : tab === 'mat' ? <FaceTab worker={worker} />
              : tab === 'luot' ? <HistoryTab workerId={workerId} onOpen={setCheckId} onManual={setManual} />
                : <SheetTab workerId={workerId} />}
        </section>
      </div>

      {worker && editing && <EditModal worker={worker} teams={teamData?.ds ?? []} onClose={closeEdit} />}
      <CheckDetailModal id={checkId} onHide={() => setCheckId(null)} />
      {manual && (
        <ManualAttendanceModal worker={manual.cong_nhan} ngay={manual.thoi_diem.slice(0, 10)}
          gioVao={manual.huong !== 'ra' ? gio(manual.thoi_diem) : ''} gioRa={manual.huong === 'ra' ? gio(manual.thoi_diem) : ''}
          note={`từ lượt lúc ${gio(manual.thoi_diem, true)}`} onClose={() => setManual(null)} />
      )}
      {worker && (
        <ConfirmModal
          show={!!confirm}
          title={confirm === 'nghi' ? `Cho ${worker.full_name} nghỉ việc?` : `Nhận lại ${worker.full_name}?`}
          message={confirm === 'nghi'
            ? <>Hệ thống sẽ <b>xoá toàn bộ dữ liệu khuôn mặt</b> (vector và ảnh mẫu) của người này và không nhận diện ở cổng nữa.
                Lịch sử kiểm tra và bảng công vẫn được giữ.</>
            : 'Công nhân sẽ trở lại trạng thái đang làm. Cần ghi nhận đồng ý và đăng ký khuôn mặt lại từ đầu.'}
          variant={confirm === 'nghi' ? 'danger' : 'primary'}
          confirmLabel={confirm === 'nghi' ? 'Cho nghỉ việc' : 'Cho đi làm lại'}
          loading={action.isPending}
          onConfirm={() => action.mutate(confirm)}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  )
}
