import { useEffect, useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Modal, Spinner } from 'react-bootstrap'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CircleAlert, CircleCheck, Eye, Pencil, Search, UserPlus, Users } from 'lucide-react'
import { layDanhSachCongNhan, layDanhSachToDoi, taoMoiCongNhan } from '../api/endpoints.js'
import {
  Card, EmptyRow, Meter, PageHead, Pager, Person, Pill, RowMenu, SkeletonRows, StatusBadge,
} from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
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
          <div className="row g-3">
            <div className="col-md-5"><Form.Label htmlFor="a-code">Mã công nhân</Form.Label>
              <Form.Control id="a-code" maxLength={20} placeholder="vd CN007" value={form.code} onChange={set('code')} autoFocus /></div>
            <div className="col-md-7"><Form.Label htmlFor="a-name">Họ tên</Form.Label>
              <Form.Control id="a-name" maxLength={100} value={form.full_name} onChange={set('full_name')} /></div>
            <div className="col-md-6"><Form.Label htmlFor="a-phone">Điện thoại</Form.Label>
              <Form.Control id="a-phone" maxLength={20} value={form.phone} onChange={set('phone')} /></div>
            <div className="col-md-6"><Form.Label htmlFor="a-trade">Nghề</Form.Label>
              <Form.Control id="a-trade" maxLength={50} placeholder="vd Thợ xây" value={form.trade} onChange={set('trade')} /></div>
            <div className="col-12"><Form.Label htmlFor="a-team">Tổ đội</Form.Label>
              <Form.Select id="a-team" value={form.team_id} onChange={set('team_id')}>
                <option value="">Chưa xếp tổ</option>
                {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </Form.Select></div>
          </div>
          <p className="small muted mt-3 mb-0">Sau khi thêm, hệ thống mở trang chi tiết để ghi nhận đồng ý và chụp mẫu khuôn mặt.</p>
          {error && <div className="note bad mt-3"><CircleAlert size={18} />{error}</div>}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onHide} disabled={mutation.isPending}>Huỷ</Button>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending && <Spinner size="sm" />}Thêm công nhân
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}

/** Cột Khuôn mặt: tiến độ mẫu + Sẵn sàng / Chưa đồng ý / Thiếu mẫu */
function FaceStatus({ w, min, max }) {
  if (w.status !== 'dang_lam') return null
  const ready = !!w.consent_at && w.so_mau >= min
  return (
    <div style={{ minWidth: 150 }}>
      <div className="d-flex align-items-center justify-content-between gap-2 mb-1">
        {ready ? <Pill tone="ok" icon={CircleCheck}>Sẵn sàng</Pill>
          : !w.consent_at ? <Pill tone="warn" icon={CircleAlert}>Chưa đồng ý</Pill>
            : <Pill tone="warn" icon={CircleAlert}>Thiếu mẫu</Pill>}
        <span className="small muted num">{w.so_mau}/{max} mẫu</span>
      </div>
      <Meter value={w.so_mau} max={max} warn={!ready} />
    </div>
  )
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function WorkerListPage() {
  const cfg = useWebConfig()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('q') ?? '')
  const q = useDebounce(search.trim(), 300)
  const teamFilter = params.get('to_doi') ?? ''                 // từ trang Tổ đội bấm vào số công nhân
  const statusFilter = params.get('trang_thai') ?? 'dang_lam'
  const [page, setPage] = useState(1)
  const [showAdd, setShowAdd] = useState(false)

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
  const filtered = !!(q || teamFilter || statusFilter !== 'dang_lam')

  return (
    <div className="page">
      <PageHead title="Công nhân" sub={data ? `${data.tong} người${statusFilter === 'dang_lam' ? ' đang làm' : ''}` : ' '}>
        <Button onClick={() => setShowAdd(true)}><UserPlus size={18} />Thêm công nhân</Button>
      </PageHead>

      <Card flush>
        <div className="filters">
          <div className="grow input-icon">
            <Search size={18} />
            <Form.Control placeholder="Tìm theo mã, họ tên hoặc số điện thoại" value={search} onChange={(e) => setSearch(e.target.value)}
              aria-label="Tìm kiếm" />
          </div>
          <Form.Select value={teamFilter} onChange={(e) => setParam('to_doi', e.target.value)} aria-label="Tổ đội" style={{ minWidth: 180 }}>
            <option value="">Tất cả tổ</option>
            {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </Form.Select>
          <Form.Select value={statusFilter} onChange={(e) => setParam('trang_thai', e.target.value)} aria-label="Trạng thái" style={{ minWidth: 160 }}>
            <option value="dang_lam">Đang làm</option>
            <option value="nghi_viec">Nghỉ việc</option>
            <option value="">Tất cả trạng thái</option>
          </Form.Select>
        </div>
        <div className="table-wrap">
          <table className="sg-table">
            <thead>
              <tr><th>Công nhân</th><th>Tổ đội</th><th>Nghề</th><th>Điện thoại</th><th>Trạng thái</th><th>Khuôn mặt</th><th className="shrink" /></tr>
            </thead>
            <tbody>
              {isLoading ? <SkeletonRows cols={7} />
                : !items.length ? (
                  filtered
                    ? <EmptyRow colSpan={7} icon={Search} title="Không tìm thấy công nhân nào" text="Thử đổi từ khoá hoặc bộ lọc." />
                    : <EmptyRow colSpan={7} icon={Users} title="Chưa có công nhân nào"
                        action={<Button onClick={() => setShowAdd(true)}><UserPlus size={18} />Thêm công nhân đầu tiên</Button>} />
                ) : items.map((w) => (
                  <tr key={w.id} className="clickable" onClick={() => navigate(`/cong-nhan/${w.id}`)}>
                    <td><Person name={w.full_name} code={w.code} workerId={w.id} /></td>
                    <td>{w.team_name}</td>
                    <td>{w.trade}</td>
                    <td className="num">{w.phone}</td>
                    <td><StatusBadge map={CONG_NHAN} value={w.status} /></td>
                    <td><FaceStatus w={w} min={cfg.minSamples} max={cfg.maxSamples} /></td>
                    <td className="shrink">
                      <RowMenu items={[
                        { label: 'Xem chi tiết', icon: Eye, onClick: () => navigate(`/cong-nhan/${w.id}`) },
                        { label: 'Sửa thông tin', icon: Pencil, onClick: () => navigate(`/cong-nhan/${w.id}?sua=1`) },
                      ]} />
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        {pages > 1 && (
          <div className="sg-card__foot">
            <span>Trang {safePage}/{pages}</span>
            <Pager page={safePage} pages={pages} onChange={setPage} />
          </div>
        )}
      </Card>

      <ThemCongNhanModal show={showAdd} onHide={() => setShowAdd(false)} teams={teams} />
    </div>
  )
}
