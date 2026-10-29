/* Man hinh cong (/cong, DE_TAI.md muc 5 buoc 6, 12 F3).
 * - Trai: hinh truc tiep /stream/gate. Phai: o ket qua lon.
 * - Trang thai: cho (xam) -> dang kiem tra (xanh duong, khi cong o pha KIEM_TRA) -> ket qua xanh/do/vang (ten, cau thong
 *   bao, gio, anh luot) trong data-result-seconds giay -> ve cho.
 * - Am thanh: trinh duyet chan phat tieng khi nguoi dung chua bam gi -> nut "Bat am thanh". Doc cau thong bao bang
 *   speechSynthesis voi giong co lang bat dau bang "vi" (uu tien giong cai san trong may: giong "Online" can mang);
 *   khong co giong tieng Viet thi phat tieng bip bang Web Audio: 1 tieng = dat (xanh), 2 tieng = khong dat hoac vang.
 * - Cong loi / mat ket noi may chu -> phu man hinh do "He thong kiem tra tam gian doan".
 */
"use strict";

const RESULT_SECONDS = Number(document.body.dataset.resultSeconds || 5);
const box = document.getElementById("result-box");
const els = {title: document.getElementById("result-title"), msg: document.getElementById("result-msg"),
             time: document.getElementById("result-time"), img: document.getElementById("result-img")};
let showing = false;      // dang hien ket qua 1 luot
let resultTimer = null;
let phase = null;         // CHO / KIEM_TRA / CHO_ROI_DI (tu su kien trang_thai)

function setBox(cls, title, msg = "", time = "", img = null) {
  box.className = `result-box ${cls}`;
  els.title.textContent = title;
  els.msg.textContent = msg;
  els.time.textContent = time;
  els.img.style.display = img ? "" : "none";
  if (img) els.img.src = img;
}

const showIdle = () => setBox("cho", "Mời đứng vào vị trí, nhìn vào camera");
const showChecking = () => setBox("kiem-tra", "Đang kiểm tra…", "Mời đứng yên, nhìn thẳng camera");

function showResult(ev) {
  showing = true;
  const name = ev.cong_nhan ? ev.cong_nhan.ten : "";
  setBox(ev.mau, name || ev.thong_bao, name ? ev.thong_bao : "", ev.gio || "", ev.anh);
  sound.announce(ev);
  clearTimeout(resultTimer);
  resultTimer = setTimeout(() => {
    showing = false;
    phase === "KIEM_TRA" ? showChecking() : showIdle();
  }, RESULT_SECONDS * 1000);
}

// ---------- am thanh ----------
const sound = {
  enabled: false, voice: null, ctx: null,

  pickVoice() {
    const vi = speechSynthesis.getVoices().filter(v => (v.lang || "").toLowerCase().startsWith("vi"));
    vi.sort((a, b) => Number(b.localService) - Number(a.localService));  // giong trong may truoc (khong can mang)
    this.voice = vi[0] || null;
    this.showInfo();
  },

  showInfo() {
    const info = document.getElementById("voice-info");
    if (!this.enabled) return;
    info.textContent = this.voice
      ? `Âm thanh: giọng ${this.voice.name} (${this.voice.lang}${this.voice.localService ? ", có sẵn trong máy" : ", trực tuyến – cần mạng"})`
      : "Âm thanh: máy không có giọng tiếng Việt → phát tiếng bíp (1 tiếng: đạt, 2 tiếng: không đạt hoặc cần làm lại)";
  },

  enable() {
    this.enabled = true;
    this.ctx = this.ctx || new (window.AudioContext || window.webkitAudioContext)();
    this.ctx.resume();
    if ("speechSynthesis" in window) {
      this.pickVoice();
      speechSynthesis.onvoiceschanged = () => this.pickVoice();  // danh sach giong tai cham
    } else {
      this.showInfo();
    }
    const b = document.getElementById("btn-sound");
    b.textContent = "🔊 Âm thanh đang bật";
    b.className = "btn btn-success btn-sm";
    this.beep(1);
  },

  beep(n) {
    if (!this.ctx) return;
    for (let i = 0; i < n; i++) {
      const t = this.ctx.currentTime + i * 0.3;
      const osc = this.ctx.createOscillator(), gain = this.ctx.createGain();
      osc.frequency.value = n === 1 ? 880 : 440;
      gain.gain.setValueAtTime(0.25, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.22);
      osc.connect(gain).connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.23);
    }
  },

  announce(ev) {
    if (!this.enabled) return;
    const beeps = ev.mau === "xanh" ? 1 : 2;
    if (!this.voice) { this.beep(beeps); return; }
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(ev.thong_bao);
    u.voice = this.voice;
    u.lang = this.voice.lang;
    u.onerror = () => this.beep(beeps);  // vd giong truc tuyen nhung mat mang
    speechSynthesis.speak(u);
  },
};

document.getElementById("btn-sound").addEventListener("click", () => sound.enable());

// ---------- toan man hinh, dong ho, hinh truc tiep ----------
document.getElementById("btn-full").addEventListener("click", () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(() => SG.toast && SG.toast("Trình duyệt không cho toàn màn hình", "danger"));
});

const clock = document.getElementById("gate-clock");
const tick = () => { clock.textContent = new Date().toLocaleTimeString("vi-VN", {timeZone: "Asia/Ho_Chi_Minh", hour12: false}); };
tick();
setInterval(tick, 1000);

const stream = document.getElementById("gate-stream");
stream.addEventListener("error", () => setTimeout(() => { stream.src = "/stream/gate?t=" + Date.now(); }, 2000));

// ---------- su kien ----------
const errorBox = document.getElementById("gate-error");
function showError(detail) {
  errorBox.classList.add("show");
  document.getElementById("gate-error-detail").textContent = detail || "";
}

SG.onEvent(ev => {
  if (ev.loai === "mat_ket_noi") { showError("Mất kết nối tới máy chủ, đang thử kết nối lại…"); return; }
  if (ev.loai === "trang_thai") {
    phase = ev.pha;
    if (ev.trang_thai === "loi" || ev.trang_thai === "tat" || ev.loi) {
      showError(ev.trang_thai === "tat" ? "Cổng đang tắt" : ev.loi);
    } else {
      errorBox.classList.remove("show");
      if (stream.naturalWidth === 0) stream.src = "/stream/gate?t=" + Date.now();  // vua khoi dong lai
    }
    if (!showing) {
      if (ev.trang_thai === "dang_khoi_dong") setBox("cho", "Đang khởi động camera…");
      else if (phase === "KIEM_TRA") showChecking();
      else showIdle();
    }
    return;
  }
  if (ev.loai === "luot") showResult(ev);
});
