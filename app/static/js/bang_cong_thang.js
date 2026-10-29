/* Trang Bang cong thang (/bang-cong/thang): moi cong nhan 1 dong, moi ngay 1 o; xuat Excel. */
"use strict";

const $ = id => document.getElementById(id);

async function load() {
  const thang = $("m-thang").value || SG.today.slice(0, 7);
  const p = new URLSearchParams({thang});
  if ($("m-team").value) p.set("to_doi", $("m-team").value);
  $("m-excel").href = "/api/bang-cong/thang/excel?" + p;
  history.replaceState(null, "", `?thang=${thang}`);
  let d;
  try { d = await SG.api("GET", "/api/bang-cong/thang?" + p); } catch (e) { SG.toast(e.message, "danger"); return; }
  const days = Array.from({length: d.so_ngay}, (_, i) => i + 1);
  $("m-head").innerHTML = `<tr><th class="text-start">Mã</th><th class="text-start">Họ tên</th>${days.map(x => `<th>${x}</th>`).join("")}
    <th>Ngày công</th><th>Tổng giờ</th><th>Lần muộn</th></tr>`;
  $("m-rows").innerHTML = d.ds.length ? d.ds.map(r => `<tr>
      <td class="text-start fw-semibold">${SG.esc(r.ma)}</td>
      <td class="text-start text-nowrap"><a href="/cu/cong-nhan/${r.worker_id}">${SG.esc(r.ho_ten)}</a></td>
      ${days.map(x => {
        const c = r.ngay[x];
        if (!c || !c.gio_vao) return "<td></td>";
        const cls = c.di_muon_phut > 0 ? "table-warning" : "";
        const text = c.gio_ra ? SG.phut(c.so_phut_lam) : "vào";
        return `<td class="${cls}" title="${c.gio_vao}–${c.gio_ra || "?"}"><a class="text-reset text-decoration-none" href="/cu/bang-cong?ngay=${c.ngay}">${text}</a></td>`;
      }).join("")}
      <td class="fw-semibold">${r.so_ngay_cong}</td><td class="fw-semibold">${SG.phut(r.tong_phut)}</td><td>${r.so_lan_muon}</td>
    </tr>`).join("") : `<tr><td colspan="${d.so_ngay + 5}" class="text-muted">Không có dữ liệu.</td></tr>`;
}

$("m-thang").value = new URLSearchParams(location.search).get("thang") || SG.today.slice(0, 7);
$("m-thang").addEventListener("change", load);
$("m-team").addEventListener("change", load);
SG.api("GET", "/api/to-doi").then(t => {
  $("m-team").insertAdjacentHTML("beforeend", t.ds.map(x => `<option value="${x.id}">${SG.esc(x.name)}</option>`).join(""));
}).catch(() => {}).finally(load);
