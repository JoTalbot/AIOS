"""
TULA — Architecture Module Analysis Tool
Для проекта AIOS (JoTalbot/AIOS) — автономный анализ docs/core/
Без привязки к Octopus.
"""
import argparse
import os
from datetime import UTC, datetime


def scan(directory):
    modules = {}
    for entry in sorted(os.listdir(directory)):
        path = os.path.join(directory, entry)
        if not os.path.isfile(path) or not entry.endswith(".md"):
            continue
        # Пропускаем INDEX, ROADMAP, ANALYSIS, REPORT
        if entry in [
            "ARCHITECTURE_ANALYSIS.md",
            "ARCHITECTURE_ROADMAP.md",
            "INDEX.md",
            "ARCHITECTURE_REPORT.md",
            "ARCHITECTURE_COMPLIANCE_MATRIX.md",
        ]:
            continue
        content = open(path, encoding="utf-8").read()
        modules[entry] = {
            "path": path,
            "content": content,
            "has_purpose": "## Purpose" in content,
            "has_core_principle": "## Core Principle" in content,
            "has_sections": content.count("## ") > 2,
        }
    return modules


def generate_report(directory):
    modules = scan(directory)
    report_path = os.path.join(directory, "ARCHITECTURE_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Отчёт TULA — Архитектура AIOS\n\n")
        f.write(f"Дата: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Директория: {directory}\n")
        f.write(f"Модулей найдено: {len(modules)} (ожидается 27)\n\n")
        for name, info in sorted(modules.items()):
            status = "✅" if info["has_purpose"] and info["has_core_principle"] else "⚠️"
            f.write(
                f"- {status} `{name}` — Purpose: {'✅' if info['has_purpose'] else '❌'}, Core: {'✅' if info['has_core_principle'] else '❌'}, Секции: {'✅' if info['has_sections'] else '❌'}\n"
            )
    print(f"📄 Отчёт архитектуры: {report_path}")


def generate_index(directory):
    index_path = os.path.join(directory, "INDEX.md")
    modules = [
        m
        for m in os.listdir(directory)
        if m.endswith(".md")
        and m
        not in [
            "ARCHITECTURE_ANALYSIS.md",
            "ARCHITECTURE_ROADMAP.md",
            "ARCHITECTURE_REPORT.md",
            "ARCHITECTURE_COMPLIANCE_MATRIX.md",
            "INDEX.md",
        ]
    ]
    modules.sort()
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# Указатель архитектуры AIOS (`docs/core/`)\n\n")
        f.write("Всего модулей: 27. Без привязки к Octopus.\n\n")
        f.write("## Полный список\n\n")
        f.writelines(f"- `{m}`\n" for m in modules)
    print(f"📄 Указатель архитектуры: {index_path}")


def generate_matrix(directory):
    matrix_path = os.path.join(directory, "ARCHITECTURE_COMPLIANCE_MATRIX.md")
    mappings = {
        "AIOS_AGENT_MODEL.md": "I, XVII, XXXVII",
        "AIOS_MEMORY_ARCHITECTURE.md": "II, XL, LXIII",
        "AIOS_DATA_MODEL.md": "I, IV, XVIII",
        "AIOS_SECURITY_FRAMEWORK.md": "V, LVI, XXXII",
        "AIOS_TRUST_MODEL.md": "XXII, LVI",
        "AIOS_AUTONOMY_MODEL.md": "VIII, XXXVII, LVII",
        "AIOS_EVOLUTION_ENGINE.md": "XXXV, XXXVI",
        "AIOS_ORCHESTRATOR_ARCHITECTURE.md": "X, XXXI",
        "AIOS_EVENT_SYSTEM.md": "XIX, XX",
        "AIOS_DEPLOYMENT_ARCHITECTURE.md": "XVI",
        "AIOS_COMMUNICATION_ARCHITECTURE.md": "IX, XXIV, LX",
        "AIOS_PROTOCOL_STACK.md": "LX",
        "AIOS_API_ARCHITECTURE.md": "XII, XVI",
        "AIOS_MCP_ARCHITECTURE.md": "XII",
        "AIOS_PLANNER_ARCHITECTURE.md": "X",
        "AIOS_CAPABILITY_ENGINE.md": "XXXV, XXXVI",
        "AIOS_TASK_EXECUTION_MODEL.md": "VIII, XXXV",
        "AIOS_WORKER_RUNTIME.md": "XVII",
        "AIOS_NODE_ARCHITECTURE.md": "I, XVI",
        "AIOS_ORGANIZATION_MODEL.md": "XXXI",
        "AIOS_OBSERVABILITY_ARCHITECTURE.md": "XXII",
        "AIOS_SYNC_ARCHITECTURE.md": "XXXIX",
        "AIOS_STORAGE_ARCHITECTURE.md": "II, XL",
        "AIOS_RESOURCE_MANAGER.md": "XI, XXXIII",
        "AIOS_RUNTIME_LIFECYCLE.md": "XV",
        "AIOS_KNOWLEDGE_EVOLUTION_MODEL.md": "VI, XXXIV, XXXV",
        "AIOS_KNOWLEDGE_OBJECT_MODEL.md": "VI, XXXIV",
        "AIOS_CORE_PRINCIPLES.md": "PREAMBLE, I–V",
    }
    with open(matrix_path, "w", encoding="utf-8") as f:
        f.write("# Матрица соответствия — Архитектура AIOS ↔ Конституция\n\n")
        f.write("| Модуль `core/` | Статьи конституции | Статус |\n")
        f.write("|---|---|---|\n")
        for module in sorted(mappings.keys()):
            articles = mappings[module]
            status = "✅" if os.path.exists(os.path.join(directory, module)) else "❌"
            f.write(f"| `{module}` | {articles} | {status} |\n")
    print(f"📄 Матрица соответствия архитектуры: {matrix_path}")


def main():
    parser = argparse.ArgumentParser(description="TULA — Architecture Analysis Tool")
    parser.add_argument(
        "--scan", metavar="DIR", default="docs/core/", help="Директория архитектуры"
    )
    parser.add_argument("--report", action="store_true", help="Сгенерировать отчёт")
    parser.add_argument("--index", action="store_true", help="Создать INDEX.md")
    parser.add_argument("--matrix", action="store_true", help="Создать матрицу соответствия")
    args = parser.parse_args()
    directory = args.scan
    if args.report:
        generate_report(directory)
    if args.index:
        generate_index(directory)
    if args.matrix:
        generate_matrix(directory)
    # По умолчанию — всё вместе
    if not (args.report or args.index or args.matrix):
        generate_report(directory)
        generate_index(directory)
        generate_matrix(directory)


if __name__ == "__main__":
    main()
