#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

MAIN_FILE=$(grep -rl "ui\.run(" --include="*.py" . 2>/dev/null | head -1 || true)

if [ -z "$MAIN_FILE" ]; then
    echo "⚠️  Файл с ui.run() не найден. Используйте существующий entrypoint."
    exit 1
fi

python3 << PYSCRIPT
import re
from pathlib import Path

target = Path("$MAIN_FILE")
code = target.read_text(encoding="utf-8")

imports_block = """
# === AI Advisor Metrics (auto-injected) ===
from aios_core.advisor.metrics_collector import MetricsCollector
from aios_core.dashboard.views.metrics_view import render_metrics_view

metrics_collector = MetricsCollector(storage_path="data/metrics")

@ui.page('/advisor/metrics', title='AI Advisor — Метрики')
def advisor_metrics_page():
    render_metrics_view(metrics_collector)
# === END AI Advisor Metrics ===
"""

if "render_metrics_view" not in code:
    pattern = r"(\n\s*ui\.run\()"
    if re.search(pattern, code):
        code = re.sub(pattern, imports_block + r"\1", code, count=1)
    else:
        code += imports_block
    target.write_text(code, encoding="utf-8")
    print(f"✅ Страница метрик зарегистрирована в {target}")
else:
    print("ℹ️  Страница уже зарегистрирована")
PYSCRIPT
