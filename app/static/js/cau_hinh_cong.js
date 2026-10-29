/* Trang Cau hinh cong (/cau-hinh-cong): nguon camera, goc xoay, khoi dong lai, xem truoc, ve vung kiem tra.
 * Moi hinh lay qua ung dung (/stream/gate, /api/cong/anh-hien-tai), khong mo thang URL camera (DroidCam chi cho 1 ket noi).
 * Vung kiem tra luu dang ti le 0-1 tren hinh DA xoay: diem bam (pixel tren anh hien thi) / kich thuoc anh hien thi. */
"use strict";

const $ = id => document.getElementById(id);
let gate = null, points = [];
const ROT = {0: "0°", 90: "90°", 180: "180°", 270: "270°"};

const fmtPts = pts => pts.map(([x, y]) => `${x},${y}`).join(" ");

function drawZone() {
  $("z-saved").setAttribute("points", gate ? fmtPts(gate.zone) : "");
  $("z-new").setAttribute("points", fmtPts(points));
  $("z-dots").innerHTML = points.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="0.012" class="z-dot"></circle>`).join("");
  $("z-info").innerHTML = points.length
    ? `Vùng mới: ${points.length} điểm${points.length < 3 ? " (cần ít nhất 3)" : ""}. Bấm <b>Lưu vùng</b> để áp dụng.`
    : `<span class="text-warning">■</span> vùng đang dùng (${gate ? gate.zone.length : 0} điểm). Bấm lên ảnh để vẽ vùng mới.`;
}

async function loadGate() {
  gate = await SG.api("GET", "/api/cong");
  $("g-name").value = gate.name;
  $("g-source").value = gate.camera_source;
  $("g-rotate").value = String(gate.rotate);
  $("g-env").classList.toggle("d-none", !gate.ghi_de_boi_env);
  $("g-env-src").textContent = gate.nguon_env || "";
  drawZone();
}

function showStatus(st) {
  const rows = [
    ["Trạng thái", `${SG.esc(SG.gateText(st)[0])}`],
    ["Nguồn đang chạy", SG.esc(st.nguon || "–")],
    ["Góc xoay", ROT[st.xoay] || "–"],
    ["Độ phân giải (sau xoay)", st.do_phan_giai ? st.do_phan_giai.replace("x", " × ") : "–"],
    ["Số khung/giây nhận được", st.khung_giay != null ? st.khung_giay : "–"],
    ["Số lượt từ lúc khởi động", st.so_luot ?? 0],
  ];
  $("g-status").innerHTML = rows.map(([k, v]) => `<tr><th class="text-nowrap">${k}</th><td>${v}</td></tr>`).join("");
}

async function pollStatus() {
  try { showStatus(await SG.api("GET", "/api/cong/trang-thai")); } catch (e) { /* lan sau thu lai */ }
}

function snapshot() {
  const img = $("z-img");
  img.onerror = () => { $("z-info").innerHTML = `<span class="text-danger">Chưa có hình từ camera cổng (xem Trạng thái).</span>`; };
  img.src = "/api/cong/anh-hien-tai?t=" + Date.now();
}

async function save(body, msg) {
  try {
    const r = await SG.api("PATCH", "/api/cong", body);
    $("g-error").classList.add("d-none");
    SG.toast(msg + (r.ghi_chu ? ` – ${r.ghi_chu}` : ""), r.ghi_chu ? "warning" : "success");
    points = [];
    await loadGate();
    setTimeout(() => { snapshot(); $("g-live").src = "/stream/gate?t=" + Date.now(); }, 2500);  // cho cong mo lai camera
  } catch (err) {
    $("g-error").textContent = err.message;
    $("g-error").classList.remove("d-none");
  }
}

$("g-form").addEventListener("submit", e => {
  e.preventDefault();
  save({name: $("g-name").value.trim() || null, camera_source: $("g-source").value.trim() || null,
        rotate: Number($("g-rotate").value)}, "Đã lưu, đang khởi động lại cổng");
});
$("g-restart").addEventListener("click", async e => SG.busy(e.currentTarget, async () => {
  try { await SG.api("POST", "/api/cong/khoi-dong-lai"); SG.toast("Đang khởi động lại cổng"); setTimeout(snapshot, 2500); }
  catch (err) { SG.toast(err.message, "danger"); }
}));

$("z-wrap").addEventListener("click", e => {
  const r = $("z-img").getBoundingClientRect();
  if (!$("z-img").naturalWidth || e.clientX < r.left || e.clientY < r.top || e.clientX > r.right || e.clientY > r.bottom) return;
  const x = Math.round(((e.clientX - r.left) / r.width) * 10000) / 10000;
  const y = Math.round(((e.clientY - r.top) / r.height) * 10000) / 10000;
  points.push([Math.min(1, Math.max(0, x)), Math.min(1, Math.max(0, y))]);
  drawZone();
});
$("z-snap").addEventListener("click", snapshot);
$("z-undo").addEventListener("click", () => { points.pop(); drawZone(); });
$("z-clear").addEventListener("click", () => { points = []; drawZone(); });
$("z-full").addEventListener("click", () => { points = [[0, 0], [1, 0], [1, 1], [0, 1]]; drawZone(); });
$("z-save").addEventListener("click", () => {
  if (points.length < 3) { SG.toast("Vùng cần ít nhất 3 điểm", "danger"); return; }
  save({zone: points}, "Đã lưu vùng kiểm tra");
});

loadGate().catch(e => SG.toast(e.message, "danger"));
snapshot();
pollStatus();
setInterval(pollStatus, 2000);
