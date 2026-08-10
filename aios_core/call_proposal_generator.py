#!/usr/bin/env python3
"""
AIOS Automated Commercial Proposal & Invoice Generator (Option 3)
Формирует КП и HTML/PDF счета на основе договоренностей из звонков с распределением 25%x4.
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
logger = logging.getLogger("aios.call_proposal")


def generate_proposal_invoice_from_call(contact_name: str, dialogue_id: str, summary_text: str, amount_usd: float = 150.0) -> Dict[str, Any]:
    """Генерирует фирменный HTML-счет и КП на основе договоренностей из звонка."""
    INVOICES_DIR.mkdir(parents=True, exist_ok=True)
    
    invoice_id = f"inv_{dialogue_id[:12]}"
    file_path = INVOICES_DIR / f"{invoice_id}.html"

    # Распределения доходов по правилу 25% x 4
    dev_share = round(amount_usd * 0.25, 2)
    inv_share = round(amount_usd * 0.25, 2)
    team_share = round(amount_usd * 0.25, 2)
    fund_share = round(amount_usd * 0.25, 2)

    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Коммерческое Предложение / Счёт — AIOS #{invoice_id}</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #0F172A; color: #F8FAFC; padding: 40px; }}
    .invoice-card {{ background: #1E293B; border: 1px solid #334155; border-radius: 16px; padding: 30px; max-width: 700px; margin: 0 auto; }}
    .header {{ border-bottom: 2px solid #00F0FF; padding-bottom: 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
    .title {{ font-size: 1.5rem; color: #00F0FF; font-weight: bold; }}
    .details {{ font-size: 0.95rem; line-height: 1.6; margin-bottom: 20px; }}
    .amount-box {{ background: #064E3B; border: 1px solid #10B981; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 25px; }}
    .split-table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; margin-top: 20px; }}
    .split-table th, .split-table td {{ border: 1px solid #334155; padding: 10px; text-align: left; }}
    .split-table th {{ background: #162032; color: #00F0FF; }}
  </style>
</head>
<body>
  <div class="invoice-card">
    <div class="header">
      <div class="title">🤖 AIOS Invoice #{invoice_id}</div>
      <div style="color: #94A3B8;">Дата: {datetime.now().strftime('%Y-%m-%d')}</div>
    </div>
    <div class="details">
      <p><strong>Заказчик / Контакт:</strong> {contact_name}</p>
      <p><strong>Основание:</strong> Договоренности по звонку #{dialogue_id}</p>
    </div>
    <div class="amount-box">
      <div style="font-size: 0.9rem; color: #6EE7B7;">ИТОГОВАЯ СУММА К ОПЛАТЕ:</div>
      <div style="font-size: 2.2rem; font-weight: bold; color: #34D399;">${amount_usd:.2f} USD</div>
    </div>
    <div>
      <strong>Выжимка согласованных условий:</strong>
      <div style="background: #111B2E; padding: 15px; border-radius: 8px; font-size: 0.9rem; margin-top: 8px; white-space: pre-line;">{summary_text[:400]}</div>
    </div>
    <table class="split-table">
      <thead>
        <tr><th>Направление распределения (25% x 4 Rule)</th><th>Сумма ($)</th></tr>
      </thead>
      <tbody>
        <tr><td>👨‍💻 Developer Wallet (25%)</td><td>${dev_share:.2f}</td></tr>
        <tr><td>📈 Investor Wallet (25%)</td><td>${inv_share:.2f}</td></tr>
        <tr><td>👥 Personnel / Team Wallet (25%)</td><td>${team_share:.2f}</td></tr>
        <tr><td>🏦 AIOS System Fund (25%)</td><td>${fund_share:.2f}</td></tr>
      </tbody>
    </table>
  </div>
</body>
</html>
"""
    file_path.write_text(html_content, encoding="utf-8")
    logger.info(f"🎉 Сгенерирован инвойс и КП: {file_path}")

    return {
        "invoice_id": invoice_id,
        "contact_name": contact_name,
        "amount_usd": amount_usd,
        "file_path": str(file_path),
        "split": {
            "developer": dev_share,
            "investor": inv_share,
            "personnel": team_share,
            "fund": fund_share
        }
    }


if __name__ == "__main__":
    res = generate_proposal_invoice_from_call("[PRIVATE_CONTACT]", "call_999", "Поставка серверов со скидкой 10%", 200.0)
    print("Generated proposal invoice:", res)
