/* Trang Chi tiet cong nhan (/cong-nhan/{id}): thong tin, dong y, mau khuon mat (chup tu camera cong, tai len, xoa),
 * luot kiem tra va bang cong gan day, cho nghi viec / di lam lai. */
"use strict";

const $ = id => document.getElementById(id);
const WID = Number($("worker-page").dataset.workerId);
const MIN = Number(document.body.dataset.minSamples), MAX = Number(document.body.dataset.maxSamples);
let worker = null;

function alertHtml(kind, text) { return `<div class="alert alert-${kind} py-2 mb-0">${SG.esc(text)}</div>`; }

// ---------- thong tin ----------
async function loadWorker() {
  worker = await SG.api("GET", `/api/cong-nhan/${WID}`);
  const w = worker, active = w.status === "dang_lam";
  $("w-title").textContent = w.full_name;
  $("w-code").textContent = w.code;
  $("w-status").innerHTML = SG.badge(SG.CONG_NHAN, w.status);
  $("i-code").value = w.code; $("i-name").value = w.full_name;
  $("i-phone").value = w.phone || ""; $("i-trade").value = w.trade || ""; $("i-team").value = w.team_id || "";
  $("i-created").textContent = w.created_at ? `Thêm ngày ${SG.ngay(w.created_at)}` : "";
  $("btn-quit").classList.toggle("d-none", !active);
  $("btn-rejoin").classList.toggle("d-none", active);

  // dong y
  if (w.consent_at) {
    $("consent-done").innerHTML = `✔ Đã ghi nhận đồng ý lúc <b>${SG.gio(w.consent_at)} ${SG.ngay(w.consent_at)}</b>` +
      (w.consent_by_name ? ` bởi <b>${SG.esc(w.consent_by_name)}</b>` : "");
  }
  $("consent-done").classList.toggle("d-none", !w.consent_at);
  $("consent-form").classList.toggle("d-none", !!w.consent_at || !active);

  // mau mat chi dung duoc khi dang lam va da dong y
  const canEnroll = active && !!w.consent_at;
  $("f-need-consent").classList.toggle("d-none", canEnroll || !active);
  for (const id of ["btn-capture", "btn-upload", "f-files"]) $(id).disabled = !canEnroll;
  if (canEnroll && !$("f-live").src) $("f-live").src = "/stream/gate";
  if (!canEnroll) $("f-live").removeAttribute("src");
}

$("info-form").addEventListener("submit", async e => {
  e.preventDefault();
  const body = {code: $("i-code").value.trim(), full_name: $("i-name").value.trim(), phone: $("i-phone").value.trim() || null,
                trade: $("i-trade").value.trim() || null, team_id: $("i-team").value ? Number($("i-team").value) : null};
  try {
    await SG.api("PATCH", `/api/cong-nhan/${WID}`, body);
    SG.toast("Đã lưu thông tin");
    await loadWorker();
  } catch (err) { SG.toast(err.message, "danger"); }
});

$("consent-check").addEventListener("change", e => { $("btn-consent").disabled = !e.target.checked; });
$("btn-consent").addEventListener("click", e => SG.busy(e.currentTarget, async () => {
  try {
    await SG.api("POST", `/api/cong-nhan/${WID}/dong-y`, {dong_y: $("consent-check").checked});
    SG.toast("Đã ghi nhận đồng ý");
    await loadWorker();
  } catch (err) { SG.toast(err.message, "danger"); }
}));

// ---------- mau khuon mat ----------
async function loadSamples() {
  const d = await SG.api("GET", `/api/cong-nhan/${WID}/mau-mat`);
  $("f-count").innerHTML = `<span class="badge text-bg-${d.du_mau ? "success" : "warning"}">${d.so_mau}/${MAX} mẫu` +
    (d.du_mau ? " · đủ để nhận diện" : ` · cần ít nhất ${MIN}`) + "</span>";
  $("btn-del-all").disabled = d.so_mau === 0;
  $("f-grid").innerHTML = d.ds.length ? d.ds.map(s => `
    <div class="face-item">
      <img src="${s.anh}" alt="Mẫu ${s.id}">
      <button class="btn btn-danger btn-sm btn-del" data-del="${s.id}" title="Xoá mẫu này">✕</button>
      <div class="face-q">${s.source === "camera" ? "camera" : "tải lên"} · ${s.quality.toFixed(2)}</div>
    </div>`).join("") : `<span class="text-muted">Chưa có mẫu khuôn mặt nào.</span>`;
}

$("btn-capture").addEventListener("click", e => SG.busy(e.currentTarget, async () => {
  try {
    const r = await SG.api("POST", `/api/cong-nhan/${WID}/mau-mat/chup`);
    $("f-capture-msg").innerHTML = alertHtml("success", `Đã chụp mẫu (chất lượng ${r.mau.quality.toFixed(2)}). Tổng ${r.so_mau} mẫu.`);
    await loadSamples();
  } catch (err) { $("f-capture-msg").innerHTML = alertHtml("danger", err.message); }
}));

$("btn-upload").addEventListener("click", e => SG.busy(e.currentTarget, async () => {
  const files = $("f-files").files;
  if (!files.length) { $("f-upload-msg").innerHTML = `<li class="text-danger">Chọn ít nhất 1 ảnh.</li>`; return; }
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  try {
    const r = await SG.api("POST", `/api/cong-nhan/${WID}/mau-mat/tai-len`, fd);
    $("f-upload-msg").innerHTML = r.ket_qua.map(x => x.ok
      ? `<li class="text-success">✔ ${SG.esc(x.ten)}</li>` : `<li class="text-danger">✕ ${SG.esc(x.ten)}: ${SG.esc(x.ly_do)}</li>`).join("");
    $("f-files").value = "";
    await loadSamples();
  } catch (err) { $("f-upload-msg").innerHTML = `<li class="text-danger">${SG.esc(err.message)}</li>`; }
}));

$("f-grid").addEventListener("click", async e => {
  const id = e.target.dataset.del;
  if (!id) return;
  try { await SG.api("DELETE", `/api/mau-mat/${id}`); await loadSamples(); } catch (err) { SG.toast(err.message, "danger"); }
});

$("btn-del-all").addEventListener("click", async () => {
  const ok = await SG.confirmBox("Xoá dữ liệu khuôn mặt",
    `Xoá <b>toàn bộ</b> mẫu khuôn mặt (vector và ảnh mẫu) của <b>${SG.esc(worker.full_name)}</b>? ` +
    "Sau khi xoá, công nhân không được nhận diện ở cổng cho tới khi đăng ký lại.", "Xoá tất cả");
  if (!ok) return;
  try {
    const r = await SG.api("DELETE", `/api/cong-nhan/${WID}/mau-mat`);
    SG.toast(`Đã xoá ${r.so_mau_da_xoa} mẫu`);
    await loadSamples();
  } catch (err) { SG.toast(err.message, "danger"); }
});

// ---------- nghi viec / di lam lai ----------
$("btn-quit").addEventListener("click", async () => {
  const ok = await SG.confirmBox("Cho nghỉ việc",
    `Cho <b>${SG.esc(worker.full_name)}</b> nghỉ việc?<br><br>Hệ thống sẽ <b>xoá toàn bộ dữ liệu khuôn mặt</b> (vector và ảnh mẫu) ` +
    "của người này và không nhận diện người này ở cổng nữa. Lịch sử kiểm tra và bảng công vẫn được giữ.", "Cho nghỉ việc");
  if (!ok) return;
  try {
    const r = await SG.api("POST", `/api/cong-nhan/${WID}/nghi-viec`);
    SG.toast(`Đã cho nghỉ việc, xoá ${r.so_mau_da_xoa} mẫu khuôn mặt`, "warning");
    await Promise.all([loadWorker(), loadSamples()]);
  } catch (err) { SG.toast(err.message, "danger"); }
});

$("btn-rejoin").addEventListener("click", async () => {
  const ok = await SG.confirmBox("Cho đi làm lại", `Nhận lại <b>${SG.esc(worker.full_name)}</b>? Cần ghi nhận đồng ý và đăng ký khuôn mặt lại từ đầu.`,
                                 "Cho đi làm lại", "btn-success");
  if (!ok) return;
  try { await SG.api("POST", `/api/cong-nhan/${WID}/di-lam-lai`); SG.toast("Đã nhận lại công nhân"); await loadWorker(); }
  catch (err) { SG.toast(err.message, "danger"); }
});

// ---------- luot kiem tra, bang cong ----------
async function loadHistory() {
  const [checks, sheet] = await Promise.all([SG.api("GET", `/api/luot?cong_nhan_id=${WID}&so_dong=10`),
                                             SG.api("GET", `/api/cong-nhan/${WID}/bang-cong?so_ngay=14`)]);
  $("w-checks").innerHTML = checks.ds.length ? checks.ds.map(c => `<tr>
      <td>${c.anh ? `<img class="thumb" src="${c.anh}" data-check="${c.id}" alt="Ảnh" loading="lazy">` : ""}</td>
      <td class="text-nowrap">${SG.ngay(c.thoi_diem)} ${SG.gio(c.thoi_diem, true)}</td>
      <td>${SG.badge(SG.KET_QUA, c.ket_qua)}${c.thieu.length ? `<div class="small text-danger">${SG.esc(SG.thieu(c.thieu))}</div>` : ""}</td>
      <td>${c.diem != null ? c.diem.toFixed(2) : "–"}</td>
      <td>${SG.badge(SG.HANH_DONG, c.hanh_dong)}</td></tr>`).join("")
    : `<tr><td colspan="5" class="text-muted">Chưa có lượt nào.</td></tr>`;
  $("w-sheet").innerHTML = sheet.ds.length ? sheet.ds.map(r => `<tr>
      <td>${SG.ngay(r.ngay)}</td><td>${r.gio_vao || ""}</td><td>${r.gio_ra || (r.thieu_gio_ra ? '<span class="text-danger">thiếu</span>' : "")}</td>
      <td>${r.di_muon_phut ? r.di_muon_phut + " phút" : ""}</td><td>${r.gio_ra ? SG.phut(r.so_phut_lam) : ""}</td>
      <td>${SG.badge(SG.CHAM_CONG, r.trang_thai)}</td></tr>`).join("")
    : `<tr><td colspan="6" class="text-muted">Chưa có ngày công nào.</td></tr>`;
}
$("w-checks").addEventListener("click", e => { const id = e.target.dataset.check; if (id) SG.showCheck(id, loadHistory); });

SG.onEvent(ev => { if (ev.loai === "luot" && ev.cong_nhan && ev.cong_nhan.id === WID) loadHistory(); });

(async () => {
  try {
    const [teams, consent] = await Promise.all([SG.api("GET", "/api/to-doi"), SG.api("GET", "/api/dong-y/noi-dung")]);
    $("i-team").insertAdjacentHTML("beforeend", teams.ds.map(t => `<option value="${t.id}">${SG.esc(t.name)}</option>`).join(""));
    $("consent-text").textContent = consent.noi_dung;
    await Promise.all([loadWorker(), loadSamples(), loadHistory()]);
  } catch (err) { SG.toast(err.message, "danger"); }
})();
