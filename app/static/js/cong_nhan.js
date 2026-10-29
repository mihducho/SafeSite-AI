/* Trang Cong nhan (/cong-nhan): danh sach, tim kiem, loc theo to va trang thai, them cong nhan (modal). */
"use strict";

const $ = id => document.getElementById(id);
let teams = [];

async function loadTeams() {
  teams = (await SG.api("GET", "/api/to-doi")).ds;
  const opts = teams.map(t => `<option value="${t.id}">${SG.esc(t.name)}</option>`).join("");
  $("f-team").insertAdjacentHTML("beforeend", opts);
  $("a-team").insertAdjacentHTML("beforeend", opts);
}

async function load() {
  const p = new URLSearchParams();
  if ($("f-q").value.trim()) p.set("q", $("f-q").value.trim());
  if ($("f-team").value) p.set("to_doi", $("f-team").value);
  if ($("f-status").value) p.set("trang_thai", $("f-status").value);
  let d;
  try { d = await SG.api("GET", "/api/cong-nhan?" + p); } catch (e) { SG.toast(e.message, "danger"); return; }
  $("cn-tong").textContent = `${d.tong} người`;
  const minSamples = Number(document.body.dataset.minSamples);
  $("cn-rows").innerHTML = d.ds.length ? d.ds.map(w => {
    const enough = w.so_mau >= minSamples;
    const faces = w.status !== "dang_lam" ? `<span class="text-muted">–</span>`
      : `<span class="badge text-bg-${enough ? "success" : "warning"}">${w.so_mau} mẫu · ${enough ? "đủ" : `chưa đủ ${minSamples}`}</span>`;
    return `<tr>
      <td class="fw-semibold">${SG.esc(w.code)}</td>
      <td><a href="/cong-nhan/${w.id}">${SG.esc(w.full_name)}</a></td>
      <td>${SG.esc(w.team_name || "")}</td><td>${SG.esc(w.trade || "")}</td><td>${SG.esc(w.phone || "")}</td>
      <td>${SG.badge(SG.CONG_NHAN, w.status)}</td>
      <td>${w.consent_at ? `<span class="text-success" title="${SG.ngayGio(w.consent_at)}">✔ Đã đồng ý</span>` : `<span class="text-muted">Chưa</span>`}</td>
      <td>${faces}</td>
      <td class="text-end"><a class="btn btn-outline-primary btn-sm" href="/cong-nhan/${w.id}">Chi tiết</a></td>
    </tr>`;
  }).join("") : `<tr><td colspan="9" class="text-muted">Không có công nhân nào.</td></tr>`;
}

const addModal = new bootstrap.Modal($("add-modal"));
$("btn-add").addEventListener("click", () => {
  $("add-form").reset();
  $("add-error").classList.add("d-none");
  addModal.show();
  setTimeout(() => $("a-code").focus(), 300);
});

$("add-form").addEventListener("submit", async e => {
  e.preventDefault();
  const body = {code: $("a-code").value.trim(), full_name: $("a-name").value.trim(), phone: $("a-phone").value.trim() || null,
                trade: $("a-trade").value.trim() || null, team_id: $("a-team").value ? Number($("a-team").value) : null};
  if (!body.code || !body.full_name) {
    $("add-error").textContent = "Cần nhập mã công nhân và họ tên.";
    $("add-error").classList.remove("d-none");
    return;
  }
  try {
    const w = await SG.api("POST", "/api/cong-nhan", body);
    addModal.hide();
    location.href = `/cong-nhan/${w.id}`;  // sang trang chi tiet de ghi nhan dong y va chup mau
  } catch (err) {
    $("add-error").textContent = err.message;
    $("add-error").classList.remove("d-none");
  }
});

$("f-q").addEventListener("input", SG.debounce(load));
$("f-team").addEventListener("change", load);
$("f-status").addEventListener("change", load);
loadTeams().then(() => {
  const team = new URLSearchParams(location.search).get("to_doi");  // tu trang To doi bam vao so cong nhan
  if (team) $("f-team").value = team;
  return load();
}).catch(e => SG.toast(e.message, "danger"));
