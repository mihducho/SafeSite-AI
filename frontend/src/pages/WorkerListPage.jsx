import { useEffect, useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Card, Col, Form, InputGroup, Modal, Row, Spinner, Table } from 'react-bootstrap'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { diLamLai, layDanhSachCongNhan, layDanhSachToDoi, nghiViec, taoMoiCongNhan } from '../api/endpoints.js'
import ConfirmModal from '../components/common/ConfirmModal.jsx'
import { Avatar, EmptyRow, Pager, StatusBadge } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { ngayGio } from '../lib/format.js'
import { CONG_NHAN } from '../lib/labels.js'
import { toast } from '../lib/toast.js'

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

// ─── Modal thêm công nhân ──────────────────────────────────────────────────────
const EMPTY = { code: '', full_name: '', phone: '', trade: '', team_id: '' }

function ThemCongNhanModal({ show, onHide, teams }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  useEffect(() => { if (show) { setForm(EMPTY); setError('') } }, [show])

  const mutation = useMutation({
    mutationFn: taoMoiCongNhan,
    meta: { silent: true },
    onSuccess: (w) => {
      qc.invalidateQueries({ queryKey: ['cong-nhan'] })
      toast.success('Đã thêm công nhân. Ghi nhận đồng ý rồi đăng ký khuôn mặt.')
      onHide()
      navigate(`/cong-nhan/${w.id}`)          // sang trang chi tiết để ghi nhận đồng ý và chụp mẫu
    },
    onError: (err) => setError(err.message),
  })
  const set = (f) => (e) => setForm((p) => ({ ...p, [f]: e.target.value }))
  const submit = (e) => {
    e.preventDefault()
    if (!form.code.trim() || !form.full_name.trim()) { setError('Cần nhập mã công nhân và họ tên.'); return }
    mutation.mutate({
      code: form.code.trim(), full_name: form.full_name.trim(), phone: form.phone.trim() || null,
      trade: form.trade.trim() || null, team_id: form.team_id ? Number(form.team_id) : null,
    })
  }

  return (
    <Modal show={show} onHide={onHide} centered>
      <Form onSubmit={submit} noValidate>
        <Modal.Header closeButton><Modal.Title>Thêm công nhân</Modal.Title></Modal.Header>
        <Modal.Body>
          <Row className="g-3">
            <Col md={6}><Form.Label htmlFor="a-code">Mã công nhân *</Form.Label>
              <Form.Control id="a-code" maxLength={20} placeholder="vd CN007" value={form.code} onChange={set('code')} autoFocus /></Col>
            <Col md={6}><Form.Label htmlFor="a-name">Họ tên *</Form.Label>
              <Form.Control id="a-name" maxLength={100} value={form.full_name} onChange={set('full_name')} /></Col>
            <Col md={6}><Form.Label htmlFor="a-phone">Điện thoại</Form.Label>
              <Form.Control id="a-phone" maxLength={20} value={form.phone} onChange={set('phone')} /></Col>
            <Col md={6}><Form.Label htmlFor="a-trade">Nghề</Form.Label>
              <Form.Control id="a-trade" maxLength={50} placeholder="vd Thợ xây" value={form.trade} onChange={set('trade')} /></Col>
            <Col xs={12}><Form.Label htmlFor="a-team">Tổ đội</Form.Label>
              <Form.Select id="a-team" value={form.team_id} onChange={set('team_id')}>
                <option value="">(chưa xếp tổ)</option>
                {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </Form.Select></Col>
          </Row>
          {error && <Alert variant="danger" className="mt-3 mb-0 py-2">{error}</Alert>}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onHide} disabled={mutation.isPending}>Huỷ</Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? <Spinner size="sm" /> : 'Thêm và đăng ký khuôn mặt'}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function WorkerListPage() {
  const qc = useQueryClient()
  const cfg = useWebConfig()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('q') ?? '')
  const q = useDebounce(search.trim(), 300)
  const teamFilter = params.get('to_doi') ?? ''                 // từ trang Tổ đội bấm vào số công nhân
  const statusFilter = params.get('trang_thai') ?? 'dang_lam'
  const [page, setPage] = useState(1)
  const [showAdd, setShowAdd] = useState(false)
  const [confirm, setConfirm] = useState(null)                  // { id, name, action: 'nghi' | 'lai' }

  const setParam = (k, v) => {
    const p = new URLSearchParams(params)
    if (v === '' && k !== 'trang_thai') p.delete(k); else p.set(k, v)
    setParams(p, { replace: true })
  }
  useEffect(() => { setPage(1) }, [q, teamFilter, statusFilter])

  const { data: teamData } = useQuery({ queryKey: ['to-doi'], queryFn: layDanhSachToDoi, staleTime: 60_000 })
  const teams = teamData?.ds ?? []
  const filters = { q: q || undefined, to_doi: teamFilter || undefined, trang_thai: statusFilter || undefined }
  const { data, isLoading } = useQuery({
    queryKey: ['cong-nhan', filters], queryFn: () => layDanhSachCongNhan(filters), placeholderData: keepPreviousData,
  })

  // API trả toàn bộ danh sách khớp bộ lọc -> phân trang phía trình duyệt
  const all = data?.ds ?? []
  const pages = Math.max(1, Math.ceil(all.length / cfg.pageSize))
  const safePage = Math.min(page, pages)
  const items = all.slice((safePage - 1) * cfg.pageSize, safePage * cfg.pageSize)

  const action = useMutation({
    mutationFn: ({ id, action: a }) => (a === 'nghi' ? nghiViec(id) : diLamLai(id)),
    onSuccess: (res, { action: a, id }) => {
      qc.invalidateQueries({ queryKey: ['cong-nhan'] })
      qc.invalidateQueries({ queryKey: ['worker', id] })
      qc.invalidateQueries({ queryKey: ['mau-mat', id] })
      toast.success(a === 'nghi' ? `Đã cho nghỉ việc, xoá ${res.so_mau_da_xoa ?? 0} mẫu khuôn mặt`
        : 'Đã nhận lại. Cần ghi nhận đồng ý và đăng ký lại khuôn mặt.')
      setConfirm(null)
    },
    onError: () => setConfirm(null),
  })

  return (
    <div className="sg-page">
      <div className="section-header">
        <h1 className="section-title mb-0">Công nhân {data && <span className="sg-sub ms-2">{data.tong} người</span>}</h1>
        <Button onClick={() => setShowAdd(true)}>➕ Thêm công nhân</Button>
      </div>

      <div className="sg-filters">
        <Form.Group style={{ minWidth: 260, flex: 1 }}>
          <Form.Label>Tìm kiếm</Form.Label>
          <InputGroup size="sm">
            <InputGroup.Text>🔍</InputGroup.Text>
            <Form.Control placeholder="Mã, họ tên hoặc số điện thoại" value={search} onChange={(e) => setSearch(e.target.value)} />
          </InputGroup>
        </Form.Group>
        <Form.Group>
          <Form.Label>Tổ đội</Form.Label>
          <Form.Select size="sm" value={teamFilter} onChange={(e) => setParam('to_doi', e.target.value)} style={{ minWidth: 180 }}>
            <option value="">Tất cả tổ</option>
            {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </Form.Select>
        </Form.Group>
        <Form.Group>
          <Form.Label>Trạng thái</Form.Label>
          <Form.Select size="sm" value={statusFilter} onChange={(e) => setParam('trang_thai', e.target.value)}>
            <option value="dang_lam">Đang làm</option>
            <option value="nghi_viec">Nghỉ việc</option>
            <option value="">Tất cả</option>
          </Form.Select>
        </Form.Group>
      </div>

      <Card>
        <div className="table-responsive">
          <Table hover className="mb-0 sg-table">
            <thead>
              <tr><th>Công nhân</th><th>Tổ đội</th><th>Nghề</th><th>Điện thoại</th><th>Trạng thái</th><th>Đồng ý</th>
                <th>Mẫu khuôn mặt</th><th className="text-end">Thao tác</th></tr>
            </thead>
            <tbody>
              {isLoading ? <EmptyRow colSpan={8}><Spinner size="sm" /></EmptyRow>
                : !items.length ? <EmptyRow colSpan={8}>Không có công nhân nào.</EmptyRow>
                  : items.map((w) => {
                    const enough = w.so_mau >= cfg.minSamples
                    return (
                      <tr key={w.id}>
                        <td>
                          <div className="d-flex align-items-center gap-2">
                            <Avatar name={w.full_name} workerId={w.id} size={36} />
                            <div>
                              <Link to={`/cong-nhan/${w.id}`} style={{ fontWeight: 600 }}>{w.full_name}</Link>
                              <div className="sg-sub">{w.code}</div>
                            </div>
                          </div>
                        </td>
                        <td>{w.team_name ?? '—'}</td>
                        <td>{w.trade ?? '—'}</td>
                        <td>{w.phone ?? '—'}</td>
                        <td><StatusBadge map={CONG_NHAN} value={w.status} /></td>
                        <td>{w.consent_at
                          ? <span className="text-success" title={ngayGio(w.consent_at)}>✔ Đã đồng ý</span>
                          : <span className="sg-muted">Chưa</span>}</td>
                        <td>{w.status !== 'dang_lam' ? <span className="sg-muted">—</span> : (
                          <Badge bg={enough ? 'success' : 'warning'} text={enough ? undefined : 'dark'}>
                            {w.so_mau}/{cfg.maxSamples} mẫu · {enough ? 'đủ' : `cần ${cfg.minSamples}`}
                          </Badge>
                        )}</td>
                        <td className="text-end text-nowrap">
                          <Link to={`/cong-nhan/${w.id}`} className="btn btn-outline-primary btn-sm me-1">Chi tiết</Link>
                          {w.status === 'dang_lam'
                            ? <Button variant="outline-danger" size="sm" onClick={() => setConfirm({ id: w.id, name: w.full_name, action: 'nghi' })}>Cho nghỉ</Button>
                            : <Button variant="outline-success" size="sm" onClick={() => setConfirm({ id: w.id, name: w.full_name, action: 'lai' })}>Đi làm lại</Button>}
                        </td>
                      </tr>
                    )
                  })}
            </tbody>
          </Table>
        </div>
        {pages > 1 && (
          <Card.Footer className="d-flex justify-content-end"><Pager page={safePage} pages={pages} onChange={setPage} /></Card.Footer>
        )}
      </Card>

      <ThemCongNhanModal show={showAdd} onHide={() => setShowAdd(false)} teams={teams} />
      <ConfirmModal
        show={!!confirm}
        title={confirm?.action === 'nghi' ? 'Cho nghỉ việc' : 'Cho đi làm lại'}
        message={confirm?.action === 'nghi'
          ? <>Cho <b>{confirm?.name}</b> nghỉ việc?<br /><br />Hệ thống sẽ <b>xoá toàn bộ dữ liệu khuôn mặt</b> (vector và ảnh mẫu)
              và không nhận diện người này ở cổng nữa. Lịch sử kiểm tra và bảng công vẫn được giữ.</>
          : <>Nhận lại <b>{confirm?.name}</b>? Cần ghi nhận đồng ý và đăng ký khuôn mặt lại từ đầu.</>}
        variant={confirm?.action === 'nghi' ? 'danger' : 'success'}
        confirmLabel={confirm?.action === 'nghi' ? 'Cho nghỉ việc' : 'Cho đi làm lại'}
        loading={action.isPending}
        onConfirm={() => action.mutate({ id: confirm.id, action: confirm.action })}
        onCancel={() => setConfirm(null)}
      />
    </div>
  )
}
