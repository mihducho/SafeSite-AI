import { useEffect, useRef, useState } from 'react'
import store from '../store/index.js'
import { clearUser } from '../store/authSlice.js'

/**
 * Một kết nối WebSocket /ws/events dùng chung cho cả tab (DE_TAI.md mục 8):
 *  - {loai:"luot", ...}        mỗi lượt kiểm tra xong (mau, thong_bao, cong_nhan, anh...)
 *  - {loai:"trang_thai", ...}  trạng thái cổng (trang_thai, pha, loi, mat_camera, khung_giay...)
 *  - {loai:"mat_ket_noi"}      do chính module này phát khi mất kết nối tới máy chủ
 * Mất kết nối -> tự kết nối lại sau 2 giây. Mã đóng 1008 = chưa đăng nhập -> về trang đăng nhập.
 * Chỉ mở kết nối khi có component đang nghe; component cuối cùng thôi nghe thì đóng.
 */
const RECONNECT_MS = 2000

let socket = null
let timer = null
let lastStatus = null
let wsState = 'dong'                   // dong | dang_ket_noi | mo | mat
const listeners = new Set()
const stateListeners = new Set()

function setWsState(s) {
  wsState = s
  stateListeners.forEach((fn) => fn(s))
}

function emit(ev) {
  listeners.forEach((fn) => {
    try { fn(ev) } catch (err) { console.error(err) }
  })
}

function connect() {
  clearTimeout(timer)
  timer = null
  if (!listeners.size) return
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const sock = new WebSocket(`${proto}://${window.location.host}/ws/events`)
  socket = sock
  setWsState('dang_ket_noi')
  sock.onopen = () => { if (socket === sock) setWsState('mo') }
  sock.onmessage = (e) => {
    if (socket !== sock) return
    let ev
    try { ev = JSON.parse(e.data) } catch { return }
    if (ev.loai === 'trang_thai') lastStatus = ev
    emit(ev)
  }
  sock.onclose = (e) => {
    if (socket !== sock) return       // kết nối cũ đã bị thay (vd component gắn lại): bỏ qua
    socket = null
    if (e.code === 1008) {             // hết phiên đăng nhập
      setWsState('dong')
      store.dispatch(clearUser())
      return
    }
    setWsState('mat')
    emit({ loai: 'mat_ket_noi' })
    if (listeners.size) timer = setTimeout(connect, RECONNECT_MS)
  }
}

function subscribe(fn) {
  listeners.add(fn)
  if (!socket && !timer) connect()
  if (lastStatus && wsState === 'mo') fn(lastStatus)  // trạng thái hiện tại cho component mới gắn
  return () => {
    listeners.delete(fn)
    if (!listeners.size) {
      clearTimeout(timer)
      timer = null
      const s = socket
      socket = null
      s?.close()
      setWsState('dong')
    }
  }
}

/** Nhận mọi sự kiện WebSocket. handler luôn là bản mới nhất (không cần useCallback). */
export function useGateEvents(handler) {
  const ref = useRef(handler)
  ref.current = handler
  useEffect(() => subscribe((ev) => ref.current(ev)), [])
}

/** Trạng thái cổng mới nhất (sự kiện trang_thai), null khi chưa nhận được. */
export function useGateStatus() {
  const [status, setStatus] = useState(wsState === 'mo' ? lastStatus : null)
  useGateEvents((ev) => { if (ev.loai === 'trang_thai') setStatus(ev) })
  return status
}

/** Tình trạng kết nối WebSocket: dong | dang_ket_noi | mo | mat */
export function useWsState() {
  const [s, setS] = useState(wsState)
  useEffect(() => {
    stateListeners.add(setS)
    setS(wsState)
    return () => stateListeners.delete(setS)
  }, [])
  return s
}
