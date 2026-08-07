(() => {
  const api = (p) => `/converge/api${p}`;
  let data = null;
  const $ = (id) => document.getElementById(id);

  function esc(s) {
    return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }
  function pill(status) {
    const s = String(status || "unknown");
    const cls = s === "active" || s === "running" ? "ok" : s === "failed" || s === "inactive" ? "bad" : "warn";
    return `<span class="pill ${cls}">${esc(s)}</span>`;
  }

  async function load() {
    const r = await fetch(api("/system"), { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(r.statusText);
    data = await r.json();
    render();
  }

  function render() {
    if (!data) return;
    const h = data.host || {};
    const b = data.business || {};
    $("side-time").textContent = data.server_time || "—";
    $("metrics").innerHTML = [
      ["CPU", `${h.cpu_percent ?? "—"}%`],
      ["RAM", `${h.memory_percent ?? "—"}%`],
      ["DISK", `${h.disk_percent ?? "—"}%`],
      ["UNREAD", b.unread ?? "—"],
    ].map(([k, v]) => `<div class="metric"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join("");

    $("bars").innerHTML = [
      ["CPU", h.cpu_percent],
      ["RAM", h.memory_percent],
      ["Disk", h.disk_percent],
    ].map(([n, v]) => {
      const val = Number(v) || 0;
      return `<div class="bar-row"><span>${esc(n)}</span><div class="bar"><i style="width:${Math.min(100, val)}%"></i></div><span>${esc(val)}%</span></div>`;
    }).join("");

    const agents = data.agents || [];
    $("agents-mini").innerHTML = agents.map((a) =>
      `<div class="agent-row"><div><strong>${esc(a.name)}</strong><div style="color:var(--muted);font-size:12px">${esc(a.role)}</div></div>${pill(a.status)}</div>`
    ).join("");
    $("agents-full").innerHTML = agents.map((a) =>
      `<div class="agent-card"><div class="name">${esc(a.name)}</div><div class="role">${esc(a.role)}</div>${pill(a.status)}</div>`
    ).join("");

    const lines = [
      `AIOS Kernel // ${data.server_time || ""}`,
      `host cpu=${h.cpu_percent}% mem=${h.memory_used_gb}/${h.memory_total_gb}G disk_free=${h.disk_free_gb}G`,
      `inbox=${b.inbox} unread=${b.unread} approvals=${b.pending_approvals} sales=${b.active_sales}`,
      `inventory_skus=${b.inventory_skus} sales_sum=${b.sales_sum} rule=${b.profit_rule}`,
      `phone_gateway=${(data.phone || {}).gateway_unit} brain=${(data.phone || {}).phone_brain_unit}`,
    ];
    const svc = data.services || {};
    Object.entries(svc).forEach(([k, v]) => lines.push(`svc ${k}=${v}`));
    $("console").textContent = lines.join("\n");

    $("biz-metrics").innerHTML = [
      ["Inbox", b.inbox],
      ["Unread", b.unread],
      ["Approvals", b.pending_approvals],
      ["Sales ₴", b.sales_sum],
    ].map(([k, v]) => `<div class="metric"><div class="v">${esc(v)}</div><div class="k">${esc(k)}</div></div>`).join("");

    const inv = data.inventory || [];
    $("inventory").innerHTML = inv.length
      ? inv.map((i) => `<div class="inv-row"><div><strong>${esc(i.name)}</strong><div style="color:var(--muted);font-size:12px">${esc(i.category || "")}</div></div><div>${esc(i.qty)} × ${esc(i.price)}</div></div>`).join("")
      : "<div style='color:var(--muted)'>Склад пуст</div>";

    const sales = data.sales || [];
    $("sales").innerHTML = sales.length
      ? sales.map((s) => `<div class="sale-row"><div><strong>${esc(s.item || s.chat)}</strong><div style="color:var(--muted);font-size:12px">${esc(s.recipient || "")} · ${esc(s.ttn || "no TTN")}</div></div><div>${esc(s.status)} · ${esc(s.amount)}</div></div>`).join("")
      : "<div style='color:var(--muted)'>Нет сделок</div>";

    $("phone-console").textContent = JSON.stringify(data.phone || {}, null, 2);

    $("services").innerHTML = Object.entries(svc).map(([k, v]) =>
      `<div class="svc"><span>${esc(k)}</span>${pill(v)}</div>`
    ).join("");
  }

  document.querySelectorAll(".nav[data-panel]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav[data-panel]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const id = btn.dataset.panel;
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      $("panel-" + id)?.classList.add("active");
      $("page-title").textContent = btn.textContent.trim();
    });
  });
  $("btn-refresh").addEventListener("click", () => load().catch((e) => alert(e.message)));
  load().catch((e) => { $("console").textContent = "load error: " + e.message; });
  setInterval(() => load().catch(() => {}), 20000);
})();
