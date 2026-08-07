(() => {
  const BASE = (() => {
    const p = location.pathname.replace(/\/index\.html$/, "");
    if (p.includes("/converge")) {
      const i = p.indexOf("/converge");
      return (p.slice(0, i + "/converge".length)).replace(/\/+$/, "") || "/converge";
    }
    return p.replace(/\/+$/, "") || "";
  })();
  const api = (path) => `${BASE}/api${path}`;

  const state = {
    tab: "chats",
    channel: "all",
    qChats: "",
    qContacts: "",
    chats: [],
    contacts: [],
    services: [],
    settings: null,
    thread: null,
    templates: [],
    unreadTotal: 0,
    lastFailedText: "",
    variants: null,
    variantsLoading: false,
  };

  const $ = (id) => document.getElementById(id);
  const els = {
    listChats: $("list-chats"),
    listContacts: $("list-contacts"),
    listServices: $("list-services"),
    emptyChats: $("empty-chats"),
    emptyContacts: $("empty-contacts"),
    profileCard: $("profile-card"),
    settingsList: $("settings-list"),
    statsGrid: $("stats-grid"),
    thread: $("thread"),
    brand: $("brand"),
    chatHead: $("chat-head"),
    threadHeader: $("thread-header"),
    chatTitle: $("chat-title"),
    chatSub: $("chat-sub"),
    chatAvatar: $("chat-avatar"),
    chatChannelBadge: $("chat-channel-badge"),
    btnBack: $("btn-back"),
    bottomNav: $("bottom-nav"),
    topbarActions: $("topbar-actions"),
    threadActions: $("thread-actions"),
    btnRefresh: $("btn-refresh"),
    btnSearchToggle: $("btn-search-toggle"),
    chipsChats: $("chips-chats"),
    chipsContacts: $("chips-contacts"),
    searchChats: $("search-chats"),
    searchContacts: $("search-contacts"),
    toast: $("toast"),
    loading: $("loading"),
    brandAvatar: $("brand-avatar"),
  };

  const CHANNELS = [
    { id: "all", label: "Все" },
    { id: "olx", label: "OLX" },
    { id: "tg", label: "Telegram" },
    { id: "viber", label: "Viber" },
    { id: "ig", label: "Instagram" },
    { id: "messenger", label: "Messenger" },
    { id: "signal", label: "Signal" },
    { id: "whatsapp", label: "WhatsApp" },
    { id: "approval", label: "AIOS" },
  ];

  const CHANNEL_ICON = {
    tg: "send",
    telegram: "send",
    olx: "storefront",
    ig: "photo_camera",
    instagram: "photo_camera",
    messenger: "chat",
    facebook: "chat",
    fb: "chat",
    viber: "call",
    whatsapp: "chat",
    wa: "chat",
    signal: "lock",
    android: "smartphone",
    approval: "smart_toy",
    crm: "badge",
    sale: "local_shipping",
  };

  function toast(msg, ms = 2600) {
    els.toast.textContent = msg;
    els.toast.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.add("hidden"), ms);
  }

  function setLoading(v) {
    els.loading.classList.toggle("hidden", !v);
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function getJSON(url) {
    const r = await fetch(url, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  }

  function avatarStyle(color) {
    const c = color || "#3e90ff";
    return `background:linear-gradient(145deg, ${c}99, ${c})`;
  }

  function renderTemplates() {
    const bar = $("templates-bar");
    if (!bar) return;
    const tpls = state.templates || [];
    if (!tpls.length) {
      bar.innerHTML = "";
      return;
    }
    bar.innerHTML = tpls
      .slice(0, 12)
      .map((t) => `<button type="button" class="tpl-chip" data-text="${esc(t.text || "")}">${esc(t.title || "Шаблон")}</button>`)
      .join("");
  }

  function showView(name) {
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    const el = document.getElementById(`view-${name}`);
    if (el) el.classList.add("active");

    const inThread = name === "thread";
    els.brand.classList.toggle("hidden", inThread);
    els.chatHead.classList.toggle("hidden", !inThread);
    els.threadHeader?.classList.toggle("hidden", !inThread);
    els.btnBack.classList.toggle("hidden", !inThread);
    els.bottomNav.classList.toggle("hidden", inThread);
    els.btnRefresh.classList.toggle("hidden", inThread);
    els.btnSearchToggle.classList.toggle("hidden", inThread);
    els.threadActions.classList.toggle("hidden", !inThread);
    document.getElementById("main").style.paddingBottom = inThread ? "0" : "";
    $("templates-bar")?.classList.toggle("hidden", !inThread);
    $("reply-variants")?.classList.toggle("hidden", !inThread);
    $("variants-sidebar")?.classList.toggle("hidden", !inThread || window.matchMedia("(max-width: 768px)").matches);
    if (!inThread) {
      const gv = $("variants-grid"); if (gv) gv.innerHTML = "";
      const vl = $("variants-loading"); if (vl) vl.classList.add("hidden");
      const sg = document.getElementById("sidebar-variants-grid"); if (sg) sg.innerHTML = "";
      const sl = document.getElementById("sidebar-variants-loading"); if (sl) sl.classList.add("hidden");
    }
    $("thread-toolbar")?.classList.toggle("hidden", !inThread);
    if (inThread) renderTemplates();
  }

  function setTab(tab) {
    state.tab = tab;
    state.thread = null;
    document.querySelectorAll(".nav-item").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === tab);
    });
    showView(tab);
    if (tab === "chats") {
      renderChips(els.chipsChats);
      renderChats();
    }
    if (tab === "contacts") {
      renderChips(els.chipsContacts);
      renderContacts();
    }
    if (tab === "services") renderServices();
    if (tab === "settings") renderSettings();
  }

  function renderChips(container) {
    if (!container) return;
    container.innerHTML = CHANNELS.map((c) => {
      const active = state.channel === c.id;
      return `<button type="button" class="chip ${active ? "active" : ""}" data-ch="${c.id}">${esc(c.label)}</button>`;
    }).join("");
  }

  function filterChats() {
    let items = state.chats.slice();
    if (state.channel && state.channel !== "all") {
      items = items.filter((c) => c.channel === state.channel);
    }
    if (state.qChats) {
      const q = state.qChats.toLowerCase();
      items = items.filter(
        (c) =>
          (c.title || "").toLowerCase().includes(q) ||
          (c.preview || "").toLowerCase().includes(q) ||
          (c.channel_label || "").toLowerCase().includes(q)
      );
    }
    return items;
  }

  function renderChats() {
    const items = filterChats();
    if (!items.length) {
      els.listChats.innerHTML = "";
      els.emptyChats.classList.remove("hidden");
      return;
    }
    els.emptyChats.classList.add("hidden");
    els.listChats.innerHTML = items
      .map((c) => {
        const unread = !!c.unread;
        const ico = CHANNEL_ICON[c.channel] || c.icon || "forum";
        const timeCls = unread ? "unread" : "";
        const nameCls = unread ? "" : "muted";
        const previewCls = unread ? "unread" : "";
        const time = c.date || c.channel_label || "";
        return `
        <div class="chat-row" data-id="${esc(c.id)}" role="button" tabindex="0">
          <div class="avatar-wrap">
            <div class="avatar" style="${avatarStyle(c.color)}">${esc(c.initials || "?")}</div>
            <span class="channel-badge inner" style="background:${esc(c.color || "#3e90ff")}">
              <span class="ms xs fill">${esc(ico)}</span>
            </span>
          </div>
          <div class="chat-row-body">
            <div class="chat-row-top">
              <div class="chat-row-name ${nameCls}">${esc(c.title)}</div>
              <div class="chat-row-time ${timeCls}">${esc(time)}</div>
            </div>
            <div class="chat-row-bottom">
              <div class="chat-row-preview ${previewCls}">${esc(c.preview || c.channel_label || "")}</div>
              ${unread ? `<span class="badge">1</span>` : ""}
            </div>
          </div>
        </div>`;
      })
      .join("");
  }

  function filterContacts() {
    let items = state.contacts.slice();
    if (state.channel && state.channel !== "all") {
      items = items.filter((c) => (c.channels || []).includes(state.channel));
    }
    if (state.qContacts) {
      const q = state.qContacts.toLowerCase();
      items = items.filter(
        (c) =>
          (c.name || "").toLowerCase().includes(q) ||
          (c.status || "").toLowerCase().includes(q) ||
          (c.channel_labels || []).join(" ").toLowerCase().includes(q)
      );
    }
    return items;
  }

  function renderContacts() {
    const items = filterContacts();
    if (!items.length) {
      els.listContacts.innerHTML = "";
      els.emptyContacts.classList.remove("hidden");
      return;
    }
    els.emptyContacts.classList.add("hidden");

    // Group by primary channel label
    const groups = new Map();
    for (const c of items) {
      const key = (c.channel_labels && c.channel_labels[0]) || (c.channels && c.channels[0]) || "Other";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(c);
    }

    let html = "";
    for (const [group, list] of groups) {
      const sample = list[0];
      const ch = (sample.channels && sample.channels[0]) || "";
      const ico = CHANNEL_ICON[ch] || "contacts";
      html += `
        <div class="group-head">
          <span class="ms">${esc(ico)}</span>
          <span>${esc(String(group).toUpperCase())}</span>
        </div>
        <div class="group-line"></div>`;
      for (const c of list) {
        const labels = (c.channel_labels || c.channels || []).join(" · ");
        html += `
        <div class="contact-card" data-contact="${esc(c.name)}" role="button" tabindex="0">
          <div class="avatar md" style="${avatarStyle(c.color)}">${esc(c.initials || "?")}</div>
          <div class="meta">
            <div class="name">${esc(c.name)}</div>
            <div class="status">${esc(c.status || labels)}</div>
          </div>
          <div class="actions">
            <span class="ms">chat</span>
          </div>
        </div>`;
      }
    }
    els.listContacts.innerHTML = html;
  }

  function renderServices() {
    els.listServices.innerHTML = (state.services || [])
      .map((s) => {
        const ok = s.connected || s.status === "active";
        const statusPill = ok
          ? `<span class="pill ok">Connected</span>`
          : s.status === "not_configured"
          ? `<span class="pill">Not configured</span>`
          : `<span class="pill warn">${esc(s.status || "idle")}</span>`;
        const actionLabel = ok ? "Manage Connection" : "Connect Account";
        return `
        <article class="service-card">
          <div class="service-card-top">
            <div class="service-icon" style="background:${esc(s.color || "#3e90ff")}">
              <span class="ms fill">${esc(s.icon || "hub")}</span>
            </div>
            <div style="flex:1;min-width:0">
              <div class="service-name">${esc(s.name)}</div>
              <div class="service-desc">${esc(s.desc || "")}</div>
            </div>
          </div>
          <div class="service-meta">
            ${statusPill}
            ${s.inbox_count ? `<span class="pill info">${esc(s.inbox_count)} в инбоксе</span>` : ""}
          </div>
          <div class="service-actions">
            <button type="button" class="btn-ghost ${ok ? "" : "primary-soft"}" data-service="${esc(s.id)}">
              <span class="ms sm">${ok ? "settings" : "link"}</span>
              ${actionLabel}
            </button>
          </div>
        </article>`;
      })
      .join("");
  }

  function renderSettings() {
    const s = state.settings || {};
    const p = s.profile || {};
    const st = s.stats || {};
    const links = s.links || {};

    els.profileCard.innerHTML = `
      <div class="avatar lg" style="background:linear-gradient(145deg,#3e90ff,#68d3ff);color:#001b3e;position:relative;z-index:1">AI</div>
      <div class="name">${esc(p.name || "AIOS Operator")}</div>
      <div class="id-pill">ID: ${esc(p.id || "USR-AIOS-01")}</div>
      <div class="role-chip"><span class="ms sm">shield</span>${esc(p.role || "Owner / Operator")}</div>
    `;

    els.settingsList.innerHTML = `
      <button type="button" class="settings-item">
        <div class="settings-item-left">
          <div class="settings-ico"><span class="ms">manage_accounts</span></div>
          <div><div class="label">Account</div><div class="hint">Учётные данные и безопасность</div></div>
        </div>
        <span class="ms chev">chevron_right</span>
      </button>
      <button type="button" class="settings-item">
        <div class="settings-item-left">
          <div class="settings-ico"><span class="ms">lock</span></div>
          <div><div class="label">Privacy</div><div class="hint">Данные и видимость · vault AIOS</div></div>
        </div>
        <span class="ms chev">chevron_right</span>
      </button>
      <button type="button" class="settings-item">
        <div class="settings-item-left">
          <div class="settings-ico"><span class="ms">notifications</span></div>
          <div><div class="label">Notifications</div><div class="hint">Алерты через Telegram-бот · unread ${esc(st.unread ?? "—")}</div></div>
        </div>
        <span class="ms chev">chevron_right</span>
      </button>
      <button type="button" class="settings-item">
        <div class="settings-item-left">
          <div class="settings-ico"><span class="ms">palette</span></div>
          <div><div class="label">Appearance</div><div class="hint">Тёмная тема Converge (Stitch)</div></div>
        </div>
        <span class="ms chev">chevron_right</span>
      </button>
      <button type="button" class="settings-item">
        <div class="settings-item-left">
          <div class="settings-ico"><span class="ms">smart_toy</span></div>
          <div><div class="label">AI drafts</div><div class="hint">Ожидают подтверждения: ${esc(st.pending_approvals ?? 0)}</div></div>
        </div>
        <span class="ms chev">chevron_right</span>
      </button>
      <a class="settings-item" href="${esc(links.crm || "/crm/")}">
        <div class="settings-item-left">
          <div class="settings-ico"><span class="ms">badge</span></div>
          <div><div class="label">CRM</div><div class="hint">Открыть AIOS CRM</div></div>
        </div>
        <span class="ms chev">chevron_right</span>
      </a>
      <a class="settings-item" href="${esc(links.parts || "/parts/")}">
        <div class="settings-item-left">
          <div class="settings-ico"><span class="ms">inventory_2</span></div>
          <div><div class="label">Витрина запчастей</div><div class="hint">/parts</div></div>
        </div>
        <span class="ms chev">chevron_right</span>
      </a>
      <a class="settings-item" href="${esc(links.kernel || "/kernel/")}">
        <div class="settings-item-left">
          <div class="settings-ico"><span class="ms">memory</span></div>
          <div><div class="label">AIOS Kernel</div><div class="hint">Операторский dashboard (Stitch)</div></div>
        </div>
        <span class="ms chev">chevron_right</span>
      </a>
    `;

    els.statsGrid.innerHTML = [
      ["Инбокс", st.inbox_items],
      ["Unread", st.unread],
      ["CRM", st.crm_contacts],
      ["Сделки", st.active_sales],
      ["Approvals", st.pending_approvals],
      ["Обновлён", st.inbox_updated_at || "—"],
    ]
      .map(
        ([k, v]) =>
          `<div class="stat"><div class="v">${esc(String(v ?? "—"))}</div><div class="k">${esc(k)}</div></div>`
      )
      .join("");
  }

  function renderThread() {
    const t = state.thread;
    if (!t) return;
    const chat = t.chat || {};
    els.chatTitle.textContent = chat.title || "Чат";
    // Also update thread-header if present (template)
    const thTitle = document.getElementById("chat-title");
    if (thTitle) thTitle.textContent = chat.title || "Чат";
    const thSub = document.getElementById("chat-sub");
    if (thSub) thSub.textContent = `${chat.channel_label || chat.channel || ""}${chat.unread ? " · есть новые" : ""}`;
    els.chatSub.textContent = `${chat.channel_label || chat.channel || ""}${chat.unread ? " · есть новые" : ""}`;
    els.chatAvatar.textContent = chat.initials || "?";
    els.chatAvatar.style = avatarStyle(chat.color || "#3e90ff");
    const ico = CHANNEL_ICON[chat.channel] || "forum";
    els.chatChannelBadge.innerHTML = `<span class="ms xs fill">${ico}</span>`;
    els.chatChannelBadge.style.background = chat.color || "#3e90ff";

    const msgs = t.messages || [];
    let html = `<div class="day-pill">Сегодня</div>`;
    html += msgs
      .map((m) => {
        let role = "inbound";
        if (m.role === "outbound" || m.role === "assistant") role = m.role === "assistant" ? "assistant" : "outbound";
        if (m.role === "system") role = "system";
        const ticks =
          role === "outbound" || role === "assistant"
            ? `<span class="ticks ms xs fill">done_all</span>`
            : "";
        const st = m.status && m.status !== "sent" ? `<span class="status-tag">${esc(m.status)}</span>` : "";
        const pendingCls = m.status === "pending" ? " pending" : m.status === "error" ? " error" : "";
        return `<div class="msg ${role}${pendingCls}">${esc(m.text || "")}${
          m.time || ticks ? `<span class="time">${esc(m.time || "")}${ticks}</span>` : ""
        }${st}</div>`;
      })
      .join("");
    els.thread.innerHTML = html;
    els.thread.scrollTop = els.thread.scrollHeight;
    if (t && t.chat && t.chat.id) {
      fetchVariants(t.chat.id, false);
    }
  }

  const STYLE_META_FALLBACK = {
    delovoy: {label:"ДЕЛОВОЙ", icon:"work", color:"#0058bc"},
    druzheskiy: {label:"ДРУЖЕСКИЙ", icon:"celebration", color:"#006c46"},
    sarkazm: {label:"САРКАЗМ", icon:"sentiment_very_satisfied", color:"#7c4d00"},
    romantichniy: {label:"РОМАНТИЧНЫЙ", icon:"favorite", color:"#ba1a1a"},
    kratko: {label:"КРАТКО", icon:"bolt", color:"#0058bc"},
    razdrazhenno: {label:"РАЗДРАЖЕННО", icon:"mood_bad", color:"#93000a"},
    oficialniy: {label:"ОФИЦИАЛЬНЫЙ", icon:"gavel", color:"#4057a5"},
    yumor: {label:"ЮМОР", icon:"comedy_mask", color:"#a53d00"},
    empatiya: {label:"ЭМПАТИЯ", icon:"volunteer_activism", color:"#2e5c00"},
    vdokhnovlyayushchiy: {label:"ВДОХНОВЛЯЮЩИЙ", icon:"rocket_launch", color:"#004493"},
  };
  function renderVariants(data) {
    const grid = document.getElementById("variants-grid");
    const panel = document.getElementById("reply-variants");
    const loading = document.getElementById("variants-loading");
    if (grid && panel) {
      if (loading) loading.classList.add("hidden");
      if (!data || !data.variants) {
        grid.innerHTML = '<div style="padding:12px;color:var(--on-variant);font-size:13px">Не удалось сгенерировать варианты</div>';
        panel.classList.remove("hidden");
      } else {
        const styles = data.styles || Object.keys(data.variants).map(id => ({id, label: id.toUpperCase(), icon: STYLE_META_FALLBACK[id]?.icon||"chat", color: STYLE_META_FALLBACK[id]?.color||"#0058bc"}));
        let html = "";
        for (const s of styles) {
          const text = data.variants[s.id] || "";
          if (!text) continue;
          const meta = STYLE_META_FALLBACK[s.id] || s;
          const ico = s.icon || meta.icon;
          const col = s.color || meta.color;
          const lbl = s.label || meta.label;
          const emoji = s.id==="delovoy"?"💼": s.id==="druzheskiy"?"🎉": s.id==="sarkazm"?"🙃": s.id==="romantichniy"?"💖": s.id==="kratko"?"⚡": s.id==="razdrazhenno"?"😤": s.id==="oficialniy"?"⚖️": s.id==="yumor"?"😄": s.id==="empatiya"?"🤝":"🚀";
          html += '<div class="variant-card" data-style="'+String(s.id).replace(/&/g,"&amp;").replace(/</g,"&lt;")+'" data-text="'+String(text).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;")+'">'+
            '<div class="variant-ico" style="background:'+String(col).replace(/"/g,"&quot;")+'"><span class="ms fill">'+String(ico).replace(/</g,"&lt;")+'</span></div>'+
            '<div class="variant-body">'+
              '<div class="variant-label" style="color:'+String(col).replace(/"/g,"&quot;")+'">'+String(lbl).replace(/</g,"&lt;")+' '+emoji+'</div>'+
              '<div class="variant-text">'+String(text).replace(/&/g,"&amp;").replace(/</g,"&lt;")+'</div>'+
            '</div></div>';
        }
        grid.innerHTML = html;
        panel.classList.remove("hidden");
      }
    }
    const sGrid = document.getElementById("sidebar-variants-grid");
    const sPanel = document.getElementById("variants-sidebar");
    const sOverlay = document.getElementById("sidebar-overlay");
    const sLoading = document.getElementById("sidebar-variants-loading");
    if (sGrid && sPanel) {
      const styles2 = data.styles || Object.keys(data.variants).map(id => ({id, label: id.toUpperCase(), icon: STYLE_META_FALLBACK[id]?.icon||"chat", color: STYLE_META_FALLBACK[id]?.color||"#0058bc"}));
      let html2 = "";
      for (const s of styles2) {
        const text = data.variants[s.id] || "";
        if (!text) continue;
        const meta = STYLE_META_FALLBACK[s.id] || s;
        const ico = s.icon || meta.icon;
        const col = s.color || meta.color;
        const lbl = s.label || meta.label;
        const emoji = s.id==="delovoy"?"💼": s.id==="druzheskiy"?"🎉": s.id==="sarkazm"?"🙃": s.id==="romantichniy"?"💖": s.id==="kratko"?"⚡": s.id==="razdrazhenno"?"😤": s.id==="oficialniy"?"⚖️": s.id==="yumor"?"😄": s.id==="empatiya"?"🤝":"🚀";
        html2 += '<div class="variant-card" data-style="'+String(s.id).replace(/&/g,"&amp;").replace(/</g,"&lt;")+'" data-text="'+String(text).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;")+'">'+
          '<div class="variant-ico" style="background:'+String(col).replace(/"/g,"&quot;")+'"><span class="ms fill">'+String(ico).replace(/</g,"&lt;")+'</span></div>'+
          '<div class="variant-body">'+
            '<div class="variant-label" style="color:'+String(col).replace(/"/g,"&quot;")+'">'+String(lbl).replace(/</g,"&lt;")+' '+emoji+'</div>'+
            '<div class="variant-text">'+String(text).replace(/&/g,"&amp;").replace(/</g,"&lt;")+'</div>'+
          '</div></div>';
      }
      sGrid.innerHTML = html2;
      if (sLoading) sLoading.classList.add("hidden");
      const isDesktop = window.matchMedia("(min-width: 769px)").matches;
      if (isDesktop && data && data.variants) {
        sPanel.classList.remove("hidden");
        sPanel.classList.add("open");
        if (sOverlay) sOverlay.classList.remove("hidden");
      }
    }
  }
  async function fetchVariants(chatId, force=false) {
    const panel = document.getElementById("reply-variants");
    const grid = document.getElementById("variants-grid");
    const loading = document.getElementById("variants-loading");
    const sPanel = document.getElementById("variants-sidebar");
    const sGrid = document.getElementById("sidebar-variants-grid");
    const sLoading = document.getElementById("sidebar-variants-loading");
    const sOverlay = document.getElementById("sidebar-overlay");
    if (panel) panel.classList.remove("hidden");
    if (loading) loading.classList.remove("hidden");
    if (sPanel) { sPanel.classList.remove("hidden"); if (sLoading) sLoading.classList.remove("hidden"); if (window.matchMedia("(min-width: 769px)").matches && sOverlay) sOverlay.classList.remove("hidden"); }
    try {
      const data = await getJSON(api('/chats/'+encodeURIComponent(chatId)+'/reply-variants'+(force?'?force=1':'')));
      renderVariants(data);
    } catch(e) {
      if (loading) loading.classList.add("hidden");
      if (grid) grid.innerHTML = '<div style="padding:12px;color:var(--on-variant);font-size:13px">Ошибка: '+String(e.message).replace(/</g,"&lt;")+'</div>';
      if (sLoading) sLoading.classList.add("hidden");
      if (sGrid) sGrid.innerHTML = '<div style="padding:12px;color:var(--on-variant);font-size:13px">Ошибка: '+String(e.message).replace(/</g,"&lt;")+'</div>';
    }
  }

  async function loadAll(silent = false) {
    if (!silent) setLoading(true);
    try {
      const [chats, contacts, services, settings, templates] = await Promise.all([
        getJSON(api("/chats")),
        getJSON(api("/contacts")),
        getJSON(api("/services")),
        getJSON(api("/settings")),
        getJSON(api("/templates")).catch(() => ({ templates: [] })),
      ]);
      state.chats = chats.chats || [];
      state.contacts = contacts.contacts || [];
      state.services = services.services || [];
      state.settings = settings;
      state.templates = templates.templates || [];
      state.unreadTotal = chats.unread_total || state.chats.filter((c) => c.unread).length;
      const badge = $("nav-unread");
      if (badge) {
        if (state.unreadTotal > 0) {
          badge.textContent = state.unreadTotal > 99 ? "99+" : String(state.unreadTotal);
          badge.classList.remove("hidden");
        } else badge.classList.add("hidden");
      }
      if (settings?.profile?.name) {
        els.brandAvatar.textContent = (settings.profile.name || "A").slice(0, 1).toUpperCase();
      }
      if (state.tab === "chats" && !state.thread) renderChats();
      if (state.tab === "contacts" && !state.thread) renderContacts();
      if (state.tab === "services" && !state.thread) renderServices();
      if (state.tab === "settings" && !state.thread) renderSettings();
    } catch (e) {
      if (!silent) toast("Ошибка загрузки: " + e.message);
    } finally {
      if (!silent) setLoading(false);
    }
  }

  async function openChat(id) {
    setLoading(true);
    try {
      state.thread = await getJSON(api(`/chats/${encodeURIComponent(id)}`));
      showView("thread");
      renderThread();
    } catch (e) {
      toast("Не удалось открыть чат");
    } finally {
      setLoading(false);
    }
  }

  async function refreshInbox() {
    setLoading(true);
    try {
      const r = await fetch(api("/refresh"), { method: "POST" });
      const j = await r.json().catch(() => ({}));
      toast(j.message || j.status || "Обновление…");
      setTimeout(() => loadAll(true), 2800);
    } catch (e) {
      toast("Ошибка обновления");
    } finally {
      setLoading(false);
    }
  }

  // Events

  function openVariantsSidebar() {
    const p = document.getElementById("variants-sidebar");
    const o = document.getElementById("sidebar-overlay");
    if (p) { p.classList.remove("hidden"); requestAnimationFrame(()=> p.classList.add("open")); }
    if (o) o.classList.remove("hidden");
  }
  function closeVariantsSidebar() {
    const p = document.getElementById("variants-sidebar");
    const o = document.getElementById("sidebar-overlay");
    if (p) p.classList.remove("open");
    setTimeout(()=> { if (p) p.classList.add("hidden"); }, 280);
    if (o) o.classList.add("hidden");
  }
  $("btn-open-variants")?.addEventListener("click", () => {
    const p = document.getElementById("variants-sidebar");
    if (p && p.classList.contains("open")) closeVariantsSidebar();
    else {
      openVariantsSidebar();
      if (state.thread?.chat?.id) fetchVariants(state.thread.chat.id, false);
    }
  });
  $("btn-close-variants")?.addEventListener("click", closeVariantsSidebar);
  $("sidebar-overlay")?.addEventListener("click", closeVariantsSidebar);
  document.getElementById("sidebar-variants-grid")?.addEventListener("click", (e) => {
    const card = e.target.closest(".variant-card");
    if (!card) return;
    const text = card.dataset.text || "";
    const input = document.getElementById("composer-input");
    if (!input || !text) return;
    input.value = text;
    input.focus();
    document.querySelectorAll(".variant-card").forEach(c=>c.classList.remove("selected"));
    card.classList.add("selected");
    if (navigator.vibrate) navigator.vibrate(10);
    if (window.matchMedia("(max-width: 768px)").matches) closeVariantsSidebar();
  });
  $("variants-grid")?.addEventListener("click", (e) => {
    const card = e.target.closest(".variant-card");
    if (!card) return;
    const text = card.dataset.text || "";
    if (!text) return;
    const input = document.getElementById("composer-input");
    if (!input || !text) return;
    input.value = text;
    input.focus();
    document.querySelectorAll(".variant-card").forEach(c=>c.classList.remove("selected"));
    card.classList.add("selected");
    if (navigator.vibrate) navigator.vibrate(10);
  });
  // Bottom AI suggestion + mini-panel (template code.html)
  function updateAiSuggestion(styleId) {
    const bubble = document.getElementById("ai-suggestion-text");
    if (!bubble || !state.variants || !state.variants.variants) return;
    const text = state.variants.variants[styleId] || "";
    if (text) bubble.textContent = text;
  }
  document.querySelectorAll("#style-mini-panel .style-mini-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#style-mini-panel .style-mini-btn").forEach(b=>b.classList.remove("active"));
      btn.classList.add("active");
      const style = btn.dataset.style;
      updateAiSuggestion(style);
      // Also fill composer
      const text = state.variants?.variants?.[style] || "";
      const input = document.getElementById("composer-input");
      if (input && text) {
        input.value = text;
        input.focus();
      }
    });
  });
  document.getElementById("btn-ai-refresh")?.addEventListener("click", () => {
    if (state.thread?.chat?.id) fetchVariants(state.thread.chat.id, true);
  });
  document.getElementById("btn-ai-close")?.addEventListener("click", () => {
    const panel = document.getElementById("ai-suggestion-panel");
    if (panel) panel.style.display = "none";
  });
  document.getElementById("btn-edit-suggestion")?.addEventListener("click", () => {
    const bubble = document.getElementById("ai-suggestion-text");
    const input = document.getElementById("composer-input");
    if (bubble && input) {
      input.value = bubble.textContent || "";
      input.focus();
    }
  });
  $("btn-variants-refresh")?.addEventListener("click", () => {
    const g = document.getElementById("variants-grid");
    const sg = document.getElementById("sidebar-variants-grid");
    if (g) g.innerHTML="";
    if (sg) sg.innerHTML="";
    if (state.thread?.chat?.id) fetchVariants(state.thread.chat.id, true);
  });
  document.getElementById("sidebar-variants-grid")?.addEventListener("click", (e) => {
    const card = e.target.closest(".variant-card");
    if (!card) return;
    const text = card.dataset.text || "";
    const input = document.getElementById("composer-input");
    if (!input || !text) return;
    input.value = text;
    input.focus();
    document.querySelectorAll(".variant-card").forEach(c=>c.classList.remove("selected"));
    card.classList.add("selected");
    if (navigator.vibrate) navigator.vibrate(10);
    if (window.matchMedia("(max-width: 768px)").matches) closeVariantsSidebar();
  });
  $("templates-bar")?.addEventListener("click", (e) => {
    const chip = e.target.closest(".tpl-chip");
    if (!chip) return;
    const input = $("composer-input");
    if (!input) return;
    input.value = chip.dataset.text || "";
    input.focus();
  });

  $("btn-live-read")?.addEventListener("click", async () => {
    if (!state.thread?.chat?.id) return;
    setLoading(true);
    try {
      state.thread = await getJSON(api(`/chats/${encodeURIComponent(state.thread.chat.id)}?live=1`));
      renderThread();
      toast(state.thread.source === "live" ? "Канал прочитан" : "Локальный срез");
    } catch (e) {
      toast("Чтение: " + e.message);
    } finally {
      setLoading(false);
    }
  });

  $("btn-retry-send")?.addEventListener("click", async () => {
    if (!state.thread?.chat?.id) return;
    setLoading(true);
    try {
      const r = await fetch(api(`/chats/${encodeURIComponent(state.thread.chat.id)}/send/retry`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: state.lastFailedText || "" }),
      });
      const j = await r.json().catch(() => ({}));
      if (j.status === "sent") {
        toast("✓ Повторно отправлено");
        state.thread = await getJSON(api(`/chats/${encodeURIComponent(state.thread.chat.id)}`));
        renderThread();
      } else toast("✗ " + (j.error || j.detail || "нечего повторять"));
    } catch (e) {
      toast("Retry: " + e.message);
    } finally {
      setLoading(false);
    }
  });

  function showTtn(prefill = {}) {
    $("ttn-detail").value = prefill.detail || state.thread?.chat?.title || "";
    $("ttn-cost").value = prefill.cost || "";
    $("ttn-recipient").value = prefill.recipient || state.thread?.chat?.title || "";
    $("ttn-phone").value = prefill.phone || "";
    $("ttn-city").value = prefill.city || "";
    $("ttn-warehouse").value = prefill.warehouse || "";
    $("ttn-overlay")?.classList.remove("hidden");
    $("ttn-sheet")?.classList.remove("hidden");
  }
  function hideTtn() {
    $("ttn-overlay")?.classList.add("hidden");
    $("ttn-sheet")?.classList.add("hidden");
  }
  $("btn-biz-ttn")?.addEventListener("click", () => showTtn());
  $("btn-ttn-cancel")?.addEventListener("click", hideTtn);
  $("ttn-overlay")?.addEventListener("click", hideTtn);
  $("btn-ttn-create")?.addEventListener("click", async () => {
    const payload = {
      detail: $("ttn-detail").value.trim(),
      cost: $("ttn-cost").value.trim(),
      recipient: $("ttn-recipient").value.trim(),
      phone: $("ttn-phone").value.trim(),
      city: $("ttn-city").value.trim(),
      warehouse: $("ttn-warehouse").value.trim(),
      confirm: true,
    };
    if (!payload.detail || !payload.cost || !payload.recipient || !payload.phone || !payload.city || !payload.warehouse) {
      toast("Заполните все поля ТТН");
      return;
    }
    setLoading(true);
    try {
      const r = await fetch(api("/business/ttn/create"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const j = await r.json().catch(() => ({}));
      if (j.status === "ok" || j.ttn || j.status === "created") {
        toast("✓ ТТН: " + (j.ttn || j.number || "создана"));
        hideTtn();
        if (state.thread?.chat?.id) {
          const text = `ТТН ${j.ttn || j.number || ""} отправлена.`.trim();
          $("composer-input").value = text;
        }
      } else {
        toast("✗ " + (j.error || j.detail || j.message || "ошибка ТТН"));
      }
    } catch (e) {
      toast("ТТН: " + e.message);
    } finally {
      setLoading(false);
    }
  });

  // remember failed text for retry

  els.bottomNav.addEventListener("click", (e) => {
    const btn = e.target.closest(".nav-item");
    if (btn) setTab(btn.dataset.tab);
  });

  function onChipClick(e) {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    state.channel = chip.dataset.ch;
    renderChips(els.chipsChats);
    renderChips(els.chipsContacts);
    if (state.tab === "chats") renderChats();
    if (state.tab === "contacts") renderContacts();
  }
  els.chipsChats.addEventListener("click", onChipClick);
  els.chipsContacts.addEventListener("click", onChipClick);

  els.listChats.addEventListener("click", (e) => {
    const row = e.target.closest(".chat-row");
    if (row?.dataset.id) openChat(row.dataset.id);
  });
  els.listContacts.addEventListener("click", (e) => {
    const card = e.target.closest(".contact-card");
    if (!card) return;
    const name = card.dataset.contact;
    const chat = state.chats.find((c) => c.title === name);
    if (chat) openChat(chat.id);
    else toast("Чата в инбоксе нет — только контакт");
  });

  els.listServices.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-service]");
    if (!btn) return;
    toast("Управление сервисом — через systemd / Telegram-бот AIOS");
  });

  els.btnBack.addEventListener("click", () => setTab(state.tab === "thread" ? "chats" : state.tab || "chats"));
  els.btnRefresh.addEventListener("click", refreshInbox);
  $("btn-empty-refresh")?.addEventListener("click", refreshInbox);
  els.btnSearchToggle.addEventListener("click", () => {
    if (state.tab === "chats") {
      els.searchChats.focus();
      els.searchChats.select();
    } else if (state.tab === "contacts") {
      els.searchContacts.focus();
    } else {
      setTab("chats");
      setTimeout(() => els.searchChats.focus(), 50);
    }
  });

  els.searchChats.addEventListener("input", () => {
    state.qChats = els.searchChats.value.trim();
    renderChats();
  });
  els.searchContacts.addEventListener("input", () => {
    state.qContacts = els.searchContacts.value.trim();
    renderContacts();
  });

  // ---- Send message flow ----
  const sendUI = {
    overlay: $("send-overlay"),
    sheet: $("confirm-sheet"),
    meta: $("confirm-meta"),
    text: $("confirm-text"),
    btnCancel: $("btn-confirm-cancel"),
    btnSend: $("btn-confirm-send"),
    pending: null,
    busy: false,
  };

  function showConfirm(pending) {
    sendUI.pending = pending;
    const label = pending.channel_label || pending.channel || "";
    const title = pending.title || pending.ref || "";
    sendUI.meta.textContent = `${label} · ${title}`;
    sendUI.text.textContent = pending.text || "";
    sendUI.overlay.classList.remove("hidden");
    sendUI.sheet.classList.remove("hidden");
  }

  function hideConfirm() {
    sendUI.pending = null;
    sendUI.overlay.classList.add("hidden");
    sendUI.sheet.classList.add("hidden");
    sendUI.busy = false;
    sendUI.btnSend.disabled = false;
    sendUI.btnCancel.disabled = false;
    $("composer")?.classList.remove("sending");
  }

  function appendLocalOutbound(text, status) {
    if (!els.thread) return;
    const time = new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
    const div = document.createElement("div");
    div.className = `msg outbound ${status === "pending" ? "pending" : status === "error" ? "error" : ""}`;
    div.innerHTML = `${esc(text)}<span class="time">${esc(time)}<span class="ticks ms xs fill">done_all</span></span>${
      status && status !== "sent" ? `<span class="status-tag">${esc(status)}</span>` : ""
    }`;
    els.thread.appendChild(div);
    els.thread.scrollTop = els.thread.scrollHeight;
  }

  async function stageSend(text) {
    if (!state.thread?.chat?.id) {
      toast("Сначала откройте чат");
      return;
    }
    const chatId = state.thread.chat.id;
    setLoading(true);
    $("composer")?.classList.add("sending");
    try {
      const r = await fetch(api(`/chats/${encodeURIComponent(chatId)}/send`), {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ text, confirm: false }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok && j.status !== "need_confirm") {
        throw new Error(j.detail || j.error || j.message || r.statusText);
      }
      if (j.status === "need_confirm") {
        showConfirm(j);
        appendLocalOutbound(text, "pending");
        $("composer-input").value = "";
        return;
      }
      if (j.status === "sent") {
        appendLocalOutbound(text, "sent");
        $("composer-input").value = "";
        toast("✓ Отправлено");
        // refresh thread
        state.thread = await getJSON(api(`/chats/${encodeURIComponent(chatId)}`));
        renderThread();
        return;
      }
      throw new Error(j.error || j.message || "Неизвестная ошибка");
    } catch (e) {
      toast("Ошибка: " + e.message);
      $("composer")?.classList.remove("sending");
    } finally {
      setLoading(false);
    }
  }

  async function confirmSend() {
    if (!sendUI.pending || sendUI.busy) return;
    sendUI.busy = true;
    sendUI.btnSend.disabled = true;
    sendUI.btnCancel.disabled = true;
    setLoading(true);
    const chatId = sendUI.pending.chat_id || state.thread?.chat?.id;
    try {
      const r = await fetch(api(`/chats/${encodeURIComponent(chatId)}/send`), {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          text: sendUI.pending.text,
          confirm: true,
          pending_id: sendUI.pending.pending_id,
          force: true,
        }),
      });
      const j = await r.json().catch(() => ({}));
      if (j.status === "sent") {
        toast("✓ Отправлено в " + (j.channel_label || j.channel || "канал"));
        hideConfirm();
        if (chatId) {
          state.thread = await getJSON(api(`/chats/${encodeURIComponent(chatId)}`));
          renderThread();
        }
        loadAll(true);
        return;
      }
      const err = j.error || j.detail || j.message || "Ошибка отправки";
      state.lastFailedText = sendUI.pending?.text || "";
      toast("✗ " + err);
      hideConfirm();
      if (chatId) {
        try {
          state.thread = await getJSON(api(`/chats/${encodeURIComponent(chatId)}`));
          renderThread();
        } catch (_) {}
      }
    } catch (e) {
      toast("Ошибка: " + e.message);
      hideConfirm();
    } finally {
      setLoading(false);
      sendUI.busy = false;
    }
  }

  async function cancelSend() {
    const p = sendUI.pending;
    hideConfirm();
    if (!p) return;
    const chatId = p.chat_id || state.thread?.chat?.id;
    try {
      await fetch(api(`/chats/${encodeURIComponent(chatId)}/send/cancel`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pending_id: p.pending_id }),
      });
    } catch (_) {}
    toast("Отменено");
    if (chatId) {
      try {
        state.thread = await getJSON(api(`/chats/${encodeURIComponent(chatId)}`));
        renderThread();
      } catch (_) {}
    }
  }

  $("composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("composer-input").value.trim();
    if (!text) return;
    if (!state.thread?.chat) {
      toast("Откройте чат для ответа");
      return;
    }
    const ch = state.thread.chat.channel;
    if (["approval", "crm", "sale"].includes(ch)) {
      toast("Это системный пункт — выберите чат клиента");
      return;
    }
    stageSend(text);
  });

  sendUI.btnCancel?.addEventListener("click", cancelSend);
  sendUI.btnSend?.addEventListener("click", confirmSend);
  sendUI.overlay?.addEventListener("click", cancelSend);

  els.settingsList?.addEventListener("click", (e) => {
    const item = e.target.closest(".settings-item");
    if (!item || item.tagName === "A") return;
    toast("Раздел настроек — в следующей итерации");
  });

  // SW
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register(`${BASE}/sw.js`).catch(() => {});
  }

  renderChips(els.chipsChats);
  setTab("chats");
  loadAll();
  setInterval(() => loadAll(true), 45000);
})();
