#!/usr/bin/env python3
"""
AIOS Order Extractor Runner
Парсинг данных доставки из текста клиента и генерация команды ТТН.
"""
import sys
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from aios_core.order_extractor import AIOSOrderExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.RunOrderExtractor")

def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = "Здравствуйте! Отправьте радиатор на ВАЗ 2109 наложенным платежом. Получатель: Коваленко Максим Сергеевич, тел 0671234567, город Полтава, Новая Почта отделение 7."
        
    extractor = AIOSOrderExtractor()
    res = extractor.extract_delivery_details(text)
    print("\n=== AIOS ORDER EXTRACTOR RESULT ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
