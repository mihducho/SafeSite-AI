import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity, ArrowLeft, Camera, CameraOff, Check, Expand, HardHat, Minimize, PersonStanding, ScanLine, ServerCrash,
  ShieldCheck, Shirt, TriangleAlert, Volume2, VolumeX, X,
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
 * Màn hình cổng (DE_TAI.md mục 5 bước 6). Mở toàn màn hình trên màn hình đặt ở cổng, nền tối (#09090B).
 *  - Trái (50%): khung ngắm kỹ thuật (recessed viewport) chứa luồng trực tiếp /stream/gate tỉ lệ 9:16.
 *  - Phải (50%): 3 thẻ kỹ thuật (Đồng hồ số Terminal · Khung trạng thái kiểm tra & danh sách 3 điều kiện bảo hộ · Hoạt động cổng gần nhất).
 *  - Loa luôn bật (useSound): tự bật khi trình duyệt cho phép (mở bằng cong.bat); bị chặn thì chạm màn hình một lần.
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

// ─── hình camera (Cột trái 50%: khung ngắm kỹ thuật + viền góc + HUD LIVE) ────
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

  const resText = status?.do_phan_giai ? status.do_phan_giai.replace('x', '×') : '720×1280'
  const fpsText = status?.khung_giay != null ? `${status.khung_giay} FPS` : '30 FPS'

  return (
    <div className="gs-viewport">
      <span className="gs-vp-corner gs-vp-corner--tl" aria-hidden="true" />
      <span className="gs-vp-corner gs-vp-corner--tr" aria-hidden="true" />
      <span className="gs-vp-corner gs-vp-corner--bl" aria-hidden="true" />
      <span className="gs-vp-corner gs-vp-corner--br" aria-hidden="true" />

      <div className="gs-cam__tag">
        <i className={`gs-cam__dot${status?.mat_camera ? ' off' : ''}`} aria-hidden="true" />
        <span>LIVE // {resText} · {fpsText}</span>
      </div>

      <div className="gs-cam" style={{ aspectRatio: ratio ? String(ratio) : '9 / 16' }}>
        <LiveStream ref={imgRef} src={src} alt="Hình trực tiếp camera cổng" onError={onError} />
        {!ratio && <div className="gs-cam__wait"><Camera size={28} strokeWidth={1.5} />Đang chờ hình từ camera…</div>}
      </div>
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

// ─── trang ─────────────────────────────────────────────────────────────────────
export default function GateScreen() {
  const cfg = useWebConfig()
  const wsState = useWsState()
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const [lastEvent, setLastEvent] = useState(null)
  const [full, setFull] = useState(!!document.fullscreenElement)
  const timerRef = useRef(null)
  const sound = useSound()
  const clock = useClock(cfg.tz)

  useGateEvents((ev) => {
    if (ev.loai === 'trang_thai') setStatus(ev)
    if (ev.loai === 'luot') {
      setResult(ev)
      setLastEvent(ev)
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
  const [statusText, statusLong, statusTone] = trangThaiCong(status, wsState)
  const ResultIcon = result ? RESULT_ICON[result.mau] ?? TriangleAlert : null
  const DownIcon = down?.icon
  const recent = result ?? lastEvent

  return (
    <div className="gs">
      <GateStream status={status} />

      <div className="gs-side">
        <div className="gs-top">
          <span className="gs-brand"><LogoMark size={30} />SafeGate</span>
          <span className={`gs-status ${statusTone}`} title={statusLong}><i />{statusText}</span>
          {sound.state === 'bi_chan'
            ? <button className="gs-btn attention" title={sound.info}><VolumeX size={16} strokeWidth={1.5} />Chạm để bật loa</button>
            : <span className="gs-btn on" title={sound.info}><Volume2 size={16} strokeWidth={1.5} />Loa đang bật</span>}
          <button className="gs-btn icon" onClick={toggleFullscreen} title={full ? 'Thoát toàn màn hình' : 'Toàn màn hình'}
            aria-label="Toàn màn hình">
            {full ? <Minimize size={16} strokeWidth={1.5} /> : <Expand size={16} strokeWidth={1.5} />}
          </button>
          <Link className="gs-btn icon" to="/" title="Về trang quản lý" aria-label="Về trang quản lý"><ArrowLeft size={16} strokeWidth={1.5} /></Link>
        </div>

        {sound.state === 'bi_chan' && (
          <div role="alert" className="gs-sound-alert">
            <VolumeX size={22} strokeWidth={1.75} />Chạm vào màn hình một lần để bật loa
          </div>
        )}

        {/* Thẻ A: Đồng hồ số Terminal */}
        <section className="gs-card gs-clock-card" aria-label="Thời gian hệ thống">
          <div className="gs-clock-card__main">
            <div className="gs-clock">{clock.gio}</div>
            <div className="gs-date">{clock.ngay}</div>
          </div>
          <div className="gs-clock-card__meta">
            <span className="gs-kicker">TERMINAL // GATE-01</span>
            <span className={`gs-ready-tag ${statusTone}`}>
              <i />{statusText}
            </span>
          </div>
        </section>

        {/* Thẻ B: Khung trạng thái xác thực & Danh sách kiểm tra bảo hộ */}
        <section className={`gs-card gs-box ${boxClass}`} aria-live="polite">
          {down ? (
            <div className="gs-in" key={`down-${down.title}`}>
              <div className="gs-icon"><DownIcon strokeWidth={1.75} /></div>
              <div className="gs-title">{down.title}</div>
              <div className="gs-sub">{down.sub}</div>
              {down.detail && <div className="gs-detail">{down.detail}</div>}
            </div>
          ) : result ? (
            <div className="gs-in" key={result.id}>
              <div className="gs-icon"><ResultIcon strokeWidth={2.5} /></div>
              <div className="gs-name">{result.cong_nhan?.ten ?? result.thong_bao}</div>
              {result.cong_nhan?.ma && <div className="gs-code">Mã {result.cong_nhan.ma}</div>}
              {result.cong_nhan && <div className="gs-msg">{displayMessage(result)}</div>}
              {result.thieu?.length > 0 && (
                <div className="gs-missing">
                  {result.thieu.map((t) => {
                    const Icon = MISSING_ICON[t] ?? TriangleAlert
                    return <span key={t}><Icon size={20} strokeWidth={1.75} />{THIEU_NGAN[t] ?? t}</span>
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
            <div className="gs-in gs-in--idle" key="cho">
              <div className="gs-scanner-bar">
                <ScanLine size={18} strokeWidth={1.75} className="gs-scanner-bar__icon" />
                <span>{starting ? 'HỆ THỐNG ĐANG KHỞI ĐỘNG CAMERA' : 'TRẠNG THÁI QUÉT // SẴN SÀNG NHẬN DIỆN'}</span>
                <i className="gs-scanner-bar__pulse" />
              </div>

              <div className="gs-guide">{starting ? 'Đang khởi động camera…' : 'Mời đứng vào vị trí, nhìn vào camera'}</div>

              <div className="gs-steps" role="list" aria-label="Yêu cầu kiểm tra tại cổng">
                <div className="gs-step-row" role="listitem">
                  <span className="gs-step-row__idx">01</span>
                  <HardHat size={18} strokeWidth={1.5} className="gs-step-row__icon" />
                  <span className="gs-step-row__label">Đội mũ bảo hộ</span>
                  <span className="gs-step-row__badge"><i />BẮT BUỘC</span>
                </div>
                <div className="gs-step-row" role="listitem">
                  <span className="gs-step-row__idx">02</span>
                  <Shirt size={18} strokeWidth={1.5} className="gs-step-row__icon" />
                  <span className="gs-step-row__label">Mặc áo phản quang</span>
                  <span className="gs-step-row__badge"><i />BẮT BUỘC</span>
                </div>
                <div className="gs-step-row" role="listitem">
                  <span className="gs-step-row__idx">03</span>
                  <PersonStanding size={18} strokeWidth={1.5} className="gs-step-row__icon" />
                  <span className="gs-step-row__label">Đứng yên 2 giây</span>
                  <span className="gs-step-row__badge"><i />XÁC THỰC</span>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Thẻ C: Hoạt động cổng gần nhất / Trạng thái sẵn sàng */}
        <section className="gs-card gs-recent-card" aria-label="Hoạt động cổng gần nhất">
          <div className="gs-recent-card__head">
            <span className="gs-recent-card__title">
              <Activity size={15} strokeWidth={1.5} />
              HOẠT ĐỘNG CỔNG GẦN NHẤT
            </span>
            <span className="gs-recent-card__count">
              Đã xử lý: <b>{status?.so_luot ?? 0}</b> lượt
            </span>
          </div>
          {recent ? (
            <div className="gs-recent-card__body">
              {recent.anh && <img className="gs-recent-card__thumb" src={recent.anh} alt="" />}
              <div className="gs-recent-card__info">
                <div className="gs-recent-card__name">
                  {recent.cong_nhan?.ten ?? recent.thong_bao}
                  {recent.cong_nhan?.ma && <span className="gs-recent-card__code">{recent.cong_nhan.ma}</span>}
                </div>
                <div className="gs-recent-card__sub">
                  {displayMessage(recent)}
                </div>
              </div>
              <div className={`gs-recent-card__pill ${recent.mau ?? 'neutral'}`}>
                <i />{recent.gio}{recent.huong ? ` · ${recent.huong === 'vao' ? 'Vào' : 'Ra'}` : ''}
              </div>
            </div>
          ) : (
            <div className="gs-recent-card__empty">
              <ShieldCheck size={16} strokeWidth={1.5} />
              <span>{statusLong || 'Cổng kiểm soát sẵn sàng · Chờ công nhân bước vào vùng nhận diện.'}</span>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
