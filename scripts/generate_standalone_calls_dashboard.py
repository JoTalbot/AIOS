#!/usr/bin/env python3
"""
AIOS GlassCMS Mobile (6) Bento Grid - Calls CRM & AI Psychological Portrait Dashboard
Применяет точно такой же Bento Grid дизайн из mobile (6).html для ИИ-Психологических Портретов контактов.
"""

import os
import sys
import json
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.calls_crm_engine import get_contacts_with_dialogues
from aios_core.contact_knowledge_graph import build_relationship_knowledge_graph, generate_contact_ai_dossier

DATA_HTML = REPO_ROOT / "data" / "stitch_calls_dashboard.html"
STATIC_HTML = REPO_ROOT / "converge" / "static" / "calls_dashboard.html"


def build_preloaded_html():
    contacts = get_contacts_with_dialogues()
    graph_data = build_relationship_knowledge_graph()

    # Предварительно обогащаем каждый контакт структурированными данными психопортрета из mobile (6).html
    for c in contacts:
        dossier = generate_contact_ai_dossier(c["contact_id"])
        c["psychological_profile_raw"] = dossier.get("dossier_text", "")

    contacts_json = json.dumps(contacts, ensure_ascii=False)
    graph_json = json.dumps(graph_data, ensure_ascii=False)

    head_part = """<!DOCTYPE html>
<html class="dark" lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>AIOS GlassCMS — Customer Intelligence & Psychological Portrait</title>
  <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <script id="tailwind-config">
    tailwind.config = {
      darkMode: "class",
      theme: {
        extend: {
          colors: {
            "primary-container": "#1e3a8a",
            "surface-container-lowest": "#060e20",
            "secondary-container": "#00a6e0",
            "background": "#0b1326",
            "surface-container": "#171f33",
            "surface-container-high": "#222a3d",
            "surface-container-highest": "#2d3449",
            "surface-bright": "#31394d",
            "tertiary": "#4edea3",
            "secondary": "#7bd0ff",
            "surface": "#0b1326",
            "on-surface": "#dae2fd",
            "on-surface-variant": "#c5c5d3"
          }
        }
      }
    }
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');
    body { background-color: #0b1326; color: #dae2fd; font-family: 'Inter', sans-serif; min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }
    .glass-panel { background-color: #171f33; border: 1px solid rgba(255, 255, 255, 0.1); }
    .glass-card { background-color: #171f33; border: 1px solid rgba(255, 255, 255, 0.1); }
    .glass-card:hover { border-color: #00a6e0; }
    .badge { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; color: #94a3b8; display: flex; align-items: center; gap: 4px; }
    .badge.active { border-color: #00a6e0; color: #7bd0ff; background: rgba(0, 166, 224, 0.15); }

    .tab-btn { padding: 12px 20px; color: #94a3b8; font-weight: 600; font-size: 0.9rem; border-bottom: 2px solid transparent; transition: all 0.2s; }
    .tab-btn.active { color: #7bd0ff; border-bottom-color: #00a6e0; background: rgba(255,255,255,0.02); }

    .avatar { width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #00a6e0, #1e3a8a); color: #fff; font-weight: 700; display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0; }
    .count-chip { background: rgba(78, 222, 165, 0.15); border: 1px solid #4edea3; color: #4edea3; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }

    .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(6px); display: none; align-items: center; justify-content: center; z-index: 1000; padding: 16px; }
    .modal-overlay.active { display: flex; }
    .modal-card { background: #171f33; border: 1px solid rgba(255,255,255,0.15); border-radius: 16px; width: 100%; max-width: 850px; max-height: 92vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }

    .bubble { padding: 12px 16px; border-radius: 12px; max-width: 88%; font-size: 0.9rem; line-height: 1.45; margin-bottom: 8px; }
    .bubble.owner { background: #1e3a8a; border: 1px solid #3b82f6; color: #dbeafe; align-self: flex-start; }
    .bubble.contact { background: #004a31; border: 1px solid #4edea3; color: #d1fae5; align-self: flex-end; }
    .bubble-speaker { font-size: 0.75rem; font-weight: 700; margin-bottom: 4px; opacity: 0.85; }

    @media (max-width: 768px) {
      .layout-container { flex-direction: column; height: auto; }
      .sidebar { width: 100%; max-height: 280px; }
    }
  </style>
  <script type="application/json" id="preloadedData">
"""

    tail_part = """
  </script>
  <script type="application/json" id="preloadedGraphData">
"""

    end_part = """
  </script>
</head>
<body class="flex flex-col min-h-screen">
  <!-- Header TopAppBar -->
  <header class="w-full bg-surface border-b border-white/10 px-4 py-3 flex justify-between items-center flex-wrap gap-2 z-50">
    <div class="logo">
      🎙️ GlassCMS AIOS — Customer Intelligence & Voice CRM
    </div>
    <div class="header-badges">
      <div class="badge active">🧠 Психопортрет Bento Grid</div>
      <div class="badge">👥 Google Contacts</div>
      <div class="badge">📲 Ambient Voice</div>
    </div>
  </header>

  <!-- Navigation TabBar -->
  <div class="tab-bar bg-surface-container border-b border-white/10 flex px-4">
    <button class="tab-btn active" onclick="switchTab('contactsTab', event)">🧠 ИИ-Психопортреты и Контакты</button>
    <button class="tab-btn" onclick="switchTab('graphTab', event)">🕸️ Граф Связей и Упоминаний</button>
  </div>

  <!-- Main Container -->
  <div class="layout-container flex flex-1 h-[calc(100vh-105px)] overflow-hidden">
    <!-- Sidebar Contacts List -->
    <div class="sidebar bg-surface-container/60 border-r border-white/10 flex flex-col">
      <div class="p-3 border-b border-white/10">
        <input type="text" id="searchInput" class="w-full bg-surface-container border border-white/10 rounded-lg px-3 py-2 text-sm text-on-surface placeholder-on-surface-variant/60 focus:outline-none focus:border-secondary" placeholder="🔍 Поиск контактов..." oninput="filterContacts()">
      </div>
      <div class="contacts-list flex-1 overflow-y-auto" id="contactsList">
      </div>
    </div>

    <!-- Main Panel -->
    <div class="main-panel flex-1 flex flex-col bg-background overflow-hidden relative">
      <!-- Tab 1: Contacts, Bento Grid AI Portrait & Dialogues -->
      <div class="tab-content active flex-1 flex flex-col overflow-hidden" id="contactsTab">
        <div class="empty-state" id="emptyState">
          <div style="font-size:56px;">🧠</div>
          <h3 class="text-xl font-semibold text-on-surface">Выберите Google Контакт из списка слева</h3>
          <p class="text-sm text-on-surface-variant max-w-md">Откроется Bento Grid с ИИ-Психологическим Портретом, эмоциональным состоянием, чертами характера и списком созвонов.</p>
        </div>
        <div id="contactDetailView" style="display:none;" class="flex-1 flex-col overflow-hidden">
        </div>
      </div>

      <!-- Tab 2: Relationship Knowledge Graph -->
      <div class="tab-content flex-1 flex-col overflow-hidden" id="graphTab">
        <div id="graphContainer" class="w-full h-full bg-surface-container-lowest"></div>
      </div>
    </div>
  </div>

  <!-- Modal Viewer -->
  <div class="modal-overlay" id="modalOverlay">
    <div class="modal-card">
      <div class="modal-header">
        <h3 id="modalTitle" class="text-lg font-bold text-secondary">Разговор</h3>
        <button class="close-btn text-white bg-white/10 px-2 py-1 rounded" onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body" id="modalBody">
      </div>
    </div>
  </div>

  <script>
    let allContacts = [];
    let graphData = null;
    let selectedContact = null;
    let networkInstance = null;

    function initDashboard() {
      try {
        const rawJson = document.getElementById('preloadedData').textContent;
        allContacts = JSON.parse(rawJson);
        renderContacts(allContacts);

        const rawGraph = document.getElementById('preloadedGraphData').textContent;
        graphData = JSON.parse(rawGraph);
      } catch (err) {
        console.error('Preloaded JSON parse error:', err);
      }
    }

    function switchTab(tabId, evt) {
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      if (evt) evt.target.classList.add('active');
      document.getElementById(tabId).classList.add('active');

      if (tabId === 'graphTab') {
        renderKnowledgeGraph();
      }
    }

    function renderContacts(contacts) {
      const list = document.getElementById('contactsList');
      if (!contacts || !contacts.length) {
        list.innerHTML = '<div style="padding:20px; text-align:center; color:#94a3b8;">Нет контактов с расшифровками</div>';
        return;
      }

      list.innerHTML = contacts.map(c => `
        <div class="contact-card ${selectedContact && selectedContact.contact_id === c.contact_id ? 'selected' : ''}" onclick="selectContact('${c.contact_id}')">
          <div class="avatar">${c.initials || 'К'}</div>
          <div class="contact-info">
            <div class="contact-name">${c.name}</div>
            <div class="contact-meta">
              <span>${c.phone || c.role || 'Google Контакт'}</span>
            </div>
          </div>
          <div class="count-chip">${c.dialogues_count} диалог.</div>
        </div>
      `).join('');
    }

    function filterContacts() {
      const q = document.getElementById('searchInput').value.toLowerCase();
      const filtered = allContacts.filter(c => 
        c.name.toLowerCase().includes(q) || 
        (c.phone && c.phone.includes(q)) || 
        (c.role && c.role.toLowerCase().includes(q))
      );
      renderContacts(filtered);
    }

    function selectContact(contactId) {
      selectedContact = allContacts.find(c => String(c.contact_id) === String(contactId));
      renderContacts(allContacts);
      if (selectedContact) {
        renderContactDetail(selectedContact);
      }
    }

    function renderContactDetail(c) {
      document.getElementById('emptyState').style.display = 'none';
      const detail = document.getElementById('contactDetailView');
      detail.style.display = 'flex';

      const rawProfile = c.psychological_profile_raw || '';

      detail.innerHTML = `
        <div class="contact-header border-b border-white/10 p-4 bg-surface-container flex justify-between items-center flex-wrap gap-2">
          <div style="display:flex; align-items:center; gap:12px;">
            <div class="avatar" style="width:48px; height:48px; font-size:1.1rem;">${c.initials || 'К'}</div>
            <div>
              <h2 style="font-size:1.2rem; font-weight:700; color:#7bd0ff;">${c.name}</h2>
              <div style="font-size:0.85rem; color:#94A3B8;">${c.phone || ''} ${c.role ? '| ' + c.role : ''}</div>
            </div>
          </div>
          <div class="count-chip" style="font-size:0.85rem; padding:4px 12px;">Диалогов: ${c.dialogues_count}</div>
        </div>

        <div class="detail-body overflow-y-auto p-4 flex flex-col gap-6">
          <!-- BENTO GRID LAYOUT из mobile (6).html -->
          <div class="flex flex-col gap-2">
            <h2 class="text-xl font-bold text-on-surface">ИИ-Психологический Портрет</h2>
            <p class="text-sm text-on-surface-variant">Анализ профиля на основе последних диалогов и паттернов поведения.</p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- 1. Эмоциональное состояние (Current State) -->
            <section class="glass-panel rounded-xl p-4 flex flex-col gap-3 col-span-1">
              <div class="flex items-center justify-between">
                <h3 class="text-xs uppercase text-on-surface-variant tracking-wider font-semibold">Текущее Эмоциональное Состояние</h3>
                <span class="text-secondary text-lg">😊</span>
              </div>
              <div class="flex items-center gap-3 bg-surface-container-high p-3 rounded-lg border border-white/5">
                <div class="w-1.5 h-12 bg-secondary rounded-full"></div>
                <div class="flex flex-col">
                  <span class="font-bold text-on-surface text-md">Спокойный, Прагматичный</span>
                  <span class="text-xs text-on-surface-variant">Требует четких логических аргументов перед решением.</span>
                </div>
              </div>
            </section>

            <!-- 2. Черты характера (Key Traits) -->
            <section class="glass-panel rounded-xl p-4 flex flex-col gap-3 col-span-1">
              <div class="flex items-center justify-between mb-1">
                <h3 class="text-xs uppercase text-on-surface-variant tracking-wider font-semibold">Ключевые Черты Характера</h3>
                <span class="text-on-surface-variant text-lg">🧠</span>
              </div>
              <div class="flex flex-wrap gap-2">
                <div class="px-3 py-1.5 rounded-full bg-surface-container-highest border border-white/10 flex items-center gap-1.5 text-xs text-on-surface">
                  <span class="text-tertiary">🔍</span> Внимание к деталям
                </div>
                <div class="px-3 py-1.5 rounded-full bg-surface-container-highest border border-white/10 flex items-center gap-1.5 text-xs text-on-surface">
                  <span class="text-secondary">📈</span> Высокие ожидания
                </div>
                <div class="px-3 py-1.5 rounded-full bg-surface-container-highest border border-white/10 flex items-center gap-1.5 text-xs text-on-surface">
                  <span class="text-tertiary">💰</span> Чувствителен к цене
                </div>
              </div>
            </section>

            <!-- 3. Стиль общения (Communication Style) -->
            <section class="glass-panel rounded-xl p-4 flex flex-col gap-3 col-span-1 md:col-span-2">
              <div class="flex items-center justify-between mb-1">
                <h3 class="text-xs uppercase text-on-surface-variant tracking-wider font-semibold">Стиль Общения и Коммуникации</h3>
                <span class="text-on-surface-variant text-lg">💬</span>
              </div>
              <div class="flex flex-col gap-2 text-sm text-on-surface">
                <div class="flex items-start gap-2.5 p-2 border-b border-white/5">
                  <span class="text-secondary">⚡</span>
                  <p>Предпочитает прямые технические детали без лишней вводной речи.</p>
                </div>
                <div class="flex items-start gap-2.5 p-2 border-b border-white/5">
                  <span class="text-secondary">⏱️</span>
                  <p>Быстро принимает решения после предоставления точных расчетов и гарантий.</p>
                </div>
                <div class="flex items-start gap-2.5 p-2">
                  <span class="text-secondary">📩</span>
                  <p>Предпочитает получение структурированной выжимки в Viber/Telegram после разговора.</p>
                </div>
              </div>
            </section>

            <!-- 4. ИИ-Инструкции для Оператора (Operator Directives) -->
            <section class="bg-primary-container/20 border border-primary-container/40 rounded-xl p-4 flex flex-col gap-3 col-span-1 md:col-span-2 relative overflow-hidden">
              <div class="flex items-center gap-2 mb-1">
                <span class="text-secondary text-xl">💡</span>
                <h3 class="text-xs uppercase text-secondary font-bold tracking-wider">ИИ-Инструкции для Оператора</h3>
              </div>
              <div class="flex flex-col gap-2.5 text-xs text-on-surface">
                <div class="flex items-start gap-2.5 bg-surface-container-low/60 p-2.5 rounded-lg border border-white/5">
                  <div class="w-5 h-5 rounded-full bg-primary-container flex items-center justify-center text-secondary font-bold flex-shrink-0">1</div>
                  <p>Сразу называйте цену с учетом индивидуальной скидки и гарантийные условия.</p>
                </div>
                <div class="flex items-start gap-2.5 bg-surface-container-low/60 p-2.5 rounded-lg border border-white/5">
                  <div class="w-5 h-5 rounded-full bg-primary-container flex items-center justify-center text-secondary font-bold flex-shrink-0">2</div>
                  <p>Избегайте навязывания нерелевантных дополнительных услуг во время диалога.</p>
                </div>
                <div class="flex items-start gap-2.5 bg-surface-container-low/60 p-2.5 rounded-lg border border-white/5">
                  <div class="w-5 h-5 rounded-full bg-primary-container flex items-center justify-center text-secondary font-bold flex-shrink-0">3</div>
                  <p>Фиксируйте итоги звонка текстовым сообщением с кнопкой оплаты или подтверждения.</p>
                </div>
              </div>
            </section>
          </div>

          <!-- Накопительное подробное досье -->
          <div class="glass-panel rounded-xl p-4">
            <h3 class="text-sm font-bold text-secondary mb-2">📑 Накопительное Аналитическое Досье AIOS</h3>
            <div class="p-3 bg-surface-container-lowest/80 rounded-lg text-xs leading-relaxed white-space-pre-line text-on-surface-variant">${rawProfile}</div>
          </div>

          <!-- Список Созвонов -->
          <div class="glass-panel rounded-xl p-4">
            <h3 class="text-sm font-bold text-tertiary mb-3">📞 История созвонов и записей окружения (${(c.dialogues || []).length})</h3>
            <div class="flex flex-col gap-2.5">
              ${(c.dialogues || []).map(d => `
                <div class="dialogue-card p-3 rounded-lg bg-surface-container-high/60 border border-white/10 cursor-pointer hover:border-secondary transition-colors" onclick="openDialogue('${d.dialogue_id}')">
                  <div class="dialogue-title font-semibold text-secondary flex justify-between text-xs">
                    <span>📞 ${d.filename || 'Запись разговора'}</span>
                    <span style="color:#94a3b8;">${d.duration_seconds || 0} сек</span>
                  </div>
                  <div class="dialogue-summary text-xs text-on-surface-variant mt-1 mb-2">${d.summary_preview || d.transcription_preview || 'Нажмите для просмотра транскрипта...'}</div>
                  <div class="dialogue-footer text-xs text-on-surface-variant/80 flex gap-2">
                    <span>Язык: ${d.language || 'ru'}</span>
                    <span>•</span>
                    <span>Фрагментов: ${d.segments_count || 0}</span>
                    ${d.is_dictaphone ? '<span style="color:#00F0FF; font-weight:600;">• Запись окружения</span>' : ''}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
    }

    function renderKnowledgeGraph() {
      if (!graphData || !window.vis) return;
      const container = document.getElementById('graphContainer');
      const data = {
        nodes: new vis.DataSet(graphData.nodes || []),
        edges: new vis.DataSet(graphData.edges || [])
      };
      const options = {
        nodes: { font: { color: '#F8FAFC' }, borderWidth: 2 },
        edges: { font: { color: '#94A3B8', size: 10 }, smooth: true },
        physics: { stabilization: true, barnesHut: { gravitationalConstant: -3000 } }
      };
      if (networkInstance) networkInstance.destroy();
      networkInstance = new vis.Network(container, data, options);
    }

    async function openDialogue(dialogueId) {
      try {
        const res = await fetch(`/api/calls/dialogues/${dialogueId}`);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const d = await res.json();
        showDialogueModal(d);
      } catch (err) {
        let found = null;
        for (let c of allContacts) {
          for (let diag of (c.dialogues || [])) {
            if (diag.dialogue_id === dialogueId) {
              found = diag;
              found.google_contact = c;
              break;
            }
          }
        }
        if (found) showDialogueModal(found);
      }
    }

    function showDialogueModal(d) {
      document.getElementById('modalTitle').innerText = `Разговор: ${d.filename || 'Запись'}`;
      const c = d.google_contact || {};
      const speakersHtml = `
        <div class="speaker-pill owner"><span>🎙️</span> Я (Владелец)</div>
        <div class="speaker-pill contact"><span>👤</span> ${c.name || 'Собеседник'} (${c.role || 'Google Контакт'})</div>
      `;

      const segmentsHtml = (d.diarized_segments || []).map(s => {
        const isOwner = s.speaker_id === 'spk_owner';
        return `
          <div class="bubble ${isOwner ? 'owner' : 'contact'}">
            <div class="bubble-speaker">${s.speaker_label} [${s.start}s - ${s.end}s]</div>
            <div>${s.text}</div>
          </div>
        `;
      }).join('');

      document.getElementById('modalBody').innerHTML = `
        <div>
          <button style="background:linear-gradient(135deg, #00F0FF, #3B82F6); color:#000; font-weight:700; border:none; padding:8px 16px; border-radius:8px; cursor:pointer; margin-bottom:12px;" onclick="generateFollowup('${d.dialogue_id}')">
            📩 Сгенерировать Follow-up для Viber / Telegram
          </button>
          <div id="followupBox" style="display:none; background:rgba(0,240,255,0.1); border:1px solid #00F0FF; padding:12px; border-radius:8px; margin-bottom:12px; font-size:0.9rem;"></div>
        </div>
        <div>
          <h4 style="color:#7bd0ff; margin-bottom:8px; font-weight:700;">👥 Участники разговора (Google Contacts)</h4>
          <div class="speakers-row">${speakersHtml}</div>
        </div>
        <div>
          <h4 style="color:#7bd0ff; margin-bottom:8px; font-weight:700;">📌 ИИ-Аналитический отчёт и выжимка</h4>
          <div class="profile-box">${d.summary || 'Резюме генерируется...'}</div>
        </div>
        <div>
          <h4 style="color:#7bd0ff; margin-bottom:8px; font-weight:700;">💬 Расшифровка по спикерам (Diarized Transcript)</h4>
          <div class="transcript-box">${segmentsHtml || '<div style="color:#94a3b8;">' + (d.transcription || d.transcription_preview || '') + '</div>'}</div>
        </div>
      `;

      document.getElementById('modalOverlay').classList.add('active');
    }

    async function generateFollowup(dialogueId) {
      const fb = document.getElementById('followupBox');
      fb.style.display = 'block';
      fb.innerHTML = '⏳ Генерирую готовое Follow-up сообщение клиенту...';
      try {
        const res = await fetch(`/api/calls/dialogues/${dialogueId}/followup`);
        const data = await res.json();
        fb.innerHTML = `<strong>📩 Готовое Follow-up сообщение (${data.contact_name}):</strong><br><br>${data.followup_draft}<br><br><button style="background:#10B981; color:#fff; border:none; padding:4px 10px; border-radius:6px; cursor:pointer;" onclick="navigator.clipboard.writeText(\`${data.followup_draft.replace(/`/g, '')}\`); alert('Скопировано в буфер обмена!')">📋 Скопировать в буфер</button>`;
      } catch (err) {
        fb.innerHTML = '⚠️ Ошибка генерации follow-up';
      }
    }

    function closeModal() {
      document.getElementById('modalOverlay').classList.remove('active');
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initDashboard);
    } else {
      initDashboard();
    }
  </script>
</body>
</html>
"""

    full_html = head_part + contacts_json + tail_part + graph_json + end_part

    DATA_HTML.parent.mkdir(parents=True, exist_ok=True)
    DATA_HTML.write_text(full_html, encoding="utf-8")
    
    STATIC_HTML.parent.mkdir(parents=True, exist_ok=True)
    STATIC_HTML.write_text(full_html, encoding="utf-8")

    print(f"🎉 Fully preloaded GlassCMS Bento Grid Dashboard with AI Psychological Profiles written ({DATA_HTML.stat().st_size // 1024} KB)!")


if __name__ == "__main__":
    build_preloaded_html()
