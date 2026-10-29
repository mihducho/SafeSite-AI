/* Trang Ca lam (/ca-lam): sua ca mac dinh. */
"use strict";

const $ = id => document.getElementById(id);
const FIELDS = {name: "s-name", start_time: "s-start", end_time: "s-end", break_start: "s-break-start",
                break_minutes: "s-break", grace_minutes: "s-grace", early_checkin_minutes: "s-early"};

async function load() {
  try {
    const s = await SG.api("GET", "/api/ca-lam");
    for (const [k, id] of Object.entries(FIELDS)) $(id).value = s[k];
  } catch (e) { SG.toast(e.message, "danger"); }
}

$("shift-form").addEventListener("submit", async e => {
  e.preventDefault();
  const body = {};
  const TIMES = {start_time: "Giờ bắt đầu", end_time: "Giờ kết thúc", break_start: "Giờ bắt đầu nghỉ trưa"};
  try {
    for (const [k, id] of Object.entries(FIELDS)) {
      const v = $(id).value.trim();
      body[k] = TIMES[k] ? SG.hhmm($(id), TIMES[k]) : $(id).type === "number" ? (v === "" ? null : Number(v)) : (v || null);
    }
    const r = await SG.api("PATCH", "/api/ca-lam", body);
    $("s-error").classList.add("d-none");
    SG.toast(`Đã lưu ca làm${r.so_dong_tinh_lai ? `, tính lại ${r.so_dong_tinh_lai} dòng bảng công hôm nay` : ""}`);
    load();
  } catch (err) {
    $("s-error").textContent = err.message;
    $("s-error").classList.remove("d-none");
  }
});

load();
