#!/usr/bin/env python3
"""
AIOS Standalone & Preloaded Stitch Calls CRM Dashboard Generator
Поддерживает Граф Связей (Vis.js), ИИ-Досье контактов и расшифровки диктофона.
"""

import os
import sys
import json
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.calls_crm_engine import get_contacts_with_dialogues
from aios_core.contact_knowledge_graph import build_relationship_knowledge_graph

DATA_HTML = REPO_ROOT / "data" / "stitch_calls_dashboard.html"
STATIC_HTML = REPO_ROOT / "converge" / "static" / "calls_dashboard.html"


def build_preloaded_html():
    contacts = get_contacts_with_dialogues()
    graph_data = build_relationship_knowledge_graph()

    contacts_json = json.dumps(contacts, ensure_ascii=False)
    graph_json = json.dumps(graph_data, ensure_ascii=False)

    head_part = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>AIOS Calls CRM, Knowledge Graph & Speaker Diarization — Stitch Dashboard</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {
      --bg: #0F172A;
      --card-bg: #1E293B;
      --card-border: #334155;
      --text: #F8FAFC;
      --text-muted: #94A3B8;
      --accent: #00F0FF;
      --accent-glow: rgba(0, 240, 255, 0.15);
      --owner-bg: #1E3A8A;
      --owner-border: #3B82F6;
      --contact-bg: #064E3B;
      --contact-border: #10B981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }
    
    header { background: #162032; border-bottom: 1px solid var(--card-border); padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
    .logo { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 1.05rem; color: var(--accent); }
    .header-badges { display: flex; gap: 6px; flex-wrap: wrap; }
    .badge { background: rgba(255,255,255,0.06); border: 1px solid var(--card-border); padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; color: var(--text-muted); display: flex; align-items: center; gap: 4px; cursor: pointer; }
    .badge.active { border-color: var(--accent); color: var(--accent); background: var(--accent-glow); }

    .tab-bar { background: #111B2E; border-bottom: 1px solid var(--card-border); display: flex; padding: 0 16px; gap: 4px; }
    .tab-btn { padding: 10px 16px; color: var(--text-muted); font-size: 0.88rem; font-weight: 600; border: none; background: none; cursor: pointer; border-bottom: 2px solid transparent; }
    .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); background: rgba(255,255,255,0.02); }

    .container { display: flex; flex: 1; height: calc(100vh - 100px); min-height: 500px; }
    
    .sidebar { width: 320px; border-right: 1px solid var(--card-border); background: #131D31; display: flex; flex-direction: column; flex-shrink: 0; }
    .search-box { padding: 12px; border-bottom: 1px solid var(--card-border); }
    .search-input { width: 100%; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 8px; padding: 10px 12px; color: var(--text); font-size: 0.9rem; outline: none; }
    .search-input:focus { border-color: var(--accent); }
    
    .contacts-list { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; }
    .contact-card { padding: 12px 14px; border-bottom: 1px solid rgba(255,255,255,0.04); cursor: pointer; transition: background 0.2s; display: flex; align-items: center; gap: 10px; }
    .contact-card:hover { background: rgba(255,255,255,0.04); }
    .contact-card.selected { background: var(--card-bg); border-left: 4px solid var(--accent); }
    
    .avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #00F0FF, #3B82F6); color: #000; font-weight: 700; display: flex; align-items: center; justify-content: center; font-size: 0.95rem; flex-shrink: 0; }
    .contact-info { flex: 1; min-width: 0; }
    .contact-name { font-weight: 600; font-size: 0.92rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .contact-meta { font-size: 0.78rem; color: var(--text-muted); margin-top: 2px; }
    .count-chip { background: var(--accent-glow); border: 1px solid var(--accent); color: var(--accent); padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; flex-shrink: 0; }

    .main-panel { flex: 1; display: flex; flex-direction: column; background: var(--bg); overflow: hidden; position: relative; }
    .tab-content { display: none; flex: 1; flex-direction: column; height: 100%; overflow: hidden; }
    .tab-content.active { display: flex; }

    .empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-muted); gap: 12px; padding: 20px; text-align: center; }
    
    .contact-header { padding: 14px 20px; border-bottom: 1px solid var(--card-border); background: var(--card-bg); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
    .detail-body { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; -webkit-overflow-scrolling: touch; }
    
    .dialogue-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 16px; cursor: pointer; transition: border 0.2s; }
    .dialogue-card:hover { border-color: var(--accent); }
    .dialogue-title { font-weight: 600; font-size: 0.95rem; color: var(--accent); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
    .dialogue-summary { font-size: 0.88rem; color: #CBD5E1; line-height: 1.45; margin-bottom: 10px; }
    .dialogue-footer { display: flex; gap: 10px; font-size: 0.78rem; color: var(--text-muted); align-items: center; flex-wrap: wrap; }

    /* Graph Container */
    #graphContainer { width: 100%; height: 100%; background: #0B1120; }

    /* Modal Viewer */
    .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.82); backdrop-filter: blur(4px); display: none; align-items: center; justify-content: center; z-index: 1000; padding: 12px; }
    .modal-overlay.active { display: flex; }
    .modal-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 16px; width: 100%; max-width: 820px; max-height: 92vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }
    .modal-header { padding: 14px 20px; border-bottom: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center; background: #162032; }
    .modal-body { padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 18px; -webkit-overflow-scrolling: touch; }
    .close-btn { cursor: pointer; font-size: 1.2rem; padding: 4px 8px; border-radius: 6px; background: rgba(255,255,255,0.08); color: #fff; border: none; }
    
    .summary-box { background: rgba(15, 23, 42, 0.7); border: 1px solid var(--card-border); border-radius: 12px; padding: 14px; font-size: 0.9rem; line-height: 1.5; white-space: pre-line; }
    
    .speakers-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 6px; }
    .speaker-pill { padding: 6px 12px; border-radius: 8px; font-size: 0.82rem; font-weight: 600; display: flex; align-items: center; gap: 6px; }
    .speaker-pill.owner { background: var(--owner-bg); border: 1px solid var(--owner-border); color: #93C5FD; }
    .speaker-pill.contact { background: var(--contact-bg); border: 1px solid var(--contact-border); color: #6EE7B7; }

    .transcript-box { display: flex; flex-direction: column; gap: 10px; margin-top: 8px; }
    .bubble { padding: 10px 14px; border-radius: 12px; max-width: 88%; font-size: 0.9rem; line-height: 1.4; }
    .bubble.owner { background: var(--owner-bg); border: 1px solid var(--owner-border); align-self: flex-start; }
    .bubble.contact { background: var(--contact-bg); border: 1px solid var(--contact-border); align-self: flex-end; }
    .bubble-speaker { font-size: 0.75rem; font-weight: 700; margin-bottom: 4px; opacity: 0.85; }

    @media (max-width: 768px) {
      .container { flex-direction: column; height: auto; min-height: auto; }
      .sidebar { width: 100%; max-height: 250px; border-right: none; border-bottom: 1px solid var(--card-border); }
      .main-panel { min-height: 450px; }
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
<body>
  <header>
    <div class="logo">
      🎙️ AIOS Calls & Voice CRM — Google Contacts
    </div>
    <div class="header-badges">
      <div class="badge active">✅ Google Contacts</div>
      <div class="badge">🎙️ Diarization</div>
      <div class="badge">📲 Ambient Voice</div>
    </div>
  </header>

  <div class="tab-bar">
    <button class="tab-btn active" onclick="switchTab('contactsTab')">🎙️ Диалоги Контактов</button>
    <button class="tab-btn" onclick="switchTab('graphTab')">🕸️ Граф Связей и Упоминаний</button>
    <button class="tab-btn" onclick="switchTab('dossierTab')">📑 ИИ-Досье Контакта</button>
  </div>

  <div class="container">
    <div class="sidebar">
      <div class="search-box">
        <input type="text" id="searchInput" class="search-input" placeholder="🔍 Поиск контактов..." oninput="filterContacts()">
      </div>
      <div class="contacts-list" id="contactsList">
      </div>
    </div>

    <div class="main-panel">
      <!-- Tab 1: Contacts & Dialogues -->
      <div class="tab-content active" id="contactsTab">
        <div class="empty-state" id="emptyState">
          <div style="font-size:48px;">📞</div>
          <h3>Выберите Google Контакт из списка слева</h3>
          <p>Отображаются только контакты, с которыми имеются расшифрованные звонки и диктофонные записи.</p>
        </div>
        <div id="contactDetailView" style="display:none; flex:1; flex-direction:column; overflow:hidden;">
        </div>
      </div>

      <!-- Tab 2: Relationship Knowledge Graph -->
      <div class="tab-content" id="graphTab">
        <div id="graphContainer"></div>
      </div>

      <!-- Tab 3: AI Contact Dossier -->
      <div class="tab-content" id="dossierTab">
        <div class="detail-body" id="dossierBody" style="padding:24px;">
          <div class="empty-state">
            <div style="font-size:48px;">📑</div>
            <h3>Выберите контакт слева для генерации ИИ-Досье</h3>
            <p>Накопительный психологический портрет, финансовые договоренности и аналитика взаимоотношений.</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="modal-overlay" id="modalOverlay">
    <div class="modal-card">
      <div class="modal-header">
        <h3 id="modalTitle">Разговор</h3>
        <button class="close-btn" onclick="closeModal()">✕</button>
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

    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      event.target.classList.add('active');
      document.getElementById(tabId).classList.add('active');

      if (tabId === 'graphTab') {
        renderKnowledgeGraph();
      }
    }

    function renderContacts(contacts) {
      const list = document.getElementById('contactsList');
      if (!contacts || !contacts.length) {
        list.innerHTML = '<div style="padding:20px; text-align:center; color:#64748B;">Нет контактов с расшифровками</div>';
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
        loadContactDossier(selectedContact);
      }
    }

    function renderContactDetail(c) {
      document.getElementById('emptyState').style.display = 'none';
      const detail = document.getElementById('contactDetailView');
      detail.style.display = 'flex';
      detail.innerHTML = `
        <div class="contact-header">
          <div style="display:flex; align-items:center; gap:12px;">
            <div class="avatar" style="width:48px; height:48px; font-size:1.1rem;">${c.initials || 'К'}</div>
            <div>
              <h2 style="font-size:1.15rem; font-weight:700;">${c.name}</h2>
              <div style="font-size:0.82rem; color:#94A3B8;">${c.phone || ''} ${c.role ? '| ' + c.role : ''}</div>
            </div>
          </div>
          <div class="count-chip" style="font-size:0.85rem; padding:4px 12px;">Всего диалогов: ${c.dialogues_count}</div>
        </div>
        <div class="detail-body">
          ${(c.dialogues || []).map(d => `
            <div class="dialogue-card" onclick="openDialogue('${d.dialogue_id}')">
              <div class="dialogue-title">
                <span>📞 ${d.filename || 'Запись разговора'}</span>
                <span style="font-size:0.8rem; color:#94A3B8;">${d.duration_seconds || 0} сек</span>
              </div>
              <div class="dialogue-summary">${d.summary_preview || d.transcription_preview || 'Нажмите для просмотра подробного транскрипта...'}</div>
              <div class="dialogue-footer">
                <span>Язык: ${d.language || 'ru'}</span>
                <span>•</span>
                <span>Фрагментов: ${d.segments_count || 0}</span>
                ${d.is_dictaphone ? '<span style="color:#00F0FF; font-weight:600;">• Запись окружения (Диктофон)</span>' : ''}
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    async function loadContactDossier(c) {
      const db = document.getElementById('dossierBody');
      db.innerHTML = `<div style="padding:20px; color:#00F0FF;">⏳ Загрузка и ИИ-анализ накопительного досье для ${c.name}...</div>`;
      try {
        const res = await fetch(`/api/calls/dossier/${c.contact_id}`);
        const data = await res.json();
        db.innerHTML = `
          <div class="contact-header" style="border-radius:12px; margin-bottom:16px;">
            <div>
              <h2 style="font-size:1.2rem; font-weight:700;">📑 ИИ-Досье и Психопортрет: ${data.name}</h2>
              <div style="font-size:0.85rem; color:#94A3B8;">${data.phone} | ${data.role} | Диалогов: ${data.dialogues_count}</div>
            </div>
          </div>
          <div class="summary-box" style="font-size:0.95rem; line-height:1.6;">${data.dossier_text || 'Досье формируется...'}</div>
        `;
      } catch (err) {
        db.innerHTML = `<div class="summary-box">👤 **Досье ${c.name}**:\nВсего диалогов: ${c.dialogues_count} шт.</div>`;
      }
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
          <h4 style="color:#00F0FF; margin-bottom:8px;">👥 Участники разговора (Google Contacts)</h4>
          <div class="speakers-row">${speakersHtml}</div>
        </div>
        <div>
          <h4 style="color:#00F0FF; margin-bottom:8px;">📌 ИИ-Аналитический отчёт и выжимка</h4>
          <div class="summary-box">${d.summary || 'Резюме генерируется...'}</div>
        </div>
        <div>
          <h4 style="color:#00F0FF; margin-bottom:8px;">💬 Расшифровка по спикерам (Diarized Transcript)</h4>
          <div class="transcript-box">${segmentsHtml || '<div style="color:#CBD5E1;">' + (d.transcription || d.transcription_preview || '') + '</div>'}</div>
        </div>
      `;

      document.getElementById('modalOverlay').classList.add('active');
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

    print(f"🎉 Fully preloaded HTML dashboard with Knowledge Graph & AI Dossiers written ({DATA_HTML.stat().st_size // 1024} KB)!")


if __name__ == "__main__":
    build_preloaded_html()
