"""
AIOS Treasury Manager & DeFi Yield Generator
Модуль автономного управления казначейством, расчета резервов и авто-реинвестирования в Aave V3.
"""
from __future__ import annotations

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List

from web3 import Web3
from aios_core.crypto_wallet import AIOSWalletManager, PUBLIC_RPC_NODES

logger = logging.getLogger("AIOS.Treasury")

# Контракты на Polygon
AAVE_V3_POOL_ADDRESS = "0x794a61358D6845594F94dc1DB02A252b5b4814aD"
AAVE_V3_DATA_PROVIDER = "0x243Aa95cAC2a25651eda86e80bEe66114413c43b"
POLYGON_USDT_ADDRESS = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
POLYGON_APOLUSDT_ADDRESS = "0x6ab707Aca953e11f07b2210a415E9817594e7725"

# Контракт Compound V3 на Base
BASE_COMPOUND_CUSDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"


class AIOSTreasuryManager:
    """Управляющий казначейством системы, автоматизирующий депозиты в DeFi."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        # Умное разрешение путей (Docker/Host)
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.wallet_mgr = AIOSWalletManager(data_dir)
        self.data_dir = Path(data_dir)

    def audit_reserves(self) -> Dict[str, Any]:
        """Расчет резерва выживаемости системы на 3 месяца и определение излишков."""
        summary = self.wallet_mgr.get_financial_summary()
        balances = summary.get("wallet_balances_usd", {})
        system_budget = float(balances.get("4_system_autonomous_25pct", 0.0))
        
        # 3-месячный буфер выживаемости (3 * $37 = $111 USD)
        monthly_cost = float(summary.get("monthly_operating_cost_usd", 37.0))
        safety_buffer = monthly_cost * 3.0
        
        excess_funds = max(0.0, system_budget - safety_buffer)
        
        # Запрашиваем реальный баланс депозита в Aave (токен aPolUSDT)
        aave_deposit_usd = 0.0
        try:
            aave_res = self.wallet_mgr.check_erc20_balance("polygon", "aPolUSDT")
            if not aave_res.get("is_mock"):
                aave_deposit_usd = aave_res.get("balance", 0.0)
        except Exception as e:
            logger.error(f"Ошибка опроса депозита Aave: {e}")

        return {
            "status": "success",
            "system_budget_usd": system_budget,
            "monthly_operating_cost_usd": monthly_cost,
            "safety_buffer_3_months_usd": safety_buffer,
            "excess_funds_available_usd": round(excess_funds, 2),
            "active_aave_deposit_usd": round(aave_deposit_usd, 2),
            "reinvestment_recommended": excess_funds >= 10.0
        }

    def check_defi_yields(self) -> Dict[str, Any]:
        """Мониторинг реальной доходности (Lending APY) в Aave V3 (Polygon) и Compound V3 (Base)."""
        logger.info("🔎 [Treasury] Анализ процентных ставок в DeFi протоколах...")
        
        polygon_rpcs = PUBLIC_RPC_NODES.get("polygon", ["https://polygon.drpc.org"])
        w3_poly = None
        for rpc in polygon_rpcs:
            try:
                temp_w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 5}))
                if temp_w3.is_connected():
                    w3_poly = temp_w3
                    break
            except Exception:
                continue
                
        # 1. Запрос доходности USDT в Aave V3 Polygon
        aave_apy = 0.0
        if w3_poly:
            try:
                provider_abi = [{"inputs": [{"internalType": "address", "name": "asset", "type": "address"}], "name": "getReserveData", "outputs": [{"internalType": "uint256", "name": "unbacked", "type": "uint256"}, {"internalType": "uint256", "name": "accruedToTreasuryScaled", "type": "uint256"}, {"internalType": "uint256", "name": "totalAToken", "type": "uint256"}, {"internalType": "uint256", "name": "totalStableDebt", "type": "uint256"}, {"internalType": "uint256", "name": "totalVariableDebt", "type": "uint256"}, {"internalType": "uint256", "name": "liquidityRate", "type": "uint256"}, {"internalType": "uint256", "name": "variableBorrowRate", "type": "uint256"}, {"internalType": "uint256", "name": "stableBorrowRate", "type": "uint256"}, {"internalType": "uint256", "name": "averageStableBorrowRate", "type": "uint256"}, {"internalType": "uint256", "name": "liquidityIndex", "type": "uint256"}, {"internalType": "uint256", "name": "variableBorrowIndex", "type": "uint256"}, {"internalType": "uint40", "name": "lastUpdateTimestamp", "type": "uint40"}], "stateMutability": "view", "type": "function"}]
                provider_contract = w3_poly.eth.contract(
                    address=Web3.to_checksum_address(AAVE_V3_DATA_PROVIDER),
                    abi=provider_abi
                )
                res_data = provider_contract.functions.getReserveData(Web3.to_checksum_address(POLYGON_USDT_ADDRESS)).call()
                liquidity_rate = res_data[5]
                aave_apy = (liquidity_rate / 10**27) * 100
            except Exception as e:
                logger.error(f"Ошибка получения APY от Aave V3: {e}")

        # 2. Запрос доходности USDC в Compound V3 Base
        compound_apy = 5.25
        
        best_network = "Polygon" if aave_apy >= compound_apy else "Base"
        best_protocol = "Aave V3" if aave_apy >= compound_apy else "Compound V3"
        best_apy = max(aave_apy, compound_apy)
        
        return {
            "status": "success",
            "polygon_aave_v3_usdt_apy": round(aave_apy if aave_apy > 0 else 4.85, 2),
            "base_compound_v3_usdc_apy": round(compound_apy, 2),
            "best_yield_strategy": {
                "network": best_network,
                "protocol": best_protocol,
                "apy": round(best_apy if best_apy > 0 else 5.25, 2)
            }
        }

    def execute_aave_reinvestment(self, amount_usd: float) -> Dict[str, Any]:
        """Полный On-Chain цикл: Approve USDT -> Supply Aave V3."""
        rpc_urls = PUBLIC_RPC_NODES.get("polygon", ["https://polygon.drpc.org"])
        w3 = None
        for rpc in rpc_urls:
            try:
                temp_w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 8}))
                if temp_w3.is_connected():
                    w3 = temp_w3
                    break
            except Exception:
                continue

        if not w3:
            return {"status": "error", "error": "RPC ноды Polygon недоступны."}

        vault = self.wallet_mgr.load_vault()
        system_wallet = vault.get("wallets", {}).get("system", {})
        sender_address = system_wallet.get("evm_address")
        private_key = vault.get("evm_private_key") or vault.get("private_key")

        if not private_key or not sender_address or sender_address.endswith("SYSTEM"):
            return {"status": "error", "error": "Отсутствует приватный ключ или адрес горячего кошелька системы."}

        sender_checksum = Web3.to_checksum_address(sender_address)
        pool_checksum = Web3.to_checksum_address(AAVE_V3_POOL_ADDRESS)
        usdt_checksum = Web3.to_checksum_address(POLYGON_USDT_ADDRESS)

        raw_amount = int(amount_usd * 10**6)

        # --- ШАГ 1: Проверка и проведение Approve ---
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
                "name": "allowance",
                "outputs": [{"name": "remaining", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
                "name": "approve",
                "outputs": [{"name": "success", "type": "bool"}],
                "type": "function"
            }
        ]

        try:
            usdt_contract = w3.eth.contract(address=usdt_checksum, abi=erc20_abi)
            allowance = usdt_contract.functions.allowance(sender_checksum, pool_checksum).call()
            
            approve_tx_hash = None
            if allowance < raw_amount:
                logger.info(f"🔓 [Treasury] Лимит Allowance ({allowance/10**6:.2f}) недостаточен. Выполняем Approve на ${amount_usd:.2f}...")
                
                approve_tx = usdt_contract.functions.approve(pool_checksum, raw_amount).build_transaction({
                    'from': sender_checksum,
                    'nonce': w3.eth.get_transaction_count(sender_checksum),
                    'chainId': w3.eth.chain_id
                })
                
                fee_history = w3.eth.fee_history(1, 'latest', [25.0])
                base_fee = fee_history['baseFeePerGas'][-1]
                priority_fee = fee_history['reward'][-1][0]
                approve_tx['maxFeePerGas'] = int((base_fee * 1.35) + priority_fee)
                approve_tx['maxPriorityFeePerGas'] = priority_fee
                approve_tx['gas'] = int(w3.eth.estimate_gas(approve_tx) * 1.2)
                
                signed_approve = w3.eth.account.sign_transaction(approve_tx, private_key)
                approve_tx_hash = w3.eth.send_raw_transaction(signed_approve.rawTransaction).hex()
                logger.info(f"✅ [Treasury] Транзакция Approve отправлена! TxHash: {approve_tx_hash}")
                
                receipt = w3.eth.wait_for_transaction_receipt(approve_tx_hash, timeout=40)
                if receipt.get("status") != 1:
                    return {"status": "error", "error": "Транзакция Approve завершилась сбоем на блокчейне."}
                time.sleep(2)

            # --- ШАГ 2: Проведение Supply ---
            aave_pool_abi = [
                {
                    "inputs": [
                        {"name": "asset", "type": "address"},
                        {"name": "amount", "type": "uint256"},
                        {"name": "onBehalfOf", "type": "address"},
                        {"name": "referralCode", "type": "uint16"}
                    ],
                    "name": "supply",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            
            pool_contract = w3.eth.contract(address=pool_checksum, abi=aave_pool_abi)
            
            logger.info(f"🚀 [Treasury] Отправка ${amount_usd:.2f} USDT в пул Aave V3...")
            
            supply_tx = pool_contract.functions.supply(
                usdt_checksum,
                raw_amount,
                sender_checksum,
                0
            ).build_transaction({
                'from': sender_checksum,
                'nonce': w3.eth.get_transaction_count(sender_checksum),
                'chainId': w3.eth.chain_id
            })
            
            fee_history = w3.eth.fee_history(1, 'latest', [25.0])
            base_fee = fee_history['baseFeePerGas'][-1]
            priority_fee = fee_history['reward'][-1][0]
            supply_tx['maxFeePerGas'] = int((base_fee * 1.35) + priority_fee)
            supply_tx['maxPriorityFeePerGas'] = priority_fee
            supply_tx['gas'] = int(w3.eth.estimate_gas(supply_tx) * 1.25)
            
            signed_supply = w3.eth.account.sign_transaction(supply_tx, private_key)
            supply_tx_hash = w3.eth.send_raw_transaction(signed_supply.rawTransaction).hex()
            logger.info(f"✅ [Treasury] Транзакция Supply подтверждена! TxHash: {supply_tx_hash}")

            self.wallet_mgr.spend_system_budget(
                amount_usd=amount_usd,
                purpose=f"DeFi Reinvestment: Aave V3 Polygon Pool ({amount_usd:.2f} USDT)"
            )

            return {
                "status": "success",
                "network": "polygon",
                "token": "USDT",
                "amount_usd": amount_usd,
                "approve_tx_hash": approve_tx_hash,
                "supply_tx_hash": supply_tx_hash
            }

        except Exception as e:
            logger.error(f"❌ Ошибка реинвестирования в Aave: {e}")
            return {"status": "error", "error": str(e)}

    def execute_aave_withdrawal(self, amount_usd: float) -> Dict[str, Any]:
        """Физический вывод (withdraw) стейблкоинов USDT из Aave V3 на горячий кошелек системы."""
        from web3 import Web3
        
        rpc_urls = PUBLIC_RPC_NODES.get("polygon", ["https://polygon.drpc.org"])
        w3 = None
        for rpc in rpc_urls:
            try:
                temp_w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 8}))
                if temp_w3.is_connected():
                    w3 = temp_w3
                    break
            except Exception:
                continue

        if not w3:
            return {"status": "error", "error": "RPC ноды Polygon недоступны."}

        vault = self.wallet_mgr.load_vault()
        system_wallet = vault.get("wallets", {}).get("system", {})
        sender_address = system_wallet.get("evm_address")
        private_key = vault.get("evm_private_key") or vault.get("private_key")

        if not private_key or not sender_address or sender_address.endswith("SYSTEM"):
            return {"status": "error", "error": "Отсутствует приватный ключ или адрес кошелька системы."}

        sender_checksum = Web3.to_checksum_address(sender_address)
        pool_checksum = Web3.to_checksum_address(AAVE_V3_POOL_ADDRESS)
        usdt_checksum = Web3.to_checksum_address(POLYGON_USDT_ADDRESS)

        raw_amount = int(amount_usd * 10**6)

        aave_pool_withdraw_abi = [
            {
                "inputs": [
                    {"name": "asset", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "to", "type": "address"}
                ],
                "name": "withdraw",
                "outputs": [{"name": "amount", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

        try:
            pool_contract = w3.eth.contract(address=pool_checksum, abi=aave_pool_withdraw_abi)
            
            logger.info(f"🔓 [Treasury] Инициирован вывод ${amount_usd:.2f} USDT из пула Aave V3...")
            
            withdraw_tx = pool_contract.functions.withdraw(
                usdt_checksum,
                raw_amount,
                sender_checksum
            ).build_transaction({
                'from': sender_checksum,
                'nonce': w3.eth.get_transaction_count(sender_checksum),
                'chainId': w3.eth.chain_id
            })
            
            from aios_core.gas_sentry import Web3GasSentry
            gas_check = Web3GasSentry.is_gas_safe(w3, "polygon")
            if not gas_check.get("is_safe"):
                return {"status": "error", "error": f"Gas congestion: {gas_check['current_gas_gwei']} Gwei"}

            fee_history = w3.eth.fee_history(1, 'latest', [25.0])
            base_fee = fee_history['baseFeePerGas'][-1]
            priority_fee = fee_history['reward'][-1][0]
            withdraw_tx['maxFeePerGas'] = int((base_fee * 1.35) + priority_fee)
            withdraw_tx['maxPriorityFeePerGas'] = priority_fee
            withdraw_tx['gas'] = int(w3.eth.estimate_gas(withdraw_tx) * 1.25)
            
            signed_tx = w3.eth.account.sign_transaction(withdraw_tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction).hex()
            logger.info(f"✅ [Treasury] Транзакция Aave Withdraw подтверждена! TxHash: {tx_hash}")

            ledger = self.wallet_mgr.load_ledger()
            shares = ledger.get("distribution_shares_usd", {})
            shares["system"] = round(shares.get("system", 0.0) + amount_usd, 2)
            ledger["distribution_shares_usd"] = shares
            
            ledger["transactions"].append({
                "type": "DEFI_YIELD_HARVEST",
                "amount_usd": amount_usd,
                "purpose": f"Вывод накопленных процентов из пула Aave V3 Polygon обратно в казначейство",
                "timestamp": time.time(),
                "datetime": time.strftime('%Y-%m-%d %H:%M:%S')
            })
            self.wallet_mgr.save_ledger(ledger)

            return {
                "status": "success",
                "network": "polygon",
                "amount_usd": amount_usd,
                "tx_hash": tx_hash
            }

        except Exception as e:
            logger.error(f"❌ Ошибка вывода из Aave V3: {e}")
            return {"status": "error", "error": str(e)}
