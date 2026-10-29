import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { STREAM_URL } from '../api/endpoints.js'
import { LiveStream } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents, useWsState } from '../lib/events.js'
import { dongHo } from '../lib/format.js'
import { THIEU_NGAN } from '../lib/labels.js'
import './GateScreen.css'

/**
 * Màn hình cổng (DE_TAI.md mục 5 bước 6). Mở toàn màn hình trên màn hình đặt ở cổng.
 *  - Trái: hình trực tiếp /stream/gate (qua backend; KHÔNG mở thẳng URL DroidCam vì DroidCam chỉ nhận 1 kết nối),
 *    giữ đúng tỉ lệ hình (điện thoại kẹp dọc 720x1280 -> cột hẹp, cao hết màn hình). Lỗi luồng hình -> tự thử lại.
 *  - Phải: ô kết quả lớn. Chờ (đồng hồ + hướng dẫn) -> đang kiểm tra (pha KIEM_TRA) -> kết quả xanh/đỏ/vàng theo `mau`
 *    của sự kiện lượt, trong giay_hien_ket_qua giây -> về chờ.
 *  - Âm thanh: trình duyệt chặn phát tiếng khi người dùng chưa bấm gì -> nút "Bật âm thanh". Đọc `thong_bao` bằng
 *    giọng tiếng Việt (ưu tiên giọng cài sẵn trong máy, không cần mạng); không có giọng -> tiếng bíp
 *    (1 tiếng = xanh, 2 tiếng = đỏ/vàng).
 *  - Mất camera / cổng lỗi / mất kết nối máy chủ -> lớp phủ "tạm gián đoạn"; WebSocket tự kết nối lại (lib/events.js).
 */

const RESULT_ICON = { xanh: '✓', do: '✗', vang: '!' }

/** Câu thông báo trên màn hình: tên đã hiện chữ lớn ở trên nên bỏ "Tên: " ở đầu (giọng đọc vẫn đọc đủ câu). */
function displayMessage(ev) {
  const name = ev.cong_nhan?.ten
  const msg = ev.thong_bao ?? ''
  if (name && msg.startsWith(`${name}: `)) {
    const rest = msg.slice(name.length + 2)
    return rest.charAt(0).toUpperCase() + rest.slice(1)
  }
  return msg
}
const STREAM_RETRY_MS = 2000

// ─── âm thanh ──────────────────────────────────────────────────────────────────
function useSound() {
  const [enabled, setEnabled] = useState(false)
  const [voice, setVoice] = useState(null)
  const ctxRef = useRef(null)
  const voiceRef = useRef(null)

  const pickVoice = useCallback(() => {
    if (!('speechSynthesis' in window)) return
    const vi = window.speechSynthesis.getVoices().filter((v) => (v.lang || '').toLowerCase().startsWith('vi'))
    vi.sort((a, b) => Number(b.localService) - Number(a.localService))   // giọng trong máy trước (không cần mạng)
    voiceRef.current = vi[0] ?? null
    setVoice(vi[0] ?? null)
  }, [])

  const beep = useCallback((n) => {
    const ctx = ctxRef.current
    if (!ctx) return
    for (let i = 0; i < n; i++) {
      const t = ctx.currentTime + i * 0.3
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.frequency.value = n === 1 ? 880 : 440
      gain.gain.setValueAtTime(0.25, t)
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.22)
      osc.connect(gain).connect(ctx.destination)
      osc.start(t)
      osc.stop(t + 0.23)
    }
  }, [])

  const enable = useCallback(() => {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (Ctx && !ctxRef.current) ctxRef.current = new Ctx()
    ctxRef.current?.resume()
    if ('speechSynthesis' in window) {
      pickVoice()
      window.speechSynthesis.onvoiceschanged = pickVoice   // danh sách giọng tải chậm
    }
    setEnabled(true)
    beep(1)
  }, [beep, pickVoice])

  const announce = useCallback((ev) => {
    if (!enabled) return
    const beeps = ev.mau === 'xanh' ? 1 : 2
    const v = voiceRef.current
    if (!v || !ev.thong_bao) { beep(beeps); return }
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(ev.thong_bao)
    u.voice = v
    u.lang = v.lang
    u.onerror = () => beep(beeps)                 // vd giọng trực tuyến nhưng mất mạng
    window.speechSynthesis.speak(u)
  }, [enabled, beep])

  useEffect(() => () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      window.speechSynthesis.onvoiceschanged = null
    }
    ctxRef.current?.close()
  }, [])

  const info = !enabled ? 'Âm thanh đang tắt (trình duyệt cần bấm nút trước khi phát).'
    : voice ? `Giọng đọc: ${voice.name}${voice.localService ? ' (có sẵn trong máy)' : ' (trực tuyến, cần mạng)'}`
      : 'Máy không có giọng tiếng Việt → phát tiếng bíp (1 tiếng: đạt, 2 tiếng: không đạt hoặc cần làm lại)'
  return { enabled, enable, announce, info }
}

// ─── hình camera ───────────────────────────────────────────────────────────────
function GateStream({ status }) {
  const imgRef = useRef(null)
  const [src, setSrc] = useState(STREAM_URL)
  const [ratio, setRatio] = useState(null)      // rộng / cao của hình thật
  const retryRef = useRef(null)

  // Luồng MJPEG: trình duyệt không phải lúc nào cũng báo "load" -> đọc kích thước định kỳ (đổi góc xoay cũng tự chỉnh)
  useEffect(() => {
    const t = setInterval(() => {
      const im = imgRef.current
      if (im?.naturalWidth) setRatio(im.naturalWidth / im.naturalHeight)
    }, 1000)
    return () => { clearInterval(t); clearTimeout(retryRef.current) }
  }, [])

  const onError = () => {
    clearTimeout(retryRef.current)
    retryRef.current = setTimeout(() => setSrc(`${STREAM_URL}?t=${Date.now()}`), STREAM_RETRY_MS)
  }

  return (
    <div className="gate-cam" style={ratio ? { aspectRatio: String(ratio) } : { width: '40vw' }}>
      <LiveStream ref={imgRef} src={src} alt="Hình trực tiếp camera cổng" onError={onError} />
      {!ratio && <div className="gate-cam__wait" style={{ position: 'absolute' }}>Đang chờ hình từ camera…</div>}
      {status?.do_phan_giai && (
        <div className="gate-cam__tag">{status.do_phan_giai.replace('x', '×')}{status.khung_giay != null ? ` · ${status.khung_giay} khung/giây` : ''}</div>
      )}
    </div>
  )
}

function useClock(tz) {
  const [now, setNow] = useState(() => dongHo(tz))
  useEffect(() => {
    setNow(dongHo(tz))
    const t = setInterval(() => setNow(dongHo(tz)), 1000)
    return () => clearInterval(t)
  }, [tz])
  return now
}

function gateChip(status, wsState) {
  if (wsState === 'mat') return ['err', 'Mất kết nối máy chủ']
  if (wsState !== 'mo' || !status) return ['warn', 'Đang kết nối…']
  if (status.mat_camera) return ['err', 'Mất kết nối camera']
  if (status.trang_thai === 'dang_khoi_dong') return ['warn', 'Đang khởi động']
  if (status.trang_thai === 'dang_chay' && !status.loi) return ['ok', status.pha === 'KIEM_TRA' ? 'Đang kiểm tra' : 'Đang chạy']
  if (status.trang_thai === 'tat') return ['err', 'Cổng đang tắt']
  return ['err', 'Cổng lỗi']
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function GateScreen() {
  const cfg = useWebConfig()
  const wsState = useWsState()
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const [recent, setRecent] = useState([])
  const timerRef = useRef(null)
  const sound = useSound()
  const clock = useClock(cfg.tz)

  useGateEvents((ev) => {
    if (ev.loai === 'trang_thai') setStatus(ev)
    if (ev.loai === 'luot') {
      setResult(ev)
      setRecent((r) => [ev, ...r].slice(0, 4))
      sound.announce(ev)
      clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setResult(null), cfg.resultSeconds * 1000)
    }
  })
  useEffect(() => () => clearTimeout(timerRef.current), [])

  const toggleFullscreen = () => {
    if (document.fullscreenElement) document.exitFullscreen()
    else document.documentElement.requestFullscreen().catch(() => {})
  }

  // Lớp phủ gián đoạn (không che khi cổng chỉ đang khởi động)
  let overlay = null
  if (wsState === 'mat') {
    overlay = { camera: false, title: 'Hệ thống kiểm tra tạm gián đoạn', sub: 'Vui lòng gặp cán bộ',
                detail: 'Mất kết nối tới máy chủ, đang thử kết nối lại…' }
  } else if (status?.mat_camera) {
    overlay = { camera: true, title: 'Mất kết nối camera, đang thử lại',
                sub: 'Kiểm tra điện thoại: mở ứng dụng camera, bật màn hình, cùng wifi', detail: '' }
  } else if (status && (status.trang_thai === 'loi' || status.trang_thai === 'tat' || (status.trang_thai === 'dang_chay' && status.loi))) {
    overlay = { camera: false, title: 'Hệ thống kiểm tra tạm gián đoạn', sub: 'Vui lòng gặp cán bộ',
                detail: status.trang_thai === 'tat' ? 'Cổng đang tắt' : status.loi }
  }

  const checking = !result && status?.trang_thai === 'dang_chay' && status.pha === 'KIEM_TRA'
  const starting = !result && status?.trang_thai === 'dang_khoi_dong'
  const boxClass = result ? `gate-result--${result.mau}` : checking ? 'gate-result--kiem-tra' : 'gate-result--cho'
  const [chipKind, chipText] = gateChip(status, wsState)

  return (
    <div className="gate-screen">
      <GateStream status={status} />

      <div className="gate-side">
        <div className="gate-top">
          <div className="gate-brand"><img src="/favicon.svg" alt="" />SafeGate</div>
          <span className={`gate-chip gate-chip--${chipKind}`}><span className="gate-chip__dot" />{chipText}</span>
          <button className={`gate-btn ${sound.enabled ? 'gate-btn--sound-on' : 'gate-btn--sound'}`} onClick={sound.enable}>
            {sound.enabled ? '🔊 Âm thanh đang bật' : '🔊 Bật âm thanh'}
          </button>
          <button className="gate-btn" onClick={toggleFullscreen}>⛶ Toàn màn hình</button>
          <Link className="gate-btn" to="/">← Quản lý</Link>
        </div>
        <div className="gate-voice">{sound.info}</div>

        <div className={`gate-result ${boxClass}`}>
          {result ? (
            <div className="gate-result__anim" key={result.id}>
              <div className="gate-icon">{RESULT_ICON[result.mau] ?? '!'}</div>
              <div className="gate-name">{result.cong_nhan?.ten ?? result.thong_bao}</div>
              {result.cong_nhan?.ma && <div className="gate-code">Mã {result.cong_nhan.ma}</div>}
              {result.cong_nhan && <div className="gate-msg">{displayMessage(result)}</div>}
              {result.thieu?.length > 0 && (
                <div className="gate-missing">{result.thieu.map((t) => <span key={t}>{THIEU_NGAN[t] ?? t}</span>)}</div>
              )}
              <div className="gate-time">
                {result.gio}
                {result.huong ? ` · ${result.huong === 'vao' ? 'Vào' : 'Ra'}` : ''}
              </div>
              {result.anh && <img className="gate-photo" src={result.anh} alt="Ảnh lượt kiểm tra" />}
            </div>
          ) : checking ? (
            <div className="gate-result__anim" key="kiem-tra">
              <div className="gate-spinner" />
              <div className="gate-name">Đang kiểm tra…</div>
              <div className="gate-msg">Mời đứng yên, nhìn thẳng camera</div>
            </div>
          ) : (
            <div className="gate-result__anim" key="cho">
              <div className="gate-clock">{clock.gio}</div>
              <div className="gate-date">{clock.ngay}</div>
              <div className="gate-guide">{starting ? 'Đang khởi động camera…' : 'Mời đứng vào vị trí, nhìn vào camera'}</div>
              <div className="gate-steps">
                <span>⛑ Đội mũ bảo hộ</span><span>🦺 Mặc áo phản quang</span><span>🧍 Đứng yên 2 giây</span>
              </div>
            </div>
          )}
        </div>

        {recent.length > 0 && (
          <div className="gate-recent">
            {recent.map((r) => (
              <div key={r.id} className={`gate-recent__item gate-recent__item--${r.mau}`}>
                <span>{r.gio}</span><b>{r.cong_nhan?.ten ?? 'Chưa nhận ra'}</b>
              </div>
            ))}
          </div>
        )}
      </div>

      {overlay && (
        <div className={`gate-overlay${overlay.camera ? ' gate-overlay--camera' : ''}`}>
          <div className="gate-overlay__icon">{overlay.camera ? '📷' : '⛔'}</div>
          <div className="gate-overlay__title">{overlay.title}</div>
          <div className="gate-overlay__sub">{overlay.sub}</div>
          {overlay.detail && <div className="gate-overlay__detail">{overlay.detail}</div>}
          <Link className="gate-btn" to="/">← Quản lý</Link>
        </div>
      )}
    </div>
  )
}
