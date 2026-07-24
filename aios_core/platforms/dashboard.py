"""Ops-dashboard: самодостаточная HTML-панель поверх pull-first REST-plane.

Панель — это read-only наблюдатель: она только читает REST-эндпоинты
(``/api/v1/shards/jobs``, ``/api/v1/shards/stats``, ``/api/v1/devices``,
``/api/v1/profiles``, ``/api/v1/shards``) и рендерит очередь джобов,
пул устройств, профили и шард-хосты. Никаких действий из UI: guarded-
философия не нарушается — мутации остаются за CLI/REST с явными вызовами.

HTML полностью инлайновый (стили + JS внутри документа, без CDN), поэтому
страница работает и из офлайн-просмотрщика: данные просто не подгрузятся,
но каркас панели виден. Все current-version подписи — «AIOS Ops».
"""

from __future__ import annotations

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #0d1117; --panel: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --ok: #3fb950; --warn: #d29922; --bad: #f85149;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px; background: var(--bg); color: var(--text);
    font: 14px/1.5 -apple-system, "Segoe UI", Roboto, sans-serif;
  }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ color: var(--muted); margin-bottom: 20px; }}
  .grid {{
    display: grid; gap: 16px;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  }}
  .panel {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; padding: 14px 16px; min-height: 120px;
  }}
  .panel h2 {{
    font-size: 13px; text-transform: uppercase; letter-spacing: .06em;
    color: var(--muted); margin: 0 0 10px;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{
    text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--border);
  }}
  th {{ color: var(--muted); font-weight: 600; }}
  .pill {{
    display: inline-block; padding: 1px 8px; border-radius: 10px;
    font-size: 12px; border: 1px solid var(--border);
  }}
  .pill.pending {{ color: var(--warn); }}
  .pill.claimed {{ color: var(--accent); }}
  .pill.done {{ color: var(--ok); }}
  .pill.failed {{ color: var(--bad); }}
  .stat {{ display: flex; justify-content: space-between; padding: 4px 0; }}
  .stat b {{ font-variant-numeric: tabular-nums; }}
  .err {{ color: var(--warn); font-size: 12px; margin-top: 6px; }}
  .foot {{ color: var(--muted); font-size: 12px; margin-top: 18px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="sub">read-only наблюдатель очереди, устройств, профилей и шардов ·
обновление каждые {refresh} с · guarded: действий из UI нет</div>
<div class="grid">
  <section class="panel" id="panel-stats">
    <h2>Очередь джобов — статистика</h2>
    <div id="stats">…</div>
    <div class="err" id="stats-err" hidden></div>
  </section>
  <section class="panel" id="panel-jobs">
    <h2>Очередь джобов — последние</h2>
    <div id="jobs">…</div>
    <div class="err" id="jobs-err" hidden></div>
  </section>
  <section class="panel" id="panel-devices">
    <h2>Пул устройств</h2>
    <div id="devices">…</div>
    <div class="err" id="devices-err" hidden></div>
  </section>
  <section class="panel" id="panel-profiles">
    <h2>Профили</h2>
    <div id="profiles">…</div>
    <div class="err" id="profiles-err" hidden></div>
  </section>
  <section class="panel" id="panel-shards">
    <h2>Шард-хосты</h2>
    <div id="shards">…</div>
    <div class="err" id="shards-err" hidden></div>
  </section>
</div>
<div class="foot">AIOS Ops · guarded-pull architecture · v9.5 · <span id="uptime">—</span></div>
<script>
const API = "{api_prefix}";
const REFRESH_MS = {refresh_ms};
let startMs = Date.now();
function uptime() {{ const s = Math.floor((Date.now() - startMs) / 1000); const m = Math.floor(s / 60), h = Math.floor(m / 60); document.getElementById("uptime").textContent = h > 0 ? h + "h " + (m % 60) + "m" : m + "m " + (s % 60) + "s"; }}
setInterval(uptime, 1000);

async function load(id, path, render) {{
  const box = document.getElementById(id);
  const errBox = document.getElementById(id + "-err");
  try {{
    const res = await fetch(API + path);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();
    box.innerHTML = render(data);
    errBox.hidden = true;
  }} catch (e) {{
    errBox.textContent = "нет связи с API: " + e.message +
      " (офлайн-просмотр — каркас без данных)";
    errBox.hidden = false;
  }}
}}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({{
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
}})[c]);

function renderStats(d) {{
  return [
    ["pending", d.pending], ["claimed", d.claimed], ["done", d.done],
    ["failed", d.failed], ["queue_depth", d.queue_depth],
    ["stale_claimed", d.stale_claimed], ["heartbeats", d.heartbeats],
  ].map(([k, v]) =>
    `<div class="stat"><span>${{k}}</span><b>${{v ?? 0}}</b></div>`).join("");
}}

function renderJobs(d) {{
  const rows = (d.jobs || []).slice(0, 12).map((j) =>
    `<tr><td>#${{j.id}}</td><td>${{esc(j.profile_key)}}</td>` +
    `<td>${{esc(j.kind)}}</td>` +
    `<td><span class="pill ${{esc(j.status)}}">${{esc(j.status)}}</span></td></tr>`
  ).join("");
  if (!rows) return "<i>очередь пуста</i>";
  return `<table><tr><th>id</th><th>профиль</th><th>вид</th>` +
    `<th>статус</th></tr>${{rows}}</table>`;
}}

function renderDevices(d) {{
  const rows = (d.devices || []).map((x) =>
    `<tr><td>${{esc(x.serial || x.name || x.id)}}</td>` +
    `<td>${{esc(x.status || (x.lease ? "leased" : "free"))}}</td></tr>`
  ).join("");
  if (!rows) return "<i>устройств нет</i>";
  return `<table><tr><th>устройство</th><th>статус</th></tr>${{rows}}</table>`;
}}

function renderProfiles(d) {{
  const rows = (d.profiles || []).map((p) =>
    `<tr><td>${{esc(p.platform)}}</td><td>${{esc(p.name)}}</td>` +
    `<td>${{esc(p.device_serial || "—")}}</td></tr>`
  ).join("");
  if (!rows) return "<i>профилей нет</i>";
  return `<table><tr><th>платформа</th><th>профиль</th>` +
    `<th>устройство</th></tr>${{rows}}</table>`;
}}

function renderShards(d) {{
  const rows = (d.hosts || d.shards || []).map((h) =>
    `<tr><td>${{esc(h.host || h.name)}}</td>` +
    `<td>${{esc(h.base_url || h.url || "")}}</td></tr>`
  ).join("");
  if (!rows) return "<i>хостов нет</i>";
  return `<table><tr><th>host</th><th>base_url</th></tr>${{rows}}</table>`;
}}

function tick() {{
  load("stats", "/shards/stats", renderStats);
  load("jobs", "/shards/jobs", renderJobs);
  load("devices", "/devices", renderDevices);
  load("profiles", "/profiles", renderProfiles);
  load("shards", "/shards", renderShards);
}}

tick();
setInterval(tick, REFRESH_MS);
</script>
</body>
</html>
"""


def dashboard_html(
    *,
    title: str = "AIOS Ops",
    api_prefix: str = "/api/v1",
    refresh_s: int = 5,
) -> str:
    """Рендерит самодостаточную HTML-панель ops-наблюдателя.

    Args:
        title: заголовок страницы.
        api_prefix: префикс REST-plane, откуда панель тянет данные.
        refresh_s: период автообновления данных, секунд.

    Returns:
        Полный HTML-документ (инлайн CSS/JS, без внешних зависимостей).
    """
    return _DASHBOARD_HTML.format(
        title=title,
        api_prefix=api_prefix,
        refresh=refresh_s,
        refresh_ms=int(refresh_s * 1000),
    )
