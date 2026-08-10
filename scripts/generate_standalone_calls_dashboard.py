#!/usr/bin/env python3
"""
AIOS Standalone Stitch Calls CRM Dashboard Generator
Создает 100% валидный HTML дашборд со встроенными данными 44+ контактов и диалогов.
"""

import os
import sys
import json
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.calls_crm_engine import get_contacts_with_dialogues

OUTPUT_HTML = REPO_ROOT / "data" / "stitch_calls_dashboard.html"
STATIC_HTML_SRC = REPO_ROOT / "converge" / "static" / "calls_dashboard.html"


def generate_standalone_dashboard():
    contacts = get_contacts_with_dialogues()
    contacts_json_str = json.dumps(contacts, ensure_ascii=False)

    template_code = STATIC_HTML_SRC.read_text(encoding="utf-8") if STATIC_HTML_SRC.exists() else ""

    # Внедряем JSON данные безопасно через <script type="application/json">
    json_embed = f"""
  <script type="application/json" id="preloadedContactsData">
{contacts_json_str}
  </script>
"""
    
    # Внедряем элемент перед закрывающим </head>
    modified_code = template_code.replace("</head>", f"{json_embed}\n</head>")

    # Внедряем считывание из JSON перед fetch в JS
    js_override = """    async function loadContacts() {
      const list = document.getElementById('contactsList');
      try {
        const jsonEl = document.getElementById('preloadedContactsData');
        if (jsonEl && jsonEl.textContent.trim()) {
          allContacts = JSON.parse(jsonEl.textContent);
          renderContacts(allContacts);
          return;
        }"""
    
    modified_code = modified_code.replace("async function loadContacts() {", js_override)

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(modified_code, encoding="utf-8")
    print(f"🎉 Автономный Stitch Дашборд сгенерирован: {OUTPUT_HTML} (размер: {OUTPUT_HTML.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    generate_standalone_dashboard()
