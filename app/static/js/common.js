/* Ham dung chung cho moi trang (DE_TAI.md muc 12 F3). JavaScript thuan, khong thu vien ngoai tru Bootstrap.
 *  SG.api(method, path, body)  goi API JSON; loi -> nem Error voi cau tieng Viet cua may chu; 401 -> ve /login
 *  SG.esc(s)                   chong chen ma HTML khi hien du lieu (ten cong nhan...)
 *  SG.ngay / SG.gio / SG.phut  dinh dang dd/mm/yyyy, HH:MM, so phut -> h:mm. API tra gio Viet Nam dang ISO
 *                              "2026-10-29T07:02:00+07:00" nen chi can cat chuoi (khong phu thuoc mui gio cua may)
 *  SG.onEvent(fn)              nhan su kien WebSocket /ws/events (tu ket noi lai khi mat ket noi)
 *  SG.toast, SG.confirmBox, SG.showCheck   thong bao nho, hop xac nhan, hop xem chi tiet 1 luot
 */
"use strict";

const SG = (() => {
  const today = document.body.dataset.today;  // YYYY-MM-DD theo gio Viet Nam (may chu tinh)

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  }

  function errorText(data, status) {
    const d = data && data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map(e => (e.loc ? e.loc.filter(x => x !== "body").join(".") + ": " : "") + e.msg).join("; ");
    return `Lỗi ${status}`;
  }

  async function api(method, path, body) {
    const init = {method, headers: {}};
    if (body instanceof FormData) init.body = body;
    else if (body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    let r;
    try {
      r = await fetch(path, init);
    } catch (e) {
      throw new Error("Không kết nối được máy chủ");
    }
    if (r.status === 401) {
      location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search);
      throw new Error("Chưa đăng nhập");
    }
    const data = (r.headers.get("content-type") || "").includes("json") ? await r.json() : null;
    if (!r.ok) throw new Error(errorText(data, r.status));
    return data;
  }

  const ngay = iso => { if (!iso) return ""; const [y, m, d] = iso.slice(0, 10).split("-"); return `${d}/${m}/${y}`; };
  const gio = (iso, seconds = false) => iso ? iso.slice(11, seconds ? 19 : 16) : "";
  const phut = m => `${Math.floor((m || 0) / 60)}:${String((m || 0) % 60).padStart(2, "0")}`;
  const ngayGio = iso => iso ? `${ngay(iso)} ${gio(iso)}` : "";

  // Nhan tieng Viet + mau Bootstrap cho cac ma trong CSDL
  const KET_QUA = {DAT: ["Đạt", "success"], KHONG_DAT: ["Không đạt", "danger"], KHONG_XAC_DINH: ["Không xác định", "warning"],
                   NHIEU_NGUOI: ["Nhiều người", "warning"], KHONG_CO_NGUOI: ["Không có người", "secondary"]};
  const HANH_DONG = {ghi_vao: ["Ghi giờ vào", "success"], ghi_ra: ["Ghi giờ ra", "primary"], khong_ghi: ["Không ghi", "secondary"],
                     bo_qua_trung: ["Bỏ qua (trùng)", "info"]};
  const MAT = {DA_NHAN_RA: ["Đã nhận ra", "success"], KHONG_NHAN_RA: ["Không nhận ra", "warning"],
               KHONG_THAY_MAT: ["Không thấy mặt", "secondary"]};
  const CHAM_CONG = {binh_thuong: ["Bình thường", "success"], ngoai_ca: ["Ngoài ca", "warning"],
                     cham_thu_cong: ["Chấm thủ công", "info"], chua_vao: ["Chưa vào", "light"]};
  const CONG_NHAN = {dang_lam: ["Đang làm", "success"], nghi_viec: ["Nghỉ việc", "secondary"]};
  const HUONG = {vao: "Vào", ra: "Ra"};
  const THIEU = {thieu_mu: "thiếu mũ bảo hộ", thieu_ao: "thiếu áo phản quang"};
  const DO_BAO_HO = {hardhat: "mũ bảo hộ", vest: "áo phản quang"};  // ten mon trong ppe.items (settings.yaml)
  const thieu = list => (list || []).map(t => THIEU[t] || t).join(", ");

  function badge(map, key) {
    const [text, color] = map[key] || [key ?? "", "light"];
    return `<span class="badge text-bg-${color}">${esc(text)}</span>`;
  }

  function toast(message, kind = "success") {
    const box = document.getElementById("toasts");
    if (!box) return;
    const el = document.createElement("div");
    el.className = `toast align-items-center text-bg-${kind} border-0`;
    el.setAttribute("role", "alert");
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${esc(message)}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Đóng"></button></div>`;
    box.appendChild(el);
    const t = new bootstrap.Toast(el, {delay: kind === "danger" ? 6000 : 3000});
    el.addEventListener("hidden.bs.toast", () => el.remove());
    t.show();
  }

  /** Hop xac nhan Bootstrap. Tra ve Promise<boolean>. bodyHtml da duoc esc() o noi goi neu co du lieu nguoi dung. */
  function confirmBox(title, bodyHtml, okText = "Đồng ý", okClass = "btn-danger") {
    const el = document.getElementById("confirm-modal");
    const ok = document.getElementById("confirm-ok");
    document.getElementById("confirm-title").textContent = title;
    document.getElementById("confirm-body").innerHTML = bodyHtml;
    ok.textContent = okText;
    ok.className = `btn ${okClass}`;
    const modal = bootstrap.Modal.getOrCreateInstance(el);
    return new Promise(resolve => {
      let answered = false;
      ok.onclick = () => { answered = true; modal.hide(); resolve(true); };
      el.addEventListener("hidden.bs.modal", () => { if (!answered) resolve(false); }, {once: true});
      modal.show();
    });
  }

  /** Nut dang xu ly: khoa nut, chay ham, mo lai nut. */
  async function busy(button, fn) {
    const old = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>${old}`;
    try { return await fn(); } finally { button.disabled = false; button.innerHTML = old; }
  }

  // --- WebSocket /ws/events dung chung ---
  const handlers = [];
  const onEvent = fn => handlers.push(fn);
  let lastStatus = null;

  function gateText(st) {
    if (!st) return ["Cổng: đang kết nối…", "secondary"];
    if (st.trang_thai === "dang_chay" && !st.loi) return [`Cổng: đang chạy${st.pha === "KIEM_TRA" ? " · đang kiểm tra" : ""}`, "success"];
    if (st.trang_thai === "dang_khoi_dong") return ["Cổng: đang khởi động", "warning"];
    if (st.trang_thai === "tat") return ["Cổng: đang tắt", "secondary"];
    return [`Cổng: lỗi${st.loi ? " – " + st.loi : ""}`, "danger"];
  }

  function setGateBadge(st, override) {
    const el = document.getElementById("gate-badge");
    if (!el) return;
    const [text, color] = override || gateText(st);
    el.textContent = text.length > 70 ? text.slice(0, 67) + "…" : text;
    el.title = text;
    el.className = `badge text-bg-${color} me-3`;
  }

  function connect() {
    const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/events`);
    ws.onmessage = e => {
      const ev = JSON.parse(e.data);
      if (ev.loai === "trang_thai") { lastStatus = ev; setGateBadge(ev); }
      handlers.forEach(h => { try { h(ev); } catch (err) { console.error(err); } });
    };
    ws.onclose = e => {
      if (e.code === 1008) { location.href = "/login?next=" + encodeURIComponent(location.pathname); return; }
      setGateBadge(null, ["Mất kết nối máy chủ", "danger"]);
      handlers.forEach(h => { try { h({loai: "mat_ket_noi"}); } catch (err) { console.error(err); } });
      setTimeout(connect, 2000);
    };
  }

  // --- hop chi tiet luot kiem tra ---
  async function showCheck(id, onChange) {
    const c = await api("GET", `/api/luot/${id}`);
    const d = c.chi_tiet || {}, nd = d.nhan_dien || {}, ms = d.ms_tb || {};
    document.getElementById("check-title").textContent = `Lượt #${c.id} – ${ngay(c.thoi_diem)} ${gio(c.thoi_diem, true)}`;
    const img = document.getElementById("check-img");
    img.src = c.anh || "";
    img.style.display = c.anh ? "" : "none";
    const rows = [
      ["Công nhân", c.cong_nhan ? `${esc(c.cong_nhan.ma)} – ${esc(c.cong_nhan.ten)}` : "–"],
      ["Kết quả", badge(KET_QUA, c.ket_qua) + (c.ly_do ? ` <span class="text-muted">(${esc(c.ly_do)})</span>` : "")],
      ["Thiếu", esc(thieu(c.missing || c.thieu)) || "–"],
      ["Nhận diện", badge(MAT, c.trang_thai_mat) + (c.diem != null ? ` điểm ${c.diem.toFixed(2)}` : "")],
      ["Người giống nhất", nd.gan_nhat_ma ? `${esc(nd.gan_nhat_ma)}${nd.diem_thu_hai != null ? `, người thứ hai ${nd.diem_thu_hai.toFixed(2)}` : ""}` : "–"],
      ["Hướng / hành động", `${HUONG[c.huong] || "–"} / ${badge(HANH_DONG, c.hanh_dong)}`],
      ["Kết quả bảo hộ gốc", d.ket_qua_bao_ho ? badge(KET_QUA, d.ket_qua_bao_ho) : "–"],
      ["Số khung", d.so_khung != null ? `${d.so_khung} (hợp lệ ${d.so_khung_hop_le ?? "–"}, có mặt ${d.so_khung_co_mat ?? "–"}, nhiều mặt ${Math.round((d.ty_le_khung_nhieu_mat || 0) * 100)}%)` : "–"],
      ["Tỷ lệ có mặt đồ bảo hộ", Object.entries(c.ty_le_co_mat || {}).map(([k, v]) => `${esc(DO_BAO_HO[k] || k)} ${Math.round(v * 100)}%`).join(", ") || "–"],
      ["Thời gian lượt", c.thoi_gian_ms != null ? `${(c.thoi_gian_ms / 1000).toFixed(2)} giây` : "–"],
      ["Mỗi khung", ms.bao_ho != null ? `bảo hộ ${ms.bao_ho} ms, YuNet ${ms.yunet} ms, SFace ${ms.sface ?? "–"} ms` : "–"],
      ["Từ lúc thấy mặt", d.tu_luc_thay_mat_ms != null ? `${(d.tu_luc_thay_mat_ms / 1000).toFixed(2)} giây` : "–"],
    ];
    document.getElementById("check-info").innerHTML = rows.map(([k, v]) => `<tr><th class="text-nowrap">${k}</th><td>${v}</td></tr>`).join("");
    const review = document.getElementById("check-review");
    const showReview = s => { review.innerHTML = s === "dung" ? badge({x: ["Đã xác nhận đúng", "success"]}, "x") :
                                               s === "bao_nham" ? badge({x: ["Đã báo nhầm", "danger"]}, "x") : ""; };
    showReview(c.danh_gia);
    const setReview = async value => {
      try {
        const r = await api("PATCH", `/api/luot/${c.id}/danh-gia`, {danh_gia: value});
        showReview(r.danh_gia);
        if (onChange) onChange(r);
      } catch (e) { toast(e.message, "danger"); }
    };
    document.getElementById("check-dung").onclick = () => setReview("dung");
    document.getElementById("check-nham").onclick = () => setReview("bao_nham");
    bootstrap.Modal.getOrCreateInstance(document.getElementById("check-modal")).show();
  }

  /** O gio HH:MM (24 gio): rong -> null; sai dang -> nem Error kem ten o. */
  function hhmm(input, label) {
    const v = input.value.trim();
    if (!v) return null;
    const m = v.match(/^(\d{1,2}):?(\d{2})$/);
    if (!m || Number(m[1]) > 23 || Number(m[2]) > 59) throw new Error(`${label}: nhập giờ dạng HH:MM (24 giờ), ví dụ 07:30`);
    return `${m[1].padStart(2, "0")}:${m[2]}`;
  }

  /** Doi tuong debounce: goi fn sau khi ngung go wait ms (o tim kiem). */
  const debounce = (fn, wait = 300) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), wait); }; };

  document.addEventListener("DOMContentLoaded", connect);

  return {api, esc, ngay, gio, phut, ngayGio, badge, thieu, toast, confirmBox, busy, onEvent, showCheck, debounce, hhmm,
          gateText, today, status: () => lastStatus, KET_QUA, HANH_DONG, MAT, CHAM_CONG, CONG_NHAN, HUONG, THIEU};
})();
