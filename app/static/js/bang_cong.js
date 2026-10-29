/* Trang Bang cong (/bang-cong): chon ngay, moi cong nhan 1 dong, cham cong thu cong (modal, bat buoc ly do). */
"use strict";

const $ = id => document.getElementById(id);
const modal = new bootstrap.Modal($("manual-modal"));
let rows = [], current = null;

function shiftDay(iso, n) {  // cong/tru n ngay tren chuoi YYYY-MM-DD (tinh theo UTC de khong lech mui gio)
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

async function load() {
  const ngay = $("d-ngay").value || SG.today;
  $("d-label").textContent = `Ngày ${SG.ngay(ngay)}`;
  history.replaceState(null, "", `?ngay=${ngay}`);
  const p = new URLSearchParams({ngay});
  if ($("d-team").value) p.set("to_doi", $("d-team").value);
  try { rows = (await SG.api("GET", "/api/bang-cong?" + p)).ds; } catch (e) { SG.toast(e.message, "danger"); return; }
  $("d-rows").innerHTML = rows.length ? rows.map((r, i) => `<tr>
      <td class="fw-semibold">${SG.esc(r.ma)}</td><td><a href="/cu/cong-nhan/${r.worker_id}">${SG.esc(r.ho_ten)}</a></td>
      <td>${SG.esc(r.to_doi || "")}</td>
      <td>${r.gio_vao || ""}</td>
      <td>${r.gio_ra || (r.thieu_gio_ra ? '<span class="badge text-bg-danger">Thiếu giờ ra</span>' : (r.gio_vao ? '<span class="text-muted">đang có mặt</span>' : ""))}</td>
      <td>${r.di_muon_phut ? `<span class="text-danger">${r.di_muon_phut} phút</span>` : ""}</td>
      <td>${r.ve_som_phut && r.gio_ra ? `${r.ve_som_phut} phút` : ""}</td>
      <td class="fw-semibold">${r.gio_ra ? SG.phut(r.so_phut_lam) : ""}</td>
      <td>${SG.badge(SG.CHAM_CONG, r.trang_thai)}</td>
      <td class="small" style="white-space: pre-line; max-width: 22rem">${SG.esc(r.ghi_chu || "")}</td>
      <td class="text-end"><button class="btn btn-outline-primary btn-sm text-nowrap" data-row="${i}">Chấm thủ công</button></td>
    </tr>`).join("") : `<tr><td colspan="11" class="text-muted">Không có công nhân nào.</td></tr>`;
  const came = rows.filter(r => r.gio_vao).length;
  $("d-sum").textContent = `${came}/${rows.length} người đã vào · ${rows.filter(r => r.di_muon_phut).length} người đi muộn · ` +
    `${rows.filter(r => r.gio_vao && !r.gio_ra).length} người chưa ra`;
}

$("d-rows").addEventListener("click", e => {
  const i = e.target.dataset.row;
  if (i === undefined) return;
  current = rows[Number(i)];
  $("m-who").textContent = `${current.ma} – ${current.ho_ten}`;
  $("m-day").textContent = SG.ngay(current.ngay);
  $("m-in").value = current.gio_vao || "";
  $("m-out").value = current.gio_ra || "";
  $("m-reason").value = "";
  $("m-error").classList.add("d-none");
  modal.show();
});

$("manual-form").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const body = {worker_id: current.worker_id, ngay: current.ngay, gio_vao: SG.hhmm($("m-in"), "Giờ vào"),
                  gio_ra: SG.hhmm($("m-out"), "Giờ ra"), ly_do: $("m-reason").value};
    if (!body.ly_do.trim()) throw new Error("Bắt buộc ghi lý do khi chấm công thủ công");
    await SG.api("POST", "/api/cham-cong-thu-cong", body);
    modal.hide();
    SG.toast("Đã lưu chấm công thủ công");
    load();
  } catch (err) {
    $("m-error").textContent = err.message;
    $("m-error").classList.remove("d-none");
  }
});

$("d-ngay").value = new URLSearchParams(location.search).get("ngay") || SG.today;
$("d-ngay").addEventListener("change", load);
$("d-prev").addEventListener("click", () => { $("d-ngay").value = shiftDay($("d-ngay").value || SG.today, -1); load(); });
$("d-next").addEventListener("click", () => { $("d-ngay").value = shiftDay($("d-ngay").value || SG.today, 1); load(); });
$("d-today").addEventListener("click", () => { $("d-ngay").value = SG.today; load(); });
$("d-team").addEventListener("change", load);
const reload = SG.debounce(load, 500);
SG.onEvent(ev => { if (ev.loai === "luot" && ev.ghi_cong && $("d-ngay").value === SG.today) reload(); });

SG.api("GET", "/api/to-doi").then(t => {
  $("d-team").insertAdjacentHTML("beforeend", t.ds.map(x => `<option value="${x.id}">${SG.esc(x.name)}</option>`).join(""));
}).catch(() => {}).finally(load);
