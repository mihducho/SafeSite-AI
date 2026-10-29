/* Trang To doi (/to-doi): danh sach, them, sua (dung chung 1 modal), so cong nhan dang lam moi to. */
"use strict";

const $ = id => document.getElementById(id);
const modal = new bootstrap.Modal($("team-modal"));
let teams = [], editing = null;  // editing: id to dang sua, null = them moi

async function load() {
  try { teams = (await SG.api("GET", "/api/to-doi")).ds; } catch (e) { SG.toast(e.message, "danger"); return; }
  $("td-rows").innerHTML = teams.length ? teams.map(t => `<tr>
      <td class="fw-semibold">${SG.esc(t.name)}</td><td>${SG.esc(t.contractor || "")}</td><td>${SG.esc(t.leader_name || "")}</td>
      <td><a href="/cong-nhan?to_doi=${t.id}">${t.so_cong_nhan}</a></td>
      <td class="text-end"><button class="btn btn-outline-primary btn-sm" data-edit="${t.id}">Sửa</button></td></tr>`).join("")
    : `<tr><td colspan="5" class="text-muted">Chưa có tổ đội nào.</td></tr>`;
}

function open(team) {
  editing = team ? team.id : null;
  $("team-title").textContent = team ? `Sửa tổ: ${team.name}` : "Thêm tổ đội";
  $("t-name").value = team ? team.name : "";
  $("t-contractor").value = team ? team.contractor || "" : "";
  $("t-leader").value = team ? team.leader_name || "" : "";
  $("team-error").classList.add("d-none");
  modal.show();
}

$("btn-add").addEventListener("click", () => open(null));
$("td-rows").addEventListener("click", e => {
  const id = Number(e.target.dataset.edit);
  if (id) open(teams.find(t => t.id === id));
});

$("team-form").addEventListener("submit", async e => {
  e.preventDefault();
  const body = {name: $("t-name").value.trim(), contractor: $("t-contractor").value.trim() || null,
                leader_name: $("t-leader").value.trim() || null};
  try {
    if (!body.name) throw new Error("Cần nhập tên tổ.");
    await SG.api(editing ? "PATCH" : "POST", editing ? `/api/to-doi/${editing}` : "/api/to-doi", body);
    modal.hide();
    SG.toast(editing ? "Đã lưu tổ đội" : "Đã thêm tổ đội");
    load();
  } catch (err) {
    $("team-error").textContent = err.message;
    $("team-error").classList.remove("d-none");
  }
});

load();
