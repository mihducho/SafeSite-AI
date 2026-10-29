import { useState } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { Button, Container, Form, Spinner, Table } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { layBangCongThang, layDanhSachToDoi, taiExcelThang } from '../api/endpoints'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { toast } from '../lib/toast.js'

// ─── helpers ──────────────────────────────────────────────────────────────────

function formatPhut(phut) {
  if (phut == null || phut === 0) return ''
  const h = Math.floor(phut / 60)
  const m = phut % 60
  if (h === 0) return `${m}p`
  if (m === 0) return `${h}h`
  return `${h}h${m}p`
}

function cellStyle(ngayData) {
  if (!ngayData) return { background: 'transparent', color: '#555' }
  const ts = ngayData.trang_thai
  if (ts === 'binh_thuong' && ngayData.thieu_gio_ra) return { background: '#3a0a0a', color: '#ff6b6b' }
  if (ts === 'binh_thuong')   return { background: '#1a4731', color: '#51cf66' }
  if (ts === 'ngoai_ca')      return { background: '#3a3000', color: '#ffd43b' }
  if (ts === 'cham_thu_cong') return { background: '#3a1a00', color: '#f7931e' }
  if (ngayData.thieu_gio_ra)  return { background: '#3a0a0a', color: '#ff6b6b' }
  return { background: 'transparent', color: '#adb5bd' }
}

function DayCell({ ngayData, onOpen }) {
  if (!ngayData || !ngayData.gio_vao) return <td style={{ background: 'rgba(0,0,0,0.2)', color: '#444', textAlign: 'center', fontSize: '0.7rem' }}>—</td>
  const st = cellStyle(ngayData)
  return (
    <td
      title={`${ngayData.gio_vao}–${ngayData.gio_ra ?? '?'} · bấm để xem bảng công ngày này`}
      onClick={() => onOpen(ngayData.ngay)}
      style={{
        ...st,
        cursor: 'pointer',
        textAlign: 'center',
        fontSize: '0.7rem',
        fontWeight: 500,
        padding: '4px 2px',
        whiteSpace: 'nowrap',
        minWidth: 36,
      }}
    >
      {ngayData.gio_ra ? formatPhut(ngayData.so_phut_lam) || '0p' : 'vào'}
    </td>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function MonthlyAttendancePage() {
  const cfg = useWebConfig()
  const navigate = useNavigate()
  const [thang, setThang]   = useState(cfg.today.slice(0, 7))
  const [toDoi, setToDoi]   = useState('')
  const [exporting, setExporting] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['bang-cong-thang', thang, toDoi],
    queryFn: () => layBangCongThang({ thang, to_doi: toDoi || undefined }),
    placeholderData: keepPreviousData,
  })

  const { data: toDoiData } = useQuery({
    queryKey: ['to-doi'],
    queryFn: () => layDanhSachToDoi(),
    staleTime: 60_000,
  })

  const cacNgay  = Array.from({ length: data?.so_ngay ?? 0 }, (_, i) => i + 1)
  const workers  = data?.ds ?? []

  const handleExport = async () => {
    setExporting(true)
    try {
      const blob = await taiExcelThang({ thang, to_doi: toDoi || undefined })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `bang_cong_${thang.replace('-', '_')}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.error(`Không xuất được file Excel: ${err.message}`)
    } finally {
      setExporting(false)
    }
  }

  return (
    <Container fluid className="py-4 px-3 px-md-4" style={{ maxWidth: '100%' }}>
      <div className="d-flex align-items-center justify-content-between mb-4 flex-wrap gap-2">
        <h1 className="section-title mb-0">Bảng công tháng</h1>
        <Button
          variant="success" size="sm"
          onClick={handleExport}
          disabled={exporting || !data}
        >
          {exporting ? <Spinner size="sm" className="me-1" /> : '📥'} Xuất Excel
        </Button>
      </div>

      {/* ── Filters ── */}
      <div className="d-flex flex-wrap gap-2 align-items-end mb-3 p-3 rounded"
        style={{ background: 'var(--navy-light, #1a2d42)', border: '1px solid rgba(255,255,255,0.1)' }}>
        <Form.Group>
          <Form.Label className="text-secondary mb-1" style={{ fontSize: '0.8rem' }}>Tháng</Form.Label>
          <Form.Control
            type="month" size="sm"
            value={thang}
            onChange={(e) => setThang(e.target.value)}
            style={{ minWidth: 150 }}
          />
        </Form.Group>
        <Form.Group>
          <Form.Label className="text-secondary mb-1" style={{ fontSize: '0.8rem' }}>Tổ đội</Form.Label>
          <Form.Select
            size="sm" value={toDoi}
            onChange={(e) => setToDoi(e.target.value)}
            style={{ minWidth: 180 }}
          >
            <option value="">— Tất cả —</option>
            {(toDoiData?.ds ?? []).map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </Form.Select>
        </Form.Group>
      </div>

      {/* ── Legend ── */}
      <div className="d-flex gap-3 mb-2 flex-wrap" style={{ fontSize: '0.75rem' }}>
        {[
          { color: '#51cf66', label: 'Bình thường' },
          { color: '#ffd43b', label: 'Ngoài ca' },
          { color: '#f7931e', label: 'Thủ công' },
          { color: '#ff6b6b', label: 'Thiếu giờ ra' },
          { color: '#555',    label: 'Vắng' },
        ].map((l) => (
          <span key={l.label} className="d-flex align-items-center gap-1" style={{ color: '#adb5bd' }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: l.color, display: 'inline-block' }} />
            {l.label}
          </span>
        ))}
      </div>

      {/* ── Matrix table ── */}
      {isLoading ? (
        <div className="text-center py-5"><Spinner animation="border" variant="warning" /></div>
      ) : isError ? (
        <div className="alert alert-danger">Không thể tải bảng công tháng.</div>
      ) : (
        <div style={{ overflowX: 'auto', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}>
          <Table
            size="sm"
            className="mb-0"
            style={{ color: '#dee2e6', minWidth: cacNgay.length * 38 + 260 }}
          >
            <thead style={{ background: 'rgba(0,0,0,0.4)', fontSize: '0.75rem', color: '#adb5bd', position: 'sticky', top: 0, zIndex: 1 }}>
              <tr>
                <th style={{ minWidth: 40, position: 'sticky', left: 0, background: '#0d1b2a', zIndex: 2 }}>STT</th>
                <th style={{ minWidth: 80, position: 'sticky', left: 40, background: '#0d1b2a', zIndex: 2 }}>Mã CN</th>
                <th style={{ minWidth: 140, position: 'sticky', left: 120, background: '#0d1b2a', zIndex: 2 }}>Họ tên</th>
                {cacNgay.map((d) => (
                  <th key={d} style={{ textAlign: 'center', minWidth: 36, padding: '4px 2px' }}>
                    {String(d).padStart(2, '0')}
                  </th>
                ))}
                <th style={{ textAlign: 'center', minWidth: 60 }}>Ngày công</th>
                <th style={{ textAlign: 'center', minWidth: 70 }}>Tổng giờ</th>
                <th style={{ textAlign: 'center', minWidth: 60 }}>Đi muộn</th>
              </tr>
            </thead>
            <tbody>
              {workers.length === 0 ? (
                <tr><td colSpan={cacNgay.length + 6} className="text-center text-muted py-4">Không có dữ liệu.</td></tr>
              ) : workers.map((wk, idx) => (
                <tr key={wk.worker_id ?? idx} style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
                  <td style={{ position: 'sticky', left: 0, background: '#0d1b2a', zIndex: 1, color: '#6c757d', fontSize: '0.8rem' }}>{idx + 1}</td>
                  <td style={{ position: 'sticky', left: 40, background: '#0d1b2a', zIndex: 1, fontFamily: 'monospace', fontSize: '0.8rem' }}>{wk.ma}</td>
                  <td style={{ position: 'sticky', left: 120, background: '#0d1b2a', zIndex: 1, fontWeight: 500, fontSize: '0.82rem', whiteSpace: 'nowrap' }}>{wk.ho_ten}</td>
                  {cacNgay.map((d) => (
                    <DayCell key={d} ngayData={wk.ngay?.[String(d)] ?? wk.ngay?.[d] ?? null} onOpen={(n) => navigate(`/bang-cong?ngay=${n}`)} />
                  ))}
                  <td style={{ textAlign: 'center', fontWeight: 600 }}>{wk.so_ngay_cong}</td>
                  <td style={{ textAlign: 'center', fontWeight: 600, color: 'var(--orange, #f7931e)' }}>
                    {Math.floor(wk.tong_phut / 60)}:{String(wk.tong_phut % 60).padStart(2, '0')}
                  </td>
                  <td style={{ textAlign: 'center', color: wk.so_lan_muon > 0 ? '#ffd43b' : '#adb5bd' }}>{wk.so_lan_muon}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
    </Container>
  )
}
