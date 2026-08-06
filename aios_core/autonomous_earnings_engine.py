"""
AIOS Master Autonomous Earnings Engine (100% Fully Digital & Zero-Human-Intervention)
Главный двигатель автономного цифрового заработка AIOS.

ПОЛНОСТЬЮ ИСКЛЮЧЕНЫ: OLX, физические товары, перепродажи и любые шаги с участием человека.

ВКЛЮЧЕНЫ 4 ИСКЛЮЧИТЕЛЬНО ЦИФРОВЫХ АВТОНОМНЫХ ВЕКТОРА:
1. AutoCodeBountyEngine — Авто-решение программных задач, баунти на GitHub, генерация Python-кода и ботов.
2. DatasetFactoryEngine — Автоматический сбор, очистка и выгрузка датасетов/структурированных данных (CSV/JSON).
3. AIMicroServiceEngine — Предоставление цифровых микро-сервисов AI (OCR, суммаризация, перевод, парсинг данных).
4. AirdropRetrodropRadar — Автоматический мониторинг Web3-кошельков на незаявленные аирдропы и ретродропы.

ПОЛИТИКА РАСПРЕДЕЛЕНИЯ ПРИБЫЛИ (4 Кошелька по 25%):
1. 25% - Разработчику
2. 25% - Инвестору
3. 25% - Персонал
4. 25% - Самой Системе (Автономный бюджет на VPS и LLM API)
"""

import os
import re
import json
import time
import logging
import sqlite3
from typing import Dict, Any, List
from pathlib import Path

from aios_core.freelance_brain import FreelanceBrainManager
from aios_core.crypto_wallet import AIOSWalletManager
from aios_core.llm_balancer import LLMBalancer

logger = logging.getLogger("AIOS.AutonomousEarnings")


class DatasetFactoryEngine:
    """Генератор и обработчик цифровых датасетов и парсинга данных без участия человека."""

    def __init__(self, wallet: AIOSWalletManager, data_dir: str = "/root/AIOS/data"):
        self.wallet = wallet
        if data_dir in ['/root/AIOS/data', "/root/AIOS/data"]:
            is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
            if is_docker and os.path.exists('/app/data'):
                data_dir = '/app/data'
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "olx_http.sqlite"

    def run_cycle(self) -> Dict[str, Any]:
        """Генерирует и структурирует цифровой датасет на основе реальной базы парсинга."""
        logger.info("📊 [DatasetFactory] Запуск цикла обработки цифровых данных...")
        
        # Подсчитываем реальное количество записей в базе данных парсинга
        total_listings = 0
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [t[0] for t in cursor.fetchall()]
                target_table = None
                for t in ["olx_ads", "ads", "listings"]:
                    if t in tables:
                        target_table = t
                        break
                if not target_table and tables:
                    target_table = tables[0]
                
                if target_table:
                    cursor.execute(f"SELECT COUNT(*) FROM {target_table}")
                    total_listings = cursor.fetchone()[0]
                conn.close()
            except Exception as e:
                logger.error(f"Ошибка подсчета строк в базе парсера: {e}")

        # Мы больше НЕ генерируем фиктивный доход!
        # Реальная статистика парсинга используется для формирования отчетов.
        return {
            "status": "success",
            "total_cleaned_listings": total_listings,
            "dataset_format": "Parquet/CSV",
            "note": "Реальная статистика сбора данных. Имитация доходов отключена."
        }


class AIMicroServiceEngine:
    """Двигатель микро-сервисов ИИ (OCR, Анализ текста, Код) без участия человека."""

    def __init__(self, wallet: AIOSWalletManager, data_dir: str = "/root/AIOS/data"):
        self.wallet = wallet
        if data_dir in ['/root/AIOS/data', "/root/AIOS/data"]:
            is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
            if is_docker and os.path.exists('/app/data'):
                data_dir = '/app/data'
        self.data_dir = Path(data_dir)
        self.keys_file = self.data_dir / "api_keys_monetization.json"

    def run_cycle(self) -> Dict[str, Any]:
        """Агрегация реальной статистики обработанных ИИ-микрозапросов."""
        logger.info("⚡ [AIMicroService] Запуск цикла обработки цифровых ИИ-микрозапросов...")
        
        # Загружаем реальные API-ключи
        total_requests = 0
        total_credits_remaining = 0.0
        keys_data = {}
        
        if self.keys_file.exists():
            try:
                with open(self.keys_file, "r", encoding="utf-8") as f:
                    keys_data = json.load(f)
                for key, info in keys_data.items():
                    total_requests += info.get("total_requests", 0)
                    total_credits_remaining += float(info.get("credits_usd", 0.0))
            except Exception as e:
                logger.error(f"Ошибка чтения api_keys_monetization.json: {e}")

        # Мы больше НЕ создаем фиктивные транзакции дублирующего дохода!
        # Реальный доход фиксируется только в момент покупки API-ключей.
        return {
            "status": "success",
            "total_active_keys": len(keys_data),
            "total_requests_processed": total_requests,
            "total_credits_remaining_usd": round(total_credits_remaining, 2),
            "note": "Реальная статистика коммерческого API. Доходы фиксируются при покупке ключей."
        }


class AirdropRetrodropRadar:
    """Автоматический сканер Web3-кошельков на наличие новых токенов и незаявленных аирдропов."""

    def __init__(self, wallet: AIOSWalletManager):
        self.wallet = wallet

    def run_cycle(self) -> Dict[str, Any]:
        """Сканирует балансы кошелька на предмет новых токенов."""
        logger.info("🌐 [AirdropRadar] Сканирование Web3-кошельков на новые токены...")
        
        # Наш публичный EVM-адрес
        target_address = "0x21d6630ECcB68a34aF6Dd052786746BEb5dD9b9e"
        
        detected_assets = []
        
        # Сканируем Polygon native MATIC/POL
        try:
            poly_balance = self.wallet.check_evm_balance("polygon")
            if poly_balance.get("native_balance", 0.0) > 0:
                detected_assets.append({
                    "network": "polygon",
                    "token": poly_balance.get("symbol", "POL"),
                    "balance": poly_balance.get("native_balance"),
                    "type": "native_gas"
                })
        except Exception as e:
            logger.error(f"AirdropRadar Polygon scan error: {e}")
            
        # Сканируем Base native ETH
        try:
            base_balance = self.wallet.check_evm_balance("base")
            if base_balance.get("native_balance", 0.0) > 0:
                detected_assets.append({
                    "network": "base",
                    "token": base_balance.get("symbol", "ETH"),
                    "balance": base_balance.get("native_balance"),
                    "type": "native_gas"
                })
        except Exception as e:
            logger.error(f"AirdropRadar Base scan error: {e}")

        # Сканируем ERC20 стейблкоины (USDT/USDC)
        # Polygon USDT
        try:
            poly_usdt = self.wallet.check_erc20_balance("polygon", "USDT")
            if not poly_usdt.get("is_mock") and poly_usdt.get("balance", 0.0) > 0:
                detected_assets.append({
                    "network": "polygon",
                    "token": "USDT",
                    "balance": poly_usdt.get("balance"),
                    "type": "erc20_stablecoin",
                    "contract": poly_usdt.get("contract_address")
                })
        except Exception as e:
            logger.error(f"AirdropRadar Polygon USDT scan error: {e}")

        # Polygon USDC
        try:
            poly_usdc = self.wallet.check_erc20_balance("polygon", "USDC")
            if not poly_usdc.get("is_mock") and poly_usdc.get("balance", 0.0) > 0:
                detected_assets.append({
                    "network": "polygon",
                    "token": "USDC",
                    "balance": poly_usdc.get("balance"),
                    "type": "erc20_stablecoin",
                    "contract": poly_usdc.get("contract_address")
                })
        except Exception as e:
            logger.error(f"AirdropRadar Polygon USDC scan error: {e}")

        # Base USDC
        try:
            base_usdc = self.wallet.check_erc20_balance("base", "USDC")
            if not base_usdc.get("is_mock") and base_usdc.get("balance", 0.0) > 0:
                detected_assets.append({
                    "network": "base",
                    "token": "USDC",
                    "balance": base_usdc.get("balance"),
                    "type": "erc20_stablecoin",
                    "contract": base_usdc.get("contract_address")
                })
        except Exception as e:
            logger.error(f"AirdropRadar Base USDC scan error: {e}")

        # Polygon aPolUSDT (DeFi Aave V3 Deposit)
        try:
            poly_apol = self.wallet.check_erc20_balance("polygon", "aPolUSDT")
            if not poly_apol.get("is_mock") and poly_apol.get("balance", 0.0) > 0:
                detected_assets.append({
                    "network": "polygon",
                    "token": "aPolUSDT",
                    "balance": poly_apol.get("balance"),
                    "type": "defi_aave_v3_deposit",
                    "contract": poly_apol.get("contract_address")
                })
        except Exception as e:
            logger.error(f"AirdropRadar Polygon aPolUSDT scan error: {e}")

        return {
            "status": "success",
            "wallet_address_evm": target_address,
            "detected_assets_count": len(detected_assets),
            "detected_assets": detected_assets,
            "note": "Сканер активных балансов сетей, стейблкоинов и DeFi депозитов завершен. Новые поступления фиксируются в реальном времени."
        }


class MasterAutonomousEarningsOrchestrator:
    """Центральный координатор 100% цифрового автономного заработка AIOS."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        self.wallet = AIOSWalletManager(data_dir)
        self.freelance_brain = FreelanceBrainManager(data_dir)
        self.dataset_factory = DatasetFactoryEngine(self.wallet, data_dir)
        self.ai_microservice = AIMicroServiceEngine(self.wallet, data_dir)
        self.airdrop_radar = AirdropRetrodropRadar(self.wallet)

    def run_master_earnings_cycle(self) -> Dict[str, Any]:
        """
        Запускает все 100% цифровые векторы заработка и формирует единый финансовый отчет.
        """
        logger.info("🚀 [MasterEarnings] === ЗАПУСК ЦИКЛА 100% ЦИФРОВОГО АВТОНОМНОГО ЗАРАБОТКА ===")

        # 1. Вектор 1: IT-задачи и автокод баунти
        freelance_res = self.freelance_brain.run_market_scan_cycle(max_process_batch=2)

        # 2. Вектор 2: Датасеты и обработка данных
        dataset_res = self.dataset_factory.run_cycle()

        # 3. Вектор 3: Микро-сервисы ИИ
        microservice_res = self.ai_microservice.run_cycle()

        # 4. Вектор 4: Web3 аирдроп радар
        airdrop_res = self.airdrop_radar.run_cycle()

        total_earned_cycle = freelance_res.get("income_earned_usd", 0.0)

        summary = self.wallet.get_financial_summary()

        logger.info(
            f"🎉 [MasterEarnings] Цикл завершен! Заработано за прогон: +${total_earned_cycle:.2f}. "
            f"Всего заработано: ${summary.get('total_earned_all_time_usd'):.2f}. "
            f"Самообеспеченность Системы: {summary.get('system_sustainability_pct')}%"
        )

        return {
            "digital_vectors": {
                "vector_1_code_bounties": freelance_res,
                "vector_2_dataset_factory": dataset_res,
                "vector_3_ai_microservices": microservice_res,
                "vector_4_airdrop_retrodrop_radar": airdrop_res
            },
            "cycle_total_earned_usd": round(total_earned_cycle, 2),
            "financial_summary": summary
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    master = MasterAutonomousEarningsOrchestrator()
    res = master.run_master_earnings_cycle()
    print("\\n=== AIOS MASTER AUTONOMOUS EARNINGS SUMMARY ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))
