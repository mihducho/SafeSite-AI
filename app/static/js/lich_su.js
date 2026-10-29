/* Trang Lich su kiem tra (/lich-su): loc theo ngay, cong nhan, ket qua, hanh dong; phan trang; anh nho -> modal anh lon
 * kem chi tiet; danh gia Dung / Bao nham. Bo loc ghi len dia chi trang (?ngay=...) de tai lai van giu. */
"use strict";

const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
let page = Number(params.get("trang") || 1), pages = 1;

function fillSelect(id, map) {
  $(id).insertAdjacentHTML("beforeend", Object.entries(map).map(([k, [t]]) => `<option value="${k}">${t}</option>`).join(""));
}
fillSelect("f-kq", SG.KET_QUA);
fillSelect("f-hd", SG.HANH_DONG);
// mo tu trang cong nhan (?cong_nhan_id=...) -> xem moi ngay; con lai mac dinh hom nay
$("f-ngay").value = params.has("ngay") ? params.get("ngay") : (params.has("cong_nhan_id") ? "" : SG.today);

function filters() {
  const p = new URLSearchParams();
  if ($("f-ngay").value) p.set("ngay", $("f-ngay").value);
  if ($("f-cn").value) p.set("cong_nhan_id", $("f-cn").value);
  if ($("f-kq").value) p.set("ket_qua", $("f-kq").value);
  if ($("f-hd").value) p.set("hanh_dong", $("f-hd").value);
  return p;
}

function reviewHtml(c) {
  if (c.danh_gia === "dung") return `<span class="badge text-bg-success">Đúng</span>`;
  if (c.danh_gia === "bao_nham") return `<span class="badge text-bg-danger">Báo nhầm</span>`;
  return `<button class="btn btn-outline-success btn-sm py-0" data-review="dung" data-id="${c.id}">Đúng</button>
          <button class="btn btn-outline-danger btn-sm py-0" data-review="bao_nham" data-id="${c.id}">Nhầm</button>`;
}

async function load() {
  const p = filters();
  const q = new URLSearchParams(p);
  if (!p.has("ngay")) q.set("ngay", "");  // "ngay=" = moi ngay
  q.set("trang", page);
  history.replaceState(null, "", "?" + q);
  p.set("trang", page);
  let d;
  try { d = await SG.api("GET", "/api/luot?" + p); } catch (e) { SG.toast(e.message, "danger"); return; }
  pages = Math.max(1, d.so_trang);
  $("ls-tong").textContent = `${d.tong} lượt` + ($("f-ngay").value ? ` ngày ${SG.ngay($("f-ngay").value)}` : "");
  $("pg-info").textContent = `Trang ${d.trang}/${pages}`;
  $("pg-prev").disabled = page <= 1;
  $("pg-next").disabled = page >= pages;
  $("ls-rows").innerHTML = d.ds.length ? d.ds.map(c => `<tr>
      <td>${c.anh ? `<img class="thumb" src="${c.anh}" data-check="${c.id}" alt="Ảnh lượt ${c.id}" loading="lazy">` : `<span class="thumb-empty"></span>`}</td>
      <td class="text-nowrap">${SG.ngay(c.thoi_diem)}<br><b>${SG.gio(c.thoi_diem, true)}</b></td>
      <td>${c.cong_nhan ? `<a href="/cu/cong-nhan/${c.cong_nhan.id}">${SG.esc(c.cong_nhan.ten)}</a><div class="small text-muted">${SG.esc(c.cong_nhan.ma)}</div>` : "–"}</td>
      <td>${SG.badge(SG.KET_QUA, c.ket_qua)}</td>
      <td class="small text-danger">${SG.esc(SG.thieu(c.thieu))}</td>
      <td>${SG.badge(SG.MAT, c.trang_thai_mat)}${c.diem != null ? `<div class="small">điểm ${c.diem.toFixed(2)}</div>` : ""}</td>
      <td>${SG.HUONG[c.huong] || "–"}</td>
      <td>${SG.badge(SG.HANH_DONG, c.hanh_dong)}</td>
      <td class="small">${c.thoi_gian_ms != null ? (c.thoi_gian_ms / 1000).toFixed(1) + " s" : ""}</td>
      <td class="text-nowrap">${reviewHtml(c)}</td></tr>`).join("")
    : `<tr><td colspan="10" class="text-muted">Không có lượt kiểm tra nào.</td></tr>`;
}

$("ls-rows").addEventListener("click", async e => {
  const t = e.target;
  if (t.dataset.check) SG.showCheck(t.dataset.check, load).catch(err => SG.toast(err.message, "danger"));
  if (t.dataset.review) {
    try { await SG.api("PATCH", `/api/luot/${t.dataset.id}/danh-gia`, {danh_gia: t.dataset.review}); load(); }
    catch (err) { SG.toast(err.message, "danger"); }
  }
});

for (const id of ["f-ngay", "f-cn", "f-kq", "f-hd"]) $(id).addEventListener("change", () => { page = 1; load(); });
$("btn-all-days").addEventListener("click", () => { $("f-ngay").value = ""; page = 1; load(); });
$("btn-reset").addEventListener("click", () => {
  $("f-ngay").value = SG.today; $("f-cn").value = ""; $("f-kq").value = ""; $("f-hd").value = ""; page = 1; load();
});
$("pg-prev").addEventListener("click", () => { if (page > 1) { page--; load(); } });
$("pg-next").addEventListener("click", () => { if (page < pages) { page++; load(); } });

// luot moi khi dang xem trang 1 -> tai lai
const reload = SG.debounce(load, 300);
SG.onEvent(ev => { if (ev.loai === "luot" && page === 1) reload(); });

(async () => {
  try {
    const ws = await SG.api("GET", "/api/cong-nhan");
    $("f-cn").insertAdjacentHTML("beforeend", ws.ds.map(w => `<option value="${w.id}">${SG.esc(w.code)} – ${SG.esc(w.full_name)}</option>`).join(""));
    for (const [id, key] of [["f-cn", "cong_nhan_id"], ["f-kq", "ket_qua"], ["f-hd", "hanh_dong"]]) {
      if (params.get(key)) $(id).value = params.get(key);
    }
  } catch (err) { SG.toast(err.message, "danger"); }
  load();
})();
