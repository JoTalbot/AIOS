"""
AIOS Invoice Generator & Interactive Billing Engine
Модуль генерации красивых интерактивных счетов-инвойсов для клиентов AIOS.
"""
from __future__ import annotations

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("AIOS.InvoiceGenerator")


class AIOSInvoiceGenerator:
    """Генератор красивых интерактивных счетов-инвойсов для клиентов AIOS."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        # Умное разрешение путей (Docker/Host)
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.data_dir = Path(data_dir)

    def generate_invoice_html(self, client_name: str, amount_usd: float, service_desc: str, invoice_id: str = None) -> str:
        """Генерирует автономный интерактивный HTML-инвойс с кнопками копирования адресов."""
        if not invoice_id:
            invoice_id = f"INV-{time.strftime('%Y%m%d')}-{int(time.time() * 1000) % 10000:03d}"
            
        date_str = time.strftime('%Y-%m-%d')
        
        # Загружаем адреса кошельков для отображения
        vault_file = self.data_dir / ".wallet_vault.json"
        evm_address = "0x21d6630ECcB68a34aF6Dd052786746BEb5dD9b9e"
        trc20_address = "TH1uNiJps4NhvNWRESwVcQERZq8sQm1LE7"
        
        if vault_file.exists():
            try:
                vault = json.loads(vault_file.read_text(encoding="utf-8"))
                system_wallets = vault.get("wallets", {}).get("system", {})
                evm_address = system_wallets.get("evm_address") or evm_address
                trc20_address = system_wallets.get("trc20_address") or trc20_address
            except Exception:
                pass

        html_template = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Счет {invoice_id} — AIOS Corporation</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: #f5f7fa;
            color: #333333;
            margin: 0;
            padding: 40px 20px;
        }}
        .invoice-card {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
            padding: 40px;
            border-top: 8px solid #1F4E78;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            border-bottom: 2px solid #eef2f5;
            padding-bottom: 30px;
            margin-bottom: 30px;
        }}
        .logo-title {{
            font-size: 24px;
            font-weight: bold;
            color: #1F4E78;
        }}
        .invoice-title {{
            font-size: 28px;
            font-weight: bold;
            color: #2b2b2b;
            text-align: right;
        }}
        .details {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 40px;
        }}
        .details-col {{
            flex: 1;
        }}
        .details-col h4 {{
            margin: 0 0 8px 0;
            color: #595959;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 1px;
        }}
        .details-col p {{
            margin: 0;
            font-size: 14px;
            line-height: 1.5;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 40px;
        }}
        th {{
            background-color: #f8fafc;
            color: #1F4E78;
            font-weight: bold;
            text-align: left;
            padding: 12px 15px;
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 2px solid #eef2f5;
        }}
        td {{
            padding: 15px;
            border-bottom: 1px solid #eef2f5;
            font-size: 14px;
        }}
        .total-section {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 40px;
        }}
        .total-box {{
            background-color: #f8fafc;
            border-radius: 8px;
            padding: 20px;
            width: 250px;
            text-align: right;
        }}
        .total-box h3 {{
            margin: 0;
            font-size: 22px;
            color: #1F4E78;
        }}
        .payment-section {{
            background-color: #f4f7f6;
            border-radius: 8px;
            padding: 25px;
            border-left: 4px solid #1F4E78;
        }}
        .payment-section h4 {{
            margin: 0 0 15px 0;
            color: #1F4E78;
            font-size: 16px;
        }}
        .wallet-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: #ffffff;
            padding: 10px 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            border: 1px solid #e2e8f0;
        }}
        .wallet-address {{
            font-family: monospace;
            font-size: 13px;
            color: #4a5568;
            word-break: break-all;
        }}
        .copy-btn {{
            background-color: #1F4E78;
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 12px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .copy-btn:hover {{
            background-color: #2c6497;
        }}
        @media print {{
            body {{ padding: 0; background: none; }}
            .invoice-card {{ box-shadow: none; padding: 0; border: none; }}
            .copy-btn {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="invoice-card">
        <div class="header">
            <div>
                <div class="logo-title">AIOS Corporation</div>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #595959;">Автономные ИИ-Решения и Трейдинг</p>
            </div>
            <div>
                <div class="invoice-title">ИНВОЙС</div>
                <p style="margin: 5px 0 0 0; text-align: right; font-size: 14px; color: #595959;">№ {invoice_id}</p>
            </div>
        </div>

        <div class="details">
            <div class="details-col">
                <h4>Получатель / Исполнитель</h4>
                <p><b>AIOS Autonomous System</b></p>
                <p>Сервер Kropyvnytskyi, UA</p>
                <p>Email: system@aios.local</p>
            </div>
            <div class="details-col">
                <h4>Плательщик / Заказчик</h4>
                <p><b>{client_name}</b></p>
                <p>Электронный клиент системы</p>
            </div>
            <div class="details-col" style="text-align: right;">
                <h4>Дата выписки</h4>
                <p>{date_str}</p>
                <h4 style="margin-top: 15px;">Срок оплаты</h4>
                <p>В течение 7 дней</p>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Описание услуги</th>
                    <th style="text-align: right;">Сумма (USD)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{service_desc}</td>
                    <td style="text-align: right; font-weight: bold;">${amount_usd:.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="total-section">
            <div class="total-box">
                <p style="margin: 0 0 5px 0; font-size: 12px; color: #595959; text-transform: uppercase;">Итого к оплате</p>
                <h3>${amount_usd:.2f} USD</h3>
            </div>
        </div>

        <div class="payment-section">
            <h4>Реквизиты для On-Chain оплаты (USDT / USDC)</h4>
            <p style="font-size: 12px; color: #595959; margin: 0 0 15px 0;">Нажмите кнопку «Копировать» для быстрого копирования адреса.</p>
            
            <div class="wallet-row">
                <div>
                    <span style="font-weight: bold; font-size: 12px; color: #1F4E78; display: block; margin-bottom: 2px;">EVM (Polygon/Base): USDT/USDC</span>
                    <span class="wallet-address" id="evm-addr">{evm_address}</span>
                </div>
                <button class="copy-btn" onclick="copyToClipboard('evm-addr')">Копировать</button>
            </div>

            <div class="wallet-row">
                <div>
                    <span style="font-weight: bold; font-size: 12px; color: #1F4E78; display: block; margin-bottom: 2px;">TRON (TRC20): USDT</span>
                    <span class="wallet-address" id="tron-addr">{trc20_address}</span>
                </div>
                <button class="copy-btn" onclick="copyToClipboard('tron-addr')">Копировать</button>
            </div>
        </div>
    </div>

    <script>
        function copyToClipboard(id) {{
            const text = document.getElementById(id).innerText;
            navigator.clipboard.writeText(text).then(() => {{
                alert("Адрес успешно скопирован в буфер обмена!");
            }}).catch(err => {{
                console.error("Ошибка копирования: ", err);
            }});
        }}
    </script>
</body>
</html>
"""
        output_file = self.data_dir / "invoices" / f"invoice_{invoice_id}.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(html_template, encoding="utf-8")
        
        logger.info(f"📑 [Invoicer] Интерактивный счет успешно сгенерирован: {output_file}")
        return str(output_file)
