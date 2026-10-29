import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Card, Col, Form, Modal, Row, Spinner } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import { capNhatToDoi, layDanhSachToDoi, taoMoiToDoi } from '../api/endpoints.js'
import { toast } from '../lib/toast.js'

// ─── Modal thêm / sửa tổ đội ───────────────────────────────────────────────────
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
        <Modal.Header closeButton><Modal.Title>{isEdit ? `Sửa tổ: ${initial.name}` : 'Thêm tổ đội'}</Modal.Title></Modal.Header>
        <Modal.Body>
          <Form.Group className="mb-3">
            <Form.Label htmlFor="t-name">Tên tổ *</Form.Label>
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
          {error && <Alert variant="danger" className="mt-3 mb-0 py-2">{error}</Alert>}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>Huỷ</Button>
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? <Spinner size="sm" /> : 'Lưu'}</Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}

function TeamCard({ team, onEdit }) {
  return (
    <Card className="h-100">
      <Card.Body className="d-flex flex-column">
        <div className="d-flex justify-content-between align-items-start mb-2 gap-2">
          <Card.Title className="mb-0 fw-bold" style={{ fontSize: '1.05rem' }}>{team.name}</Card.Title>
          <Link to={`/cong-nhan?to_doi=${team.id}`} title="Xem công nhân của tổ">
            <Badge bg="warning" text="dark" style={{ fontSize: '0.85rem', padding: '4px 10px', borderRadius: 20 }}>
              {team.so_cong_nhan ?? 0} công nhân
            </Badge>
          </Link>
        </div>
        <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', flex: 1 }}>
          <div className="mb-1">🏗️ Nhà thầu phụ: <span style={{ color: 'var(--text-primary)' }}>{team.contractor || '—'}</span></div>
          <div>👤 Tổ trưởng: <span style={{ color: 'var(--text-primary)' }}>{team.leader_name || '—'}</span></div>
        </div>
        <div className="mt-3 pt-2" style={{ borderTop: '1px solid var(--border-color)' }}>
          <Button variant="outline-primary" size="sm" onClick={() => onEdit(team)}>✏️ Sửa</Button>
        </div>
      </Card.Body>
    </Card>
  )
}

export default function TeamPage() {
  const [modalData, setModalData] = useState(null)   // null = đóng, {} = thêm, {id,...} = sửa
  const { data, isLoading } = useQuery({ queryKey: ['to-doi'], queryFn: layDanhSachToDoi })
  const ds = data?.ds ?? []

  return (
    <div className="sg-page">
      {modalData !== null && <ToDoiModal initial={modalData} onClose={() => setModalData(null)} />}
      <div className="section-header">
        <h1 className="section-title mb-0">Tổ đội <span className="sg-sub ms-2">{ds.length} tổ</span></h1>
        <Button onClick={() => setModalData({})}>➕ Thêm tổ đội</Button>
      </div>
      {isLoading ? <div className="text-center py-5"><Spinner animation="border" /></div>
        : !ds.length ? (
          <div className="empty-state">
            <p className="empty-state-text">Chưa có tổ đội nào.</p>
            <Button onClick={() => setModalData({})}>Thêm tổ đội đầu tiên</Button>
          </div>
        ) : (
          <Row className="g-3">
            {ds.map((team) => (
              <Col key={team.id} xs={12} sm={6} lg={4} xl={3}><TeamCard team={team} onEdit={setModalData} /></Col>
            ))}
          </Row>
        )}
    </div>
  )
}
