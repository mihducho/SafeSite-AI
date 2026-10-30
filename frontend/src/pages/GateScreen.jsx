import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft, Camera, CameraOff, Check, Expand, HardHat, Minimize, PersonStanding, ServerCrash, Shirt, TriangleAlert,
  Volume2, VolumeX, X,
} from 'lucide-react'
import { STREAM_URL } from '../api/endpoints.js'
import { LogoMark } from '../components/common/Logo.jsx'
import { LiveStream } from '../components/common/ui.jsx'
import { useWebConfig } from '../hooks/useWebConfig.js'
import { useGateEvents, useWsState } from '../lib/events.js'
import { dongHo } from '../lib/format.js'
import { THIEU_NGAN, trangThaiCong } from '../lib/labels.js'
import './GateScreen.css'

/**
 * Màn hình cổng (DE_TAI.md mục 5 bước 6). Mở toàn màn hình trên màn hình đặt ở cổng, nền tối.
 *  - Trái: hình trực tiếp /stream/gate (qua backend; KHÔNG mở thẳng URL DroidCam vì DroidCam chỉ nhận 1 kết nối),
 *    giữ đúng tỉ lệ hình (điện thoại kẹp dọc 720x1280 -> cột hẹp, cao hết màn hình). Lỗi luồng hình -> tự thử lại.
 *  - Phải: ô kết quả lớn. Chờ (đồng hồ + hướng dẫn) -> đang kiểm tra (pha KIEM_TRA) -> kết quả xanh/đỏ/vàng theo `mau`
 *    của sự kiện lượt, trong giay_hien_ket_qua giây -> về chờ.
 *  - Loa luôn bật (useSound): tự bật khi trình duyệt cho phép (mở bằng cong.bat); bị chặn thì chạm màn hình một lần.
 *    Đọc `thong_bao` bằng giọng tiếng Việt (ưu tiên giọng cài sẵn trong máy, không cần mạng); không có giọng -> tiếng
 *    bíp (1 tiếng = xanh, 2 tiếng = đỏ/vàng).
 *  - Mất camera / cổng lỗi / mất kết nối máy chủ -> ô đỏ "tạm gián đoạn"; WebSocket tự kết nối lại (lib/events.js).
 */

const RESULT_ICON = { xanh: Check, do: X, vang: TriangleAlert }
const MISSING_ICON = { thieu_mu: HardHat, thieu_ao: Shirt }

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

// ─── âm thanh: loa LUÔN BẬT ────────────────────────────────────────────────────
// Trình duyệt chỉ cho phát tiếng (giọng đọc, tiếng bíp) khi người dùng đã bấm vào trang, TRỪ KHI được phép tự phát:
//  - mở bằng cong.bat (Edge kiosk, tham số --autoplay-policy=no-user-gesture-required), hoặc
//  - trong Edge đặt "Tự động phát nội dung đa phương tiện: Cho phép" cho địa chỉ ứng dụng.
// Khi đó trang tự bật loa ngay lúc mở. Nếu vẫn bị chặn: chạm / bấm phím BẤT KỲ đâu trên màn hình một lần là bật.
// Không có nút tắt loa.
function useSound() {
  const [state, setState] = useState('dang_bat')   // dang_bat | bat | bi_chan
  const [voice, setVoice] = useState(null)
  const ctxRef = useRef(null)
  const voiceRef = useRef(null)
  const stateRef = useRef('dang_bat')
  stateRef.current = state

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
    ctx.resume()
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

  // Bật loa: được gọi lúc mở trang (thử tự bật) và ở lần chạm / bấm phím đầu tiên (nếu trình duyệt chặn).
  const unlock = useCallback((fromUser) => {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (Ctx && !ctxRef.current) {
      const c = new Ctx()
      // resume() chạy bất đồng bộ: loa chỉ bật thật khi AudioContext chuyển sang 'running'
      c.onstatechange = () => {
        if (c.state !== 'running' || stateRef.current === 'bat') return
        if (stateRef.current === 'bi_chan') beep(1)                // vừa chạm để bật: bíp một tiếng xác nhận
        setState('bat')
      }
      ctxRef.current = c
    }
    const ctx = ctxRef.current
    if (!ctx || ctx.state === 'running') { setState('bat'); return }   // không có Web Audio: vẫn thử giọng đọc
    ctx.resume().catch(() => {})
    // Không có thao tác của người dùng thì resume() bị treo nếu trình duyệt chặn -> xem trạng thái sau một lát
    if (!fromUser) setTimeout(() => { if (ctx.state !== 'running') setState('bi_chan') }, 400)
  }, [beep])

  useEffect(() => {
    if ('speechSynthesis' in window) {
      pickVoice()
      window.speechSynthesis.onvoiceschanged = pickVoice        // danh sách giọng tải chậm
    }
    unlock(false)
    // Bị chặn: lần chạm / bấm phím đầu tiên ở bất kỳ đâu sẽ bật loa (bắt ở pha capture, trước mọi nút khác)
    const onUser = () => unlock(true)
    const events = ['pointerdown', 'keydown', 'touchstart']
    events.forEach((e) => document.addEventListener(e, onUser, { capture: true }))
    return () => {
      events.forEach((e) => document.removeEventListener(e, onUser, { capture: true }))
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel()
        window.speechSynthesis.onvoiceschanged = null
      }
      ctxRef.current?.close()
      ctxRef.current = null
    }
  }, [pickVoice, unlock])

  const announce = useCallback((ev) => {
    const beeps = ev.mau === 'xanh' ? 1 : 2
    const v = voiceRef.current
    if (!v || !ev.thong_bao || !('speechSynthesis' in window)) { beep(beeps); return }
    const synth = window.speechSynthesis
    synth.cancel()
    synth.resume()                                   // Chrome / Edge đôi khi tự tạm dừng hàng đợi đọc sau lâu không dùng
    const u = new SpeechSynthesisUtterance(ev.thong_bao)
    u.voice = v
    u.lang = v.lang
    u.onerror = (e) => {
      if (e.error === 'not-allowed') setState('bi_chan')         // trình duyệt chặn: hiện hướng dẫn chạm màn hình
      if (e.error !== 'interrupted' && e.error !== 'canceled') beep(beeps)   // vd giọng trực tuyến nhưng mất mạng
    }
    synth.speak(u)
  }, [beep])

  const info = state === 'bi_chan'
    ? 'Trình duyệt đang chặn âm thanh: chạm vào màn hình một lần để bật loa (mở bằng cong.bat thì loa tự bật).'
    : voice ? `Loa luôn bật · giọng đọc ${voice.name}${voice.localService ? ' (có sẵn trong máy)' : ' (trực tuyến, cần mạng)'}`
      : 'Loa luôn bật · máy không có giọng tiếng Việt nên phát tiếng bíp (1 tiếng: đạt, 2 tiếng: không đạt hoặc cần làm lại)'
  return { state, announce, info }
}

// ─── hình camera ───────────────────────────────────────────────────────────────
function GateStream({ status }) {
  const imgRef = useRef(null)
  const [src, setSrc] = useState(STREAM_URL)
  const [ratio, setRatio] = useState(null)      // rộng / cao của hình thật
  const retryRef = useRef(null)
  const lostRef = useRef(false)   // mất camera: backend gửi ảnh báo lỗi nằm ngang -> giữ tỉ lệ khung dọc cũ
  lostRef.current = !!status?.mat_camera

  // Luồng MJPEG: trình duyệt không phải lúc nào cũng báo "load" -> đọc kích thước định kỳ (đổi góc xoay cũng tự chỉnh)
  useEffect(() => {
    const t = setInterval(() => {
      const im = imgRef.current
      if (im?.naturalWidth && !lostRef.current) setRatio(im.naturalWidth / im.naturalHeight)
    }, 1000)
    return () => { clearInterval(t); clearTimeout(retryRef.current) }
  }, [])

  const onError = () => {
    clearTimeout(retryRef.current)
    retryRef.current = setTimeout(() => setSrc(`${STREAM_URL}?t=${Date.now()}`), STREAM_RETRY_MS)
  }

  return (
    <div className="gs-cam" style={ratio ? { aspectRatio: String(ratio) } : { width: '34vw' }}>
      <LiveStream ref={imgRef} src={src} alt="Hình trực tiếp camera cổng" onError={onError} />
      {!ratio && <div className="gs-cam__wait"><Camera size={36} />Đang chờ hình từ camera…</div>}
      {status?.do_phan_giai && (
        <div className="gs-cam__tag">{status.do_phan_giai.replace('x', '×')}{status.khung_giay != null ? ` · ${status.khung_giay} khung/giây` : ''}</div>
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

/** Hình minh hoạ: người đứng trong khung, đội mũ bảo hộ */
function StandIllustration() {
  return (
    <svg className="gs-illus" viewBox="0 0 200 220" fill="none" aria-hidden="true">
      <rect x="40" y="8" width="120" height="196" rx="16" stroke="#334155" strokeWidth="4" strokeDasharray="10 8" />
      <ellipse cx="100" cy="196" rx="44" ry="8" fill="#1E293B" />
      <path d="M78 52a22 22 0 0 1 44 0z" fill="#F59E0B" />
      <rect x="72" y="50" width="56" height="7" rx="3.5" fill="#FCD34D" />
      <circle cx="100" cy="72" r="16" fill="#CBD5E1" />
      <path d="M70 120c0-17 13-28 30-28s30 11 30 28v26H70z" fill="#F59E0B" />
      <path d="M80 104h40M78 120h44" stroke="#E2E8F0" strokeWidth="5" strokeLinecap="round" />
      <rect x="78" y="146" width="16" height="44" rx="6" fill="#64748B" />
      <rect x="106" y="146" width="16" height="44" rx="6" fill="#64748B" />
    </svg>
  )
}

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function GateScreen() {
  const cfg = useWebConfig()
  const wsState = useWsState()
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const [full, setFull] = useState(!!document.fullscreenElement)
  const timerRef = useRef(null)
  const sound = useSound()
  const clock = useClock(cfg.tz)

  useGateEvents((ev) => {
    if (ev.loai === 'trang_thai') setStatus(ev)
    if (ev.loai === 'luot') {
      setResult(ev)
      sound.announce(ev)
      clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setResult(null), cfg.resultSeconds * 1000)
    }
  })
  useEffect(() => () => clearTimeout(timerRef.current), [])
  useEffect(() => {
    const on = () => setFull(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', on)
    return () => document.removeEventListener('fullscreenchange', on)
  }, [])

  const toggleFullscreen = () => {
    if (document.fullscreenElement) document.exitFullscreen()
    else document.documentElement.requestFullscreen().catch(() => {})
  }

  // Gián đoạn -> ô đỏ (không tính lúc cổng chỉ đang khởi động)
  let down = null
  if (wsState === 'mat') {
    down = { icon: ServerCrash, title: 'Hệ thống kiểm tra tạm gián đoạn', sub: 'Vui lòng gặp cán bộ',
             detail: 'Mất kết nối tới máy chủ, đang thử kết nối lại…' }
  } else if (status?.mat_camera) {
    down = { icon: CameraOff, title: 'Mất kết nối camera, đang thử lại',
             sub: 'Kiểm tra điện thoại: mở ứng dụng camera, bật màn hình, cùng wifi', detail: '' }
  } else if (status && (status.trang_thai === 'loi' || status.trang_thai === 'tat' || (status.trang_thai === 'dang_chay' && status.loi))) {
    down = { icon: TriangleAlert, title: 'Hệ thống kiểm tra tạm gián đoạn', sub: 'Vui lòng gặp cán bộ',
             detail: status.trang_thai === 'tat' ? 'Cổng đang tắt' : '' }
  }

  const checking = !result && status?.trang_thai === 'dang_chay' && status.pha === 'KIEM_TRA'
  const starting = !result && status?.trang_thai === 'dang_khoi_dong'
  const boxClass = down ? 'do' : result ? result.mau : checking ? 'kiem-tra' : ''
  const [statusText, , statusTone] = trangThaiCong(status, wsState)
  const ResultIcon = result ? RESULT_ICON[result.mau] ?? TriangleAlert : null
  const DownIcon = down?.icon

  return (
    <div className="gs">
      <GateStream status={status} />

      <div className="gs-side">
        <div className="gs-top">
          <span className="gs-brand"><LogoMark size={34} />SafeGate</span>
          <span className={`gs-status ${statusTone}`}><i />{statusText}</span>
          {sound.state === 'bi_chan'
            ? <button className="gs-btn attention"><VolumeX size={17} />Chạm để bật loa</button>
            : <span className="gs-btn on" title="Loa luôn bật"><Volume2 size={17} />Loa đang bật</span>}
          <button className="gs-btn icon" onClick={toggleFullscreen} title={full ? 'Thoát toàn màn hình' : 'Toàn màn hình'}
            aria-label="Toàn màn hình">
            {full ? <Minimize size={17} /> : <Expand size={17} />}
          </button>
          <Link className="gs-btn icon" to="/" title="Về trang quản lý" aria-label="Về trang quản lý"><ArrowLeft size={17} /></Link>
        </div>
        <div className="gs-voice">{sound.info}</div>

        {sound.state === 'bi_chan' && (
          <div role="alert" style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '14px 18px', borderRadius: 6,
            background: '#D97706', color: '#FFFFFF', fontSize: 24, fontWeight: 700, cursor: 'pointer',
          }}>
            <VolumeX size={28} />Chạm vào màn hình một lần để bật loa
          </div>
        )}
        <div className={`gs-box ${boxClass}`}>
          {down ? (
            <div className="gs-in" key={`down-${down.title}`}>
              <div className="gs-icon"><DownIcon /></div>
              <div className="gs-title">{down.title}</div>
              <div className="gs-sub">{down.sub}</div>
              {down.detail && <div className="gs-detail">{down.detail}</div>}
            </div>
          ) : result ? (
            <div className="gs-in" key={result.id}>
              <div className="gs-icon"><ResultIcon strokeWidth={3} /></div>
              <div className="gs-name">{result.cong_nhan?.ten ?? result.thong_bao}</div>
              {result.cong_nhan?.ma && <div className="gs-code">Mã {result.cong_nhan.ma}</div>}
              {result.cong_nhan && <div className="gs-msg">{displayMessage(result)}</div>}
              {result.thieu?.length > 0 && (
                <div className="gs-missing">
                  {result.thieu.map((t) => {
                    const Icon = MISSING_ICON[t] ?? TriangleAlert
                    return <span key={t}><Icon size={22} />{THIEU_NGAN[t] ?? t}</span>
                  })}
                </div>
              )}
              <div className="gs-meta">
                {result.anh && <img className="gs-photo" src={result.anh} alt="Ảnh lượt kiểm tra" />}
                <span>{result.gio}{result.huong ? ` · ${result.huong === 'vao' ? 'Vào' : 'Ra'}` : ''}</span>
              </div>
            </div>
          ) : checking ? (
            <div className="gs-in" key="kiem-tra">
              <div className="gs-spinner" />
              <div className="gs-title">Đang kiểm tra…</div>
              <div className="gs-sub">Mời đứng yên, nhìn thẳng camera</div>
            </div>
          ) : (
            <div className="gs-in" key="cho">
              <StandIllustration />
              <div className="gs-clock">{clock.gio}</div>
              <div className="gs-date">{clock.ngay}</div>
              <div className="gs-guide">{starting ? 'Đang khởi động camera…' : 'Mời đứng vào vị trí, nhìn vào camera'}</div>
              <div className="gs-steps">
                <span><HardHat size={20} />Đội mũ bảo hộ</span>
                <span><Shirt size={20} />Mặc áo phản quang</span>
                <span><PersonStanding size={20} />Đứng yên 2 giây</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
