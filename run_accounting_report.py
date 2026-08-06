#!/usr/bin/env python3
"""
AIOS Financial Report Generator Entrypoint
Запуск автономной генерации финансовых отчетов Excel (.xlsx).
"""

import sys
import os
import argparse
import logging
import json
from pathlib import Path

# Убедимся, что корень проекта импортируем
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aios_core.accounting_reporter import AIOSAccountingReporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunAccounting")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS Financial Report Generator")
    parser.add_argument("--output", type=str, default="/root/AIOS/data/aios_financial_report.xlsx", help="Путь сохранения файла Excel")
    args = parser.parse_args()

    reporter = AIOSAccountingReporter()
    try:
        report_path = reporter.generate_excel_report(args.output)
        print(json.dumps({
            "status": "success",
            "message": "Финансовый отчет Excel успешно сгенерирован",
            "report_path": report_path
        }, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
