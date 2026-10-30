import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Modal, Spinner } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import { Building2, ChevronRight, CircleAlert, Pencil, Plus, UserRound, UsersRound } from 'lucide-react'
import { capNhatToDoi, layDanhSachToDoi, taoMoiToDoi } from '../api/endpoints.js'
import { Avatar, Card, EmptyState, PageHead, Skeleton } from '../components/common/ui.jsx'
import { toast } from '../lib/toast.js'

// ─── Cửa sổ thêm / sửa tổ đội ──────────────────────────────────────────────────
function ToDoiModal({ initial, onClose }) {
  const qc = useQueryClient()
  const isEdit = !!initial?.id
  const [name, setName] = useState(initial?.name ?? '')
  const [contractor, setContractor] = useState(initial?.contractor ?? '')
  const [leader, setLeader] = useState(initial?.leader_name ?? '')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: (body) => (isEdit ? capNhatToDoi(initial.id, body) : taoMoiToDoi(body)),
    meta: { silent: true },
    onSuccess: () => {
      toast.success(isEdit ? 'Đã lưu tổ đội' : 'Đã thêm tổ đội')
      qc.invalidateQueries({ queryKey: ['to-doi'] })
      onClose()
    },
    onError: (err) => setError(err.message),
  })
  const submit = (e) => {
    e.preventDefault()
    if (!name.trim()) { setError('Cần nhập tên tổ.'); return }
    mutation.mutate({ name: name.trim(), contractor: contractor.trim() || null, leader_name: leader.trim() || null })
  }

  return (
    <Modal show onHide={onClose} centered backdrop="static">
      <Form onSubmit={submit} noValidate>
        <Modal.Header closeButton><Modal.Title>{isEdit ? 'Sửa tổ đội' : 'Thêm tổ đội'}</Modal.Title></Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3">
            <Form.Label htmlFor="t-name">Tên tổ</Form.Label>
            <Form.Control id="t-name" maxLength={100} value={name} onChange={(e) => setName(e.target.value)} placeholder="vd Tổ xây dựng A" autoFocus />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label htmlFor="t-contractor">Nhà thầu phụ</Form.Label>
            <Form.Control id="t-contractor" maxLength={100} value={contractor} onChange={(e) => setContractor(e.target.value)} />
          </Form.Group>
          <Form.Group>
            <Form.Label htmlFor="t-leader">Tổ trưởng</Form.Label>
            <Form.Control id="t-leader" maxLength={100} value={leader} onChange={(e) => setLeader(e.target.value)} />
          </Form.Group>
          {error && <div className="note bad mt-3"><CircleAlert size={17} strokeWidth={1.5} />{error}</div>}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>Huỷ</Button>
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending && <Spinner size="sm" />}{isEdit ? 'Lưu' : 'Thêm tổ đội'}</Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}

function TeamCard({ team, onEdit }) {
  return (
    <section className="sg-card d-flex flex-column">
      <div className="d-flex align-items-start gap-3 p-3 pb-2">
        <Avatar name={team.name} size={38} face={false} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 14.5, fontWeight: 600 }}>{team.name}</div>
          <div className="team-kv mt-2">
            <span><Building2 size={14} strokeWidth={1.5} />Nhà thầu phụ</span><b>{team.contractor}</b>
            <span><UserRound size={14} strokeWidth={1.5} />Tổ trưởng</span><b>{team.leader_name}</b>
          </div>
        </div>
        <Button variant="text" className="btn-text btn-icon" onClick={() => onEdit(team)} aria-label={`Sửa ${team.name}`} title="Sửa"><Pencil size={16} strokeWidth={1.5} /></Button>
      </div>
      <Link to={`/cong-nhan?to_doi=${team.id}`} className="team-foot">
        <span><b className="num">{team.so_cong_nhan ?? 0}</b> công nhân đang làm</span><ChevronRight size={16} strokeWidth={1.5} />
      </Link>
    </section>
  )
}

export default function TeamPage() {
  const [modalData, setModalData] = useState(null)   // null = đóng, {} = thêm, {id,...} = sửa
  const { data, isLoading } = useQuery({ queryKey: ['to-doi'], queryFn: layDanhSachToDoi })
  const ds = data?.ds ?? []

  return (
    <div className="page">
      {modalData !== null && <ToDoiModal initial={modalData} onClose={() => setModalData(null)} />}
      <PageHead title="Tổ đội" sub={data ? `${ds.length} tổ · ${ds.reduce((s, t) => s + (t.so_cong_nhan ?? 0), 0)} công nhân đang làm` : ' '}>
        <Button onClick={() => setModalData({})}><Plus size={16} strokeWidth={1.5} />Thêm tổ đội</Button>
      </PageHead>
      {isLoading ? <div className="grid team-grid">{[1, 2, 3].map((k) => <Card key={k}><Skeleton height={90} /></Card>)}</div>
        : !ds.length ? (
          <Card><EmptyState icon={UsersRound} title="Chưa có tổ đội nào" text="Tạo tổ đội để xếp công nhân và lọc bảng công theo tổ."
            action={<Button onClick={() => setModalData({})}><Plus size={16} strokeWidth={1.5} />Thêm tổ đội đầu tiên</Button>} /></Card>
        ) : <div className="grid team-grid">{ds.map((t) => <TeamCard key={t.id} team={t} onEdit={setModalData} />)}</div>}
    </div>
  )
}
