#!/usr/bin/env python3
"""
AIOS Invoice Generator Entrypoint
Запуск автономной генерации счетов-инвойсов для клиентов.
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

from aios_core.invoice_generator import AIOSInvoiceGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunInvoice")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS Invoice Generator")
    parser.add_argument("--client", type=str, required=True, help="Имя заказчика/клиента")
    parser.add_argument("--amount", type=float, required=True, help="Сумма счета в USD")
    parser.add_argument("--desc", type=str, required=True, help="Описание оказанных ИИ-услуг")
    parser.add_argument("--id", type=str, help="Уникальный ID счета (необязательно)")
    args = parser.parse_args()

    generator = AIOSInvoiceGenerator()
    try:
        invoice_path = generator.generate_invoice_html(
            client_name=args.client,
            amount_usd=args.amount,
            service_desc=args.desc,
            invoice_id=args.id
        )
        print(json.dumps({
            "status": "success",
            "message": "Интерактивный HTML счет успешно выписан",
            "invoice_path": invoice_path
        }, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
