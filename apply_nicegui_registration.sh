#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "🔍 Ищу главный файл NiceGUI..."

# Ищем файл с ui.run( — это точка входа NiceGUI
MAIN_FILE=$(grep -rl "ui\.run(" --include="*.py" . 2>/dev/null | head -1 || true)

if [ -z "$MAIN_FILE" ]; then
    echo "⚠️  Файл с ui.run() не найден. Создаю отдельный entrypoint..."
    MAIN_FILE="./aios_core/dashboard/app.py"
    mkdir -p aios_core/dashboard
    cat > "$MAIN_FILE" << 'PYEOF'
"""AIOS Dashboard — NiceGUI entrypoint."""
from nicegui import ui

@ui.page('/')
def index():
    ui.label('🐙 AIOS Dashboard').classes('text-h3')
    ui.link('🤖 Шаблоны AI Advisor', '/advisor/templates')

ui.run(title='AIOS', port=8080, reload=True)
PYEOF
    echo "✅ Создан: $MAIN_FILE"
fi

echo "📝 Главный файл: $MAIN_FILE"
echo "🔧 Встраиваю регистрацию страницы шаблонов..."

# Python-скрипт для безопасной вставки кода в найденный файл
python3 << PYSCRIPT
import re
from pathlib import Path

target = Path("$MAIN_FILE")
code = target.read_text(encoding="utf-8")

# --- Блок импортов для вставки ---
imports_block = """
# === AI Advisor Templates (auto-injected) ===
from aios_core.advisor.templates_engine import TemplateEngine
from aios_core.dashboard.views.advisor_templates_view import render_advisor_templates_view

template_engine = TemplateEngine(storage_path="data/templates")

@ui.page('/advisor/templates', title='AI Advisor — Шаблоны')
def advisor_templates_page():
    render_advisor_templates_view(template_engine)
# === END AI Advisor Templates ===
"""

# Проверяем, не вставлено ли уже
if "render_advisor_templates_view" in code:
    print("ℹ️  Страница уже зарегистрирована. Пропускаю.")
else:
    # Вставляем ПЕРЕД строкой ui.run(
    pattern = r"(\n\s*ui\.run\()"
    if re.search(pattern, code):
        code = re.sub(pattern, imports_block + r"\1", code, count=1)
        print("✅ Вставлено перед ui.run()")
    else:
        # Если ui.run() не нашли в явном виде — добавляем в конец
        code += imports_block
        print("✅ Добавлено в конец файла")

    target.write_text(code, encoding="utf-8")
    print(f"✅ Файл обновлён: {target}")
PYSCRIPT

echo ""
echo "================================================"
echo "✅ Задача 2 выполнена!"
echo ""
echo "📋 Проверка:"
echo "   grep -n 'advisor_templates' $MAIN_FILE"
echo ""
echo "🚀 Запуск дашборда:"
echo "   python $MAIN_FILE"
echo "   → Откройте: http://localhost:8080/advisor/templates"
echo "================================================"
