#!/usr/bin/env python3
"""
AIOS Call Invoice & Quotation Generator (25%x4 Split)
Формирует официальный HTML-инвойс и коммерческое предложение по итогам договоренностей из звонка,
с расчетом комиссии и распределением прибыли 25%х4 (Разработчик, Инвестор, Команда, Фонд).
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

INVOICES_DIR = REPO_ROOT / "data" / "invoices"
logger = logging.getLogger("aios.call_invoice")


def generate_call_invoice(contact_name: str, amount_usd: float, item_name: str, dialogue_id: str) -> Dict[str, Any]:
    """Генерирует HTML инвойс с распределением прибыли 25%х4."""
    INVOICES_DIR.mkdir(parents=True, exist_ok=True)
    inv_id = f"inv_call_{hash(dialogue_id + str(amount_usd))}"
    
    # Правило 25%х4
    share = amount_usd * 0.25
    
    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Счёт-Фактура AIOS — {inv_id}</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #0F172A; color: #F8FAFC; padding: 40px; }}
    .invoice-card {{ background: #1E293B; border: 1px solid #334155; border-radius: 16px; padding: 32px; max-width: 650px; margin: 0 auto; }}
    .header {{ border-bottom: 2px solid #00F0FF; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; }}
    .title {{ font-size: 24px; font-weight: bold; color: #00F0FF; }}
    .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
    .table th, .table td {{ padding: 12px; border-bottom: 1px solid #334155; text-align: left; }}
    .total {{ font-size: 20px; font-weight: bold; color: #10B981; margin-top: 16px; }}
    .split-box {{ background: rgba(0, 240, 255, 0.1); border: 1px solid #00F0FF; padding: 16px; border-radius: 8px; margin-top: 20px; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="invoice-card">
    <div class="header">
      <div>
        <div class="title">AIOS Commercial Invoice</div>
        <div style="color: #94A3B8; font-size: 14px;">№ {inv_id} | {datetime.now().strftime("%Y-%m-%d")}</div>
      </div>
      <div style="text-align: right;">
        <div style="font-weight: bold;">Плательщик: {contact_name}</div>
        <div style="color: #94A3B8; font-size: 14px;">По итогам звонка AIOS</div>
      </div>
    </div>

    <table class="table">
      <thead>
        <tr><th>Наименование товара / услуги</th><th>Сумма (USD)</th></tr>
      </thead>
      <tbody>
        <tr><td>{item_name}</td><td>${amount_usd:.2f}</td></tr>
      </tbody>
    </table>

    <div class="total">Итого к оплате: ${amount_usd:.2f} USD</div>

    <div class="split-box">
      <strong>📊 Распределение дохода 25%х4 (AIOS Profit Distribution):</strong>
      <ul style="margin-top: 8px; padding-left: 20px;">
        <li>25% Разработчик (Developer Wallet): <strong>${share:.2f}</strong></li>
        <li>25% Инвестор (Investor Wallet): <strong>${share:.2f}</strong></li>
        <li>25% Команда (Team Wallet): <strong>${share:.2f}</strong></li>
        <li>25% Системный Фонд AIOS (System Fund): <strong>${share:.2f}</strong></li>
      </ul>
    </div>
  </div>
</body>
</html>
"""
    out_file = INVOICES_DIR / f"{inv_id}.html"
    out_file.write_text(html_content, encoding="utf-8")
    
    logger.info(f"🎉 Сгенерирован инвойс {inv_id} на сумму ${amount_usd} USD для {contact_name}")
    return {
        "invoice_id": inv_id,
        "contact": contact_name,
        "amount_usd": amount_usd,
        "item_name": item_name,
        "html_path": str(out_file),
        "split_usd_each": share
    }


if __name__ == "__main__":
    inv = generate_call_invoice("[PRIVATE_CONTACT]", 1500.0, "Фара BMW X5 (Оригинал)", "diag_bmw_1")
    print("Generated invoice:", inv)
