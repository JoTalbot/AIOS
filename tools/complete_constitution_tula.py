#!/usr/bin/env python3
"""
TULA — Tool for Universal Legislative Analysis & Constitution Completion
Для проекта AIOS (JoTalbot/AIOS)  — автономный анализ репозитория (без привязки к Octopus)
Версия: 1.0
Автор: автономный анализатор AIOS
Дата: 2026-07-19
"""

import os
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime

# Цвета для терминала
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Римские цифры для нумерации статей
ROMAN_MAP = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20,
    "XXI": 21, "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25,
    "XXVI": 26, "XXVII": 27, "XXVIII": 28, "XXIX": 29, "XXX": 30,
    "XXXI": 31, "XXXII": 32, "XXXIII": 33, "XXXIV": 34, "XXXV": 35,
    "XXXVI": 36, "XXXVII": 37, "XXXVIII": 38, "XXXIX": 39, "XL": 40,
    "XLI": 41, "XLII": 42, "XLIII": 43, "XLIV": 44, "XLV": 45,
    "XLVI": 46, "XLVII": 47, "XLVIII": 48, "XLIX": 49, "L": 50,
    "LI": 51, "LII": 52, "LIII": 53, "LIV": 54, "LV": 55,
    "LVI": 56, "LVII": 57, "LVIII": 58, "LIX": 59, "LX": 60,
    "LXI": 61, "LXII": 62, "LXIII": 63, "LXIV": 64, "LXV": 65,
    "LXVI": 66, "LXVII": 67,
}

REQUIRED_SECTIONS = [
    "Status:", "Level:", "Scope:",
    "# 1.",  # Definition
    "# 2.",  # Law
    "Constitutional",  # Principle
    "END OF ARTICLE",
]


def roman_to_int(s):
    s = s.upper()
    total = 0
    i = 0
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    while i < len(s):
        if i + 1 < len(s) and values[s[i + 1]] > values[s[i]]:
            total += values[s[i + 1]] - values[s[i]]
            i += 2
        else:
            total += values[s[i]]
            i += 1
    return total


def int_to_roman(num):
    val = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    roman_num = ""
    for value, symbol in val:
        while num >= value:
            roman_num += symbol
            num -= value
    return roman_num


def check_file_name_errors(directory):
    errors = []
    for entry in os.listdir(directory):
        path = os.path.join(directory, entry)
        if not os.path.isfile(path) or not entry.endswith(".md"):
            continue
        if entry.startswith("# "):
            errors.append({"file": entry, "type": "prefixed_with_hash", "suggestion": entry.lstrip("# ")})
        elif entry.startswith("RTICLE-"):
            errors.append({"file": entry, "type": "typo_in_article", "suggestion": entry.replace("RTICLE-", "ARTICLE-", 1)})
    return errors


def fix_file_name_errors(directory, errors):
    for err in errors:
        old_path = os.path.join(directory, err["file"])
        new_path = os.path.join(directory, err["suggestion"])
        if not os.path.exists(new_path):
            os.rename(old_path, new_path)
            print(f"{GREEN}✅ Переименовано: {err['file']} → {err['suggestion']}{RESET}")
        else:
            print(f"{YELLOW}⚠️ Файл {err['suggestion']} уже существует, пропуск.{RESET}")


def scan_articles(directory):
    articles = {}
    for entry in sorted(os.listdir(directory)):
        path = os.path.join(directory, entry)
        if not os.path.isfile(path) or not entry.endswith(".md"):
            continue
        # Пропускаем Preamble и другие не-статьи
        if entry.startswith("ARTICLE-") or entry.startswith("# ARTICLE-") or entry.startswith("RTICLE-"):
            # Извлекаем римскую цифру
            match = re.search(r"ARTICLE-([IVXLCDM]+)-", entry)
            if match:
                num_str = match.group(1)
                num = roman_to_int(num_str)
                articles[num] = {"file": entry, "path": path, "content": open(path, "r", encoding="utf-8").read()}
    return articles


def check_article_completeness(article_num, info):
    content = info["content"]
    issues = []
    # Проверка обязательных секций
    for sec in REQUIRED_SECTIONS:
        if sec not in content:
            issues.append(f"Отсутствует секция: {sec}")
    # Проверка END
    if "END OF ARTICLE" not in content:
        issues.append("Отсутствует завершающий маркер END OF ARTICLE")
    return issues


def generate_report(directory, fix=False):
    print(f"{BOLD}{BLUE}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{BLUE}║  TULA — Tool for Universal Legislative Analysis               ║{RESET}")
    print(f"{BOLD}{BLUE}║  Анализ конституции AIOS (JoTalbot/AIOS)                      ║{RESET}")
    print(f"{BOLD}{BLUE}╚══════════════════════════════════════════════════════════════╝{RESET}")
    print()
    print(f"{BLUE}📂 Анализируем: {directory}{RESET}")
    print(f"{BLUE}⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print()

    # Проверка ошибок имён
    errors = check_file_name_errors(directory)
    if errors:
        print(f"{YELLOW}⚠️ Обнаружены ошибки в именах файлов ({len(errors)}):{RESET}")
        for e in errors:
            print(f"   - {e['file']} → {e['suggestion']} (тип: {e['type']})")
        if fix:
            print(f"{BLUE}🔧 Применяем исправления (--fix)...{RESET}")
            fix_file_name_errors(directory, errors)
    else:
        print(f"{GREEN}✅ Ошибок в именах файлов не обнаружено.{RESET}")
    print()

    # Сканирование статей
    articles = scan_articles(directory)
    print(f"{BLUE}📊 Найдено статей: {len(articles)} (ожидается I–LXVII = 67){RESET}")
    
    all_numbers = sorted(articles.keys())
    min_num = min(all_numbers) if all_numbers else 1
    max_num = max(all_numbers) if all_numbers else 67
    expected = list(range(min_num, max_num + 1))
    missing = [n for n in expected if n not in articles]
    
    if missing:
        print(f"{RED}❌ Пропущенные номера: {missing}{RESET}")
    else:
        print(f"{GREEN}✅ Пропущенных номеров нет (диапазон {min_num}–{max_num}).{RESET}")
    
    # Проверка полноты каждой статьи
    incomplete = {}
    for num in sorted(articles.keys()):
        info = articles[num]
        file_name = info["file"]
        issues = check_article_completeness(num, info)
        if issues:
            incomplete[num] = {"file": file_name, "issues": issues}
        else:
            print(f"{GREEN}✅ {int_to_roman(num):>5s} ({file_name}) — полная{RESET}")
    
    if incomplete:
        print()
        print(f"{YELLOW}⚠️ Неполные статьи ({len(incomplete)}):{RESET}")
        for num in sorted(incomplete):
            print(f"   - {int_to_roman(num):>5s} ({incomplete[num]['file']}): {', '.join(incomplete[num]['issues'])}")
    else:
        print(f"{GREEN}✅ Все статьи имеют полную структуру.{RESET}")
    
    # Вывод списка всех статей с номерами
    print()
    print(f"{BLUE}📋 Полный список статей:{RESET}")
    for num in sorted(articles.keys()):
        roman = int_to_roman(num)
        print(f"   {roman:>5s} → {articles[num]['file']}")
    
    # Генерация отчёта в файл
    report_path = os.path.join(directory, "CONSTITUTION_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Отчёт TULA — Анализ конституции AIOS\n\n")
        f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Директория: {directory}\n\n")
        f.write(f"## Найдено статей: {len(articles)}\n")
        if missing:
            f.write(f"## Пропущенные номера: {missing}\n")
        f.write(f"## Ошибки имён: {len(errors)}\n")
        if errors:
            for e in errors:
                f.write(f"- `{e['file']}` → `{e['suggestion']}` ({e['type']})\n")
        f.write(f"## Неполные статьи: {len(incomplete)}\n")
        f.write(f"\n## Полный список:\n")
        for num in sorted(articles.keys()):
            roman = int_to_roman(num)
            status = "❌" if num in incomplete else "✅"
            f.write(f"- {status} {roman} — `{articles[num]['file']}`\n")
    print()
    print(f"{BLUE}📄 Отчёт сохранён: {report_path}{RESET}")
    
    return {
        "directory": directory,
        "articles_found": len(articles),
        "errors": errors,
        "missing": missing,
        "incomplete": incomplete,
        "report": report_path,
    }


def generate_template_for_article(article_num):
    roman = int_to_roman(article_num)
    template = f"""# ARTICLE-{roman}-TITLE.md

# ARTICLE {roman} — TITLE
## Constitutional Law of AIOS [Topic Description]

**Status:** Immutable Core Law  
**Level:** Constitutional  
**Scope:** All AIOS [relevant entities/systems]

---

# 1. Definition of [Topic]

[Topic] is the constitutional [description].

---

# 2. Law of [Core Law 1]

AIOS MUST [requirement].

---

# 3. Law of [Core Law 2]

AIOS SHOULD [requirement].

---

# [N]. Constitutional [Topic] Principle

The purpose of [topic] is [purpose statement].

---

# Final Constitutional Rule

AIOS MUST preserve [key elements].

---

**END OF ARTICLE {roman}**
"""
    return template


def create_template(directory, article_num):
    roman = int_to_roman(article_num)
    file_name = f"ARTICLE-{roman}-TITLE.md"
    path = os.path.join(directory, file_name)
    if os.path.exists(path) or os.path.exists(os.path.join(directory, f"# ARTICLE-{roman}-PROTOCOLS.md")):
        print(f"{YELLOW}⚠️ Статья {roman} уже существует.{RESET}")
        return
    content = generate_template_for_article(article_num)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"{GREEN}✅ Создан шаблон: {file_name}{RESET}")


def generate_compliance_matrix(directory):
    matrix_path = os.path.join(directory, "COMPLIANCE_MATRIX.md")
    articles = scan_articles(directory)
    with open(matrix_path, "w", encoding="utf-8") as f:
        f.write("# Матрица соответствия — Конституция AIOS → Реализация\n\n")
        f.write("| Статья | Название | Реализация в репозитории | Статус |\n")
        f.write("|---|---|---|---|\n")
        # Базовая привязка к документам docs/core/
        mappings = {
            1: ("Identity", "docs/core/AIOS_AGENT_MODEL.md", "✅"),
            2: ("Memory", "docs/core/AIOS_MEMORY_ARCHITECTURE.md", "✅"),
            3: ("Authority", "docs/core/AIOS_ORCHESTRATOR_ARCHITECTURE.md", "✅"),
            5: ("Security", "docs/core/AIOS_SECURITY_FRAMEWORK.md", "✅"),
            8: ("Autonomy", "docs/core/AIOS_AUTONOMY_MODEL.md", "✅"),
            10: ("Governance", "docs/core/AIOS_ORCHESTRATOR_ARCHITECTURE.md", "✅"),
            16: ("Architecture", "docs/architecture/AIOS_SYSTEM_ARCHITECTURE.md", "✅"),
            17: ("Agents", "docs/core/AIOS_AGENT_MODEL.md", "✅"),
            30: ("Constitutional Interpretation", "docs/constitution/ARTICLE-XXX-CONSTITUTIONAL-INTERPRETATION.md", "✅"),
            31: ("Governance", "docs/core/AIOS_ORCHESTRATOR_ARCHITECTURE.md", "✅"),
            36: ("Evolution", "docs/core/AIOS_EVOLUTION_ENGINE.md", "✅"),
        }
        for num in sorted(articles.keys()):
            roman = int_to_roman(num)
            file_name = articles[num]["file"]
            # Извлекаем название статьи из файла
            name = file_name.replace("ARTICLE-", "").replace("# ARTICLE-", "").replace("RTICLE-", "").replace(".md", "").split("-")[1:] if "-" in file_name else "Unknown"
            name_str = " ".join(name).title() if isinstance(name, list) and len(name) > 0 else file_name
            # Попытка извлечь название из файла
            match = re.search(r"ARTICLE-[IVXLCDM]+-([A-Z-]+)\.md", file_name)
            if match:
                name_str = match.group(1).replace("-", " ").title()
            mapping = mappings.get(num, (name_str, "—", "📄"))
            f.write(f"| {roman} | {mapping[0]} | {mapping[1]} | {mapping[2]} |\n")
    print(f"{BLUE}📄 Матрица соответствия сохранена: {matrix_path}{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="TULA — Tool for Universal Legislative Analysis & Constitution Completion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python3 complete_constitution_tula.py --scan docs/constitution/
  python3 complete_constitution_tula.py --scan docs/constitution/ --fix
  python3 complete_constitution_tula.py --template 49 --scan docs/constitution/
  python3 complete_constitution_tula.py --matrix docs/constitution/
        """,
    )
    parser.add_argument("--scan", metavar="DIR", default="docs/constitution/", help="Директория с конституцией")
    parser.add_argument("--fix", action="store_true", help="Автоматически исправить ошибки имён файлов")
    parser.add_argument("--template", type=int, metavar="NUM", help="Создать шаблон статьи с номером (римская цифра)")
    parser.add_argument("--matrix", action="store_true", help="Создать матрицу соответствия (COMPLIANCE_MATRIX.md)")
    parser.add_argument("--report", type=str, default="CONSTITUTION_REPORT.md", help="Имя отчёта")
    args = parser.parse_args()

    directory = args.scan
    if not os.path.isdir(directory):
        print(f"{RED}❌ Директория не найдена: {directory}{RESET}")
        sys.exit(1)

    # Обработка флагов
    if args.template:
        create_template(directory, args.template)
        return

    if args.matrix:
        generate_compliance_matrix(directory)
        return

    result = generate_report(directory, fix=args.fix)
    
    # Если всё чисто, выводим финальную сводку
    if not result["missing"] and not result["incomplete"]:
        print()
        print(f"{BOLD}{GREEN}═══════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{GREEN}  КОНСТИТУЦИЯ AIOS — ФОРМАЛЬНО ЗАВЕРШЕНА                     {RESET}")
        print(f"{BOLD}{GREEN}═══════════════════════════════════════════════════════════════{RESET}")
        print(f"{GREEN}Всего статей: {result['articles_found']} (I–LXVII){RESET}")
        print(f"{GREEN}Ошибок имён: {len(result['errors'])}{RESET}")
        print(f"{GREEN}Пропущенных номеров: {len(result['missing'])}{RESET}")
        print(f"{GREEN}Неполных статей: {len(result['incomplete'])}{RESET}")
        print()
        print(f"{BLUE}Следующие шаги (см. CONSTITUTION_ROADMAP.md):{RESET}")
        print(f"  1. Исправить ошибки имён (если --fix не использовался)")
        print(f"  2. Запустить --matrix для генерации матрицы соответствия")
        print(f"  3. Добавить ссылку на конституцию в docs/ (см. CONSTITUTION_ROADMAP.md)")
        print(f"  4. Обновить AIOS_BOOTSTRAP.md (добавить шаг проверки соответствия)")
        print()
    else:
        print()
        print(f"{BOLD}{YELLOW}═══════════════════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{YELLOW}  ТРЕБУЕТСЯ ДООБРАБОТКА КОНСТИТУЦИИ                       {RESET}")
        print(f"{BOLD}{YELLOW}═══════════════════════════════════════════════════════════════{RESET}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
