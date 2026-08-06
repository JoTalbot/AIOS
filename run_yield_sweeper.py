#!/usr/bin/env python3
"""
AIOS Yield Sweeper Daemon & Weekly On-Chain Clearing Manager
Скрипт еженедельного клиринга дивидендов и автоматической On-Chain выплаты долей.

Опции:
  --confirm    — Реально отправить On-Chain транзакции (без флага — безопасный сухой прогон/просмотр)
"""

import sys
import os
import time
import argparse
import logging
import json
from pathlib import Path

# Убедимся, что корень проекта импортируем
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Если запущен в докере, используем /app, иначе /root/AIOS
data_dir = "/root/AIOS/data"
is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
if is_docker and os.path.exists("/app/data"):
    data_dir = "/app/data"

from aios_core.crypto_wallet import AIOSWalletManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.YieldSweeper")


def run_sweeper_cycle(confirm: bool = False) -> dict:
    logger.info("💸 [YieldSweeper] Запуск цикла On-Chain клиринга дивидендов...")
    
    wallet_mgr = AIOSWalletManager(data_dir)
    ledger = wallet_mgr.load_ledger()
    
    # 1. Инициализация учета невыплаченных долей (Unpaid Shares) для обратной совместимости
    if "unpaid_shares_usd" not in ledger:
        # Если запускаемся впервые, все накопленные доли считаем невыплаченными
        shares = ledger.get("distribution_shares_usd", {
            "developer": 0.0,
            "investor": 0.0,
            "personnel": 0.0,
            "system": 0.0
        })
        ledger["unpaid_shares_usd"] = {
            "developer": round(shares.get("developer", 0.0), 2),
            "investor": round(shares.get("investor", 0.0), 2),
            "personnel": round(shares.get("personnel", 0.0), 2)
        }
        ledger["paid_shares_usd"] = {
            "developer": 0.0,
            "investor": 0.0,
            "personnel": 0.0
        }
        wallet_mgr.save_ledger(ledger)
        
    unpaid = ledger["unpaid_shares_usd"]
    paid = ledger.get("paid_shares_usd", {"developer": 0.0, "investor": 0.0, "personnel": 0.0})
    
    # 2. Опрос реальных On-Chain балансов стейблкоинов на кошельке системы
    balances = {
        "polygon": {"USDT": 0.0, "USDC": 0.0},
        "base": {"USDC": 0.0, "USDT": 0.0}
    }
    
    # Проверяем Polygon
    try:
        poly_usdt = wallet_mgr.check_erc20_balance("polygon", "USDT")
        if not poly_usdt.get("is_mock"):
            balances["polygon"]["USDT"] = poly_usdt.get("balance", 0.0)
            
        poly_usdc = wallet_mgr.check_erc20_balance("polygon", "USDC")
        if not poly_usdc.get("is_mock"):
            balances["polygon"]["USDC"] = poly_usdc.get("balance", 0.0)
    except Exception as e:
        logger.error(f"Ошибка проверки балансов Polygon: {e}")
        
    # Проверяем Base
    try:
        base_usdc = wallet_mgr.check_erc20_balance("base", "USDC")
        if not base_usdc.get("is_mock"):
            balances["base"]["USDC"] = base_usdc.get("balance", 0.0)
            
        base_usdt = wallet_mgr.check_erc20_balance("base", "USDT")
        if not base_usdt.get("is_mock"):
            balances["base"]["USDT"] = base_usdt.get("balance", 0.0)
    except Exception as e:
        logger.error(f"Ошибка проверки балансов Base: {e}")
        
    logger.info(f"💰 Реальные On-Chain балансы на кошельке системы: {json.dumps(balances)}")
    logger.info(f"📋 Невыплаченные доли в Gross-бухе: Developer: ${unpaid['developer']:.2f}, Investor: ${unpaid['investor']:.2f}")

    vault = wallet_mgr.load_vault()
    wallets = vault.get("wallets", {})
    
    payout_txs = []
    total_paid_this_cycle = 0.0

    # 3. Алгоритм клиринга дивидендов
    # Мы проходим по каждой сети и токену, где баланс > 5.0 USD, и выплачиваем долги участникам
    for network, tokens in balances.items():
        for token_symbol, balance in tokens.items():
            if balance < 5.0:
                continue
                
            logger.info(f"🎯 Обнаружен баланс ${balance:.2f} {token_symbol} в сети {network.upper()}. Распределяем долги...")
            
            # Распределяем баланс между разработчиком и инвестором пропорционально их долгу
            for party in ["developer", "investor"]:
                party_unpaid = unpaid.get(party, 0.0)
                if party_unpaid <= 0:
                    continue
                    
                party_info = wallets.get(party, {})
                evm_address = party_info.get("evm_address", "")
                
                # Проверяем, настроен ли реальный кошелек
                is_placeholder = (
                    not evm_address or 
                    evm_address.startswith("0x0000") or 
                    any(suffix in evm_address.upper() for suffix in ["DEVAIOS", "INVAIOS", "STAFFAIOS"])
                )
                
                if is_placeholder:
                    logger.info(f"ℹ️ [YieldSweeper] Выплата {party} пропущена: адрес является плейсхолдером ({evm_address})")
                    continue
                    
                # Сумма выплаты - минимум из долга системы перед участником и доступного баланса
                payout_amount = min(party_unpaid, balance)
                if payout_amount < 1.0: # Не отправляем транзакции менее $1
                    continue
                    
                logger.info(f"📲 [YieldSweeper] Найдено обязательство: {party} долг ${party_unpaid:.2f}. Отправляем ${payout_amount:.2f} {token_symbol} в сети {network.upper()}...")
                
                if confirm:
                    # РЕАЛЬНАЯ ОТПРАВКА СРЕДСТВ В БЛОКЧЕЙН!
                    tx_res = wallet_mgr.send_evm_tokens(
                        network=network,
                        token_symbol=token_symbol,
                        recipient=evm_address,
                        amount_usd=payout_amount
                    )
                    
                    if tx_res.get("status") == "success":
                        tx_hash = tx_res.get("tx_hash")
                        logger.info(f"✅ [YieldSweeper] Транзакция подтверждена! TxHash: {tx_hash}")
                        
                        # Обновляем бухгалтерию
                        unpaid[party] = round(unpaid[party] - payout_amount, 2)
                        paid[party] = round(paid.get(party, 0.0) + payout_amount, 2)
                        total_paid_this_cycle += payout_amount
                        balance -= payout_amount
                        
                        payout_txs.append({
                            "party": party,
                            "address": evm_address,
                            "network": network,
                            "token": token_symbol,
                            "amount_usd": payout_amount,
                            "status": "executed",
                            "tx_hash": tx_hash
                        })
                    else:
                        logger.error(f"❌ [YieldSweeper] Ошибка On-Chain перевода: {tx_res.get('error')}")
                        payout_txs.append({
                            "party": party,
                            "address": evm_address,
                            "network": network,
                            "token": token_symbol,
                            "amount_usd": payout_amount,
                            "status": "error",
                            "error": tx_res.get("error")
                        })
                else:
                    # Сухой прогон (Simulation)
                    logger.info(f"🔬 [YieldSweeper-DRY RUN] Имитация транзакции: {payout_amount:.2f} {token_symbol} -> {evm_address}")
                    payout_txs.append({
                        "party": party,
                        "address": evm_address,
                        "network": network,
                        "token": token_symbol,
                        "amount_usd": payout_amount,
                        "status": "simulated"
                    })

    # Сохраняем обновленные балансы долей, если реально были выплаты
    if confirm and total_paid_this_cycle > 0:
        ledger["unpaid_shares_usd"] = unpaid
        ledger["paid_shares_usd"] = paid
        
        # Добавляем лог клиринга в историю транзакций
        ledger["transactions"].append({
            "type": "YIELD_CLEARING_RUN",
            "total_payout_usd": total_paid_this_cycle,
            "payouts": payout_txs,
            "timestamp": time.time(),
            "datetime": time.strftime('%Y-%m-%d %H:%M:%S')
        })
        wallet_mgr.save_ledger(ledger)
        logger.info(f"💾 [YieldSweeper] Бухгалтерия сохранена. Всего выплачено On-Chain: ${total_paid_this_cycle:.2f} USD")

    return {
        "status": "success",
        "confirm_execution": confirm,
        "total_payout_usd": total_paid_this_cycle,
        "payout_transactions": payout_txs,
        "remaining_unpaid_debts_usd": unpaid,
        "total_paid_all_time_usd": paid
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOS Weekly Yield Sweeper and Clearing Manager")
    parser.add_argument("--confirm", action="store_true", help="Реально отправить On-Chain транзакции и обновить бухгалтерию")
    args = parser.parse_args()
    
    res = run_sweeper_cycle(confirm=args.confirm)
    print("\n" + "=" * 50)
    print("=== AIOS YIELD SWEEPER & CLEARING RUN RESULTS ===")
    print("=" * 50)
    print(json.dumps(res, indent=2, ensure_ascii=False))
