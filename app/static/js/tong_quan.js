/* Trang Tong quan (/): so lieu hom nay + luot moi nhat + nguoi dang co mat. Moi luot moi (WebSocket) -> tai lai. */
"use strict";

let lastTopId = null;

function luotItem(c, isNew) {
  const who = c.cong_nhan ? `<a href="/cu/cong-nhan/${c.cong_nhan.id}">${SG.esc(c.cong_nhan.ten)}</a>
      <span class="text-muted small">${SG.esc(c.cong_nhan.ma)}</span>` : `<span class="text-muted">${SG.MAT[c.trang_thai_mat][0]}</span>`;
  const img = c.anh ? `<img class="thumb" src="${c.anh}" alt="Ảnh lượt" data-check="${c.id}" loading="lazy">` : `<span class="thumb-empty"></span>`;
  return `<li class="list-group-item d-flex align-items-center gap-3${isNew ? " new-item" : ""}">
    ${img}
    <div class="flex-grow-1">
      <div>${who}</div>
      <div class="small">${SG.badge(SG.KET_QUA, c.ket_qua)} ${SG.badge(SG.HANH_DONG, c.hanh_dong)}
        ${c.thieu && c.thieu.length ? `<span class="text-danger">${SG.esc(SG.thieu(c.thieu))}</span>` : ""}</div>
    </div>
    <div class="text-end text-nowrap"><div class="fw-semibold">${SG.gio(c.thoi_diem, true)}</div>
      <div class="small text-muted">${c.diem != null ? "điểm " + c.diem.toFixed(2) : ""}</div></div>
  </li>`;
}

async function load() {
  let d;
  try { d = await SG.api("GET", "/api/tong-quan"); } catch (e) { SG.toast(e.message, "danger"); return; }
  document.getElementById("tq-ngay").textContent = SG.ngay(d.ngay);
  for (const k of ["so_cong_nhan", "da_vao", "dang_co_mat", "luot_khong_dat"]) {
    document.getElementById(`tq-${k}`).textContent = d[k];
  }
  document.getElementById("tq-ty_le_dat").textContent = d.ty_le_dat == null ? "–" : `${Math.round(d.ty_le_dat * 100)}%`;
  document.getElementById("tq-ty-le-ghi-chu").textContent =
    d.luot_dat + d.luot_khong_dat ? `${d.luot_dat}/${d.luot_dat + d.luot_khong_dat} lượt đạt` : "chưa có lượt";

  const list = document.getElementById("tq-luot");
  const topId = d.luot_moi_nhat.length ? d.luot_moi_nhat[0].id : null;
  list.innerHTML = d.luot_moi_nhat.length
    ? d.luot_moi_nhat.map(c => luotItem(c, lastTopId !== null && c.id > lastTopId)).join("")
    : `<li class="list-group-item text-muted">Chưa có lượt kiểm tra nào.</li>`;
  lastTopId = topId;

  document.getElementById("tq-co-mat-n").textContent = d.dang_co_mat_ds.length;
  document.getElementById("tq-co-mat").innerHTML = d.dang_co_mat_ds.length
    ? d.dang_co_mat_ds.map(p => `<li class="list-group-item d-flex justify-content-between">
        <span><a href="/cu/cong-nhan/${p.worker_id}">${SG.esc(p.ho_ten)}</a> <span class="small text-muted">${SG.esc(p.ma)}${p.to_doi ? " · " + SG.esc(p.to_doi) : ""}</span></span>
        <span class="text-nowrap">vào ${p.gio_vao}</span></li>`).join("")
    : `<li class="list-group-item text-muted">Chưa có ai.</li>`;
}

document.getElementById("tq-luot").addEventListener("click", e => {
  const id = e.target.dataset.check;
  if (id) SG.showCheck(id, load).catch(err => SG.toast(err.message, "danger"));
});

const reload = SG.debounce(load, 300);
SG.onEvent(ev => {
  const live = document.getElementById("tq-live");
  if (ev.loai === "luot") reload();
  if (ev.loai === "mat_ket_noi") { live.className = "badge text-bg-danger ms-2"; live.textContent = "● Mất kết nối"; }
  if (ev.loai === "trang_thai") { live.className = "badge text-bg-success ms-2"; live.textContent = "● Trực tiếp"; }
});
load();
