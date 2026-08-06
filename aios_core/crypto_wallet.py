"""
AIOS Multi-Chain Crypto Wallet & 4-Way Profit Distribution Manager
Модуль криптокошельков и распределения прибыли AIOS.

ПОЛИТИКА РАСПРЕДЕЛЕНИЯ ПРИБЫЛИ (25% / 25% / 25% / 25%):
Вся прибыль проекта от любого источника автоматически делится на 4 равные части
и распределяется по 4 отдельным кошелькам:
1. 25% - Разработчик (Developer Wallet)
2. 25% - Инвестор (Investor Wallet)
3. 25% - Персонал (Personnel/Staff Wallet)
4. 25% - Система (System Autonomous Wallet) — средства, которые AIOS может тратить
   по своему усмотрению (VPS серверы, LLM API ключи, домены, новое железо).
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from web3 import Web3

logger = logging.getLogger('AIOS.CryptoWallet')

PUBLIC_RPC_NODES = {
    'ethereum': ['https://cloudflare-eth.com', 'https://rpc.ankr.com/eth'],
    'polygon': ['https://polygon-rpc.com', 'https://rpc.ankr.com/polygon'],
    'arbitrum': ['https://arb1.arbitrum.io/rpc', 'https://rpc.ankr.com/arbitrum'],
    'base': ['https://mainnet.base.org', 'https://developer-access-mainnet.base.org'],
    'bsc': ['https://bsc-dataseed.binance.org', 'https://rpc.ankr.com/bsc']
}

DEFAULT_COSTS = {
    'vps_hosting_usd': 15.0,     # Стоимость VPS сервера в месяц ($)
    'llm_budget_usd': 20.0,       # Порог бюджета на платные LLM в месяц ($)
    'domain_dns_usd': 2.0,        # Поддержка доменов / инфраструктуры ($)
}


class AIOSWalletManager:
    """Управление 4 кошельками прибыли и бюджетом самообеспечения AIOS."""

    def __init__(self, data_dir: str = '/root/AIOS/data'):
        self.data_dir = Path(data_dir)
        self.vault_file = self.data_dir / '.wallet_vault.json'
        self.ledger_file = self.data_dir / 'self_funding_ledger.json'
        self._ensure_files()

    def _ensure_files(self):
        """Создание файлов хранения с конфигурацией 4 кошельков при их отсутствии."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.vault_file.exists():
            default_vault = {
                'rule': 'PROFIT_SPLIT_4_WAY_25_PERCENT',
                'wallets': {
                    'developer': {
                        'label': '1. Разработчик',
                        'evm_address': '0x000000000000000000000000000000000DEVAIOS',
                        'trc20_address': 'T_AIOS_DEVELOPER_WALLET_ADDRESS'
                    },
                    'investor': {
                        'label': '2. Инвестор',
                        'evm_address': '0x000000000000000000000000000000000INVAIOS',
                        'trc20_address': 'T_AIOS_INVESTOR_WALLET_ADDRESS'
                    },
                    'personnel': {
                        'label': '3. Персонал',
                        'evm_address': '0x00000000000000000000000000000000STAFFAIOS',
                        'trc20_address': 'T_AIOS_PERSONNEL_WALLET_ADDRESS'
                    },
                    'system': {
                        'label': '4. Система (Автономный бюджет)',
                        'evm_address': '0x00000000000000000000000000000000000SYSTEM',
                        'trc20_address': 'T_AIOS_SYSTEM_AUTONOMOUS_WALLET'
                    }
                }
            }
            with open(self.vault_file, 'w', encoding='utf-8') as f:
                json.dump(default_vault, f, indent=2, ensure_ascii=False)
            os.chmod(self.vault_file, 0o600)

        if not self.ledger_file.exists():
            default_ledger = {
                'total_earned_usd': 0.0,
                'total_spent_system_usd': 0.0,
                'distribution_shares_usd': {
                    'developer': 0.0,
                    'investor': 0.0,
                    'personnel': 0.0,
                    'system': 0.0
                },
                'monthly_costs': DEFAULT_COSTS,
                'transactions': []
            }
            with open(self.ledger_file, 'w', encoding='utf-8') as f:
                json.dump(default_ledger, f, indent=2, ensure_ascii=False)

    def load_vault(self) -> Dict[str, Any]:
        """Загрузка данных кошельков из хранилища."""
        try:
            with open(self.vault_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'Ошибка чтения wallet vault: {e}')
            return {}

    def save_vault(self, data: Dict[str, Any]):
        """Сохранение данных в хранилище с защитой прав доступа."""
        with open(self.vault_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.chmod(self.vault_file, 0o600)

    def load_ledger(self) -> Dict[str, Any]:
        """Загрузка реестра доходов/расходов."""
        try:
            with open(self.ledger_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'Ошибка чтения ledger: {e}')
            return {'total_earned_usd': 0.0, 'transactions': []}

    def save_ledger(self, ledger: Dict[str, Any]):
        """Сохранение реестра доходов/расходов."""
        with open(self.ledger_file, 'w', encoding='utf-8') as f:
            json.dump(ledger, f, indent=2, ensure_ascii=False)

    def get_public_addresses(self) -> Dict[str, Any]:
        """Возвращает публичные адреса 4 кошельков системы."""
        vault = self.load_vault()
        return vault.get('wallets', {})

    def record_income(self, amount_usd: float, source: str, task_id: str, network_token: str = 'USDT') -> Dict[str, Any]:
        """
        Фиксация поступившей прибыли и строгое разделение на 4 равные части (25% каждому):
        1. Разработчик - 25%
        2. Инвестор - 25%
        3. Персонал - 25%
        4. Система - 25% (расходуется системой по своему усмотрению)
        """
        ledger = self.load_ledger()
        ledger['total_earned_usd'] = ledger.get('total_earned_usd', 0.0) + amount_usd

        share = amount_usd * 0.25  # Ровно 25% каждой из 4 сторон

        shares = ledger.get('distribution_shares_usd', {
            'developer': 0.0,
            'investor': 0.0,
            'personnel': 0.0,
            'system': 0.0
        })

        shares['developer'] = shares.get('developer', 0.0) + share
        shares['investor'] = shares.get('investor', 0.0) + share
        shares['personnel'] = shares.get('personnel', 0.0) + share
        shares['system'] = shares.get('system', 0.0) + share

        ledger['distribution_shares_usd'] = shares

        tx = {
            'type': 'INCOME_SPLIT_4_WAY',
            'total_amount_usd': amount_usd,
            'share_per_wallet_usd': share,
            'breakdown': {
                'developer_25pct': share,
                'investor_25pct': share,
                'personnel_25pct': share,
                'system_25pct': share
            },
            'source': source,
            'task_id': task_id,
            'token': network_token,
            'timestamp': time.time(),
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        if 'transactions' not in ledger:
            ledger['transactions'] = []
        ledger['transactions'].append(tx)
        self.save_ledger(ledger)

        logger.info(
            f'💰 [CryptoWallet 4-Way Split] Зачислено ${amount_usd:.2f} ({source}). '
            f'Распределено по 25% (${share:.2f}): Разработчик, Инвестор, Персонал, Система.'
        )
        return tx

    def spend_system_budget(self, amount_usd: float, purpose: str) -> Dict[str, Any]:
        """
        Расход средств Системы (часть 4) по её собственному усмотрению
        (оплата VPS серверов, LLM API ключей, доменов).
        """
        ledger = self.load_ledger()
        shares = ledger.get('distribution_shares_usd', {})
        system_available = shares.get('system', 0.0)

        if system_available < amount_usd:
            return {
                'status': 'insufficient_funds',
                'requested': amount_usd,
                'available': system_available,
                'message': f'Недостаточно средств в автономном бюджете Системы (${system_available:.2f})'
            }

        shares['system'] -= amount_usd
        ledger['distribution_shares_usd'] = shares
        ledger['total_spent_system_usd'] = ledger.get('total_spent_system_usd', 0.0) + amount_usd

        tx = {
            'type': 'SYSTEM_EXPENSE',
            'amount_usd': amount_usd,
            'purpose': purpose,
            'timestamp': time.time(),
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        ledger['transactions'].append(tx)
        self.save_ledger(ledger)

        logger.info(f'💸 [System Budget Expense] Система потратила ${amount_usd:.2f} на "{purpose}". Остаток системного кошелька: ${shares["system"]:.2f}')
        return {
            'status': 'success',
            'spent_usd': amount_usd,
            'remaining_system_budget': shares['system']
        }

    def get_financial_summary(self) -> Dict[str, Any]:
        """Сводка балансов по всем 4 кошелькам и уровень самообеспечения."""
        ledger = self.load_ledger()
        costs = ledger.get('monthly_costs', DEFAULT_COSTS)
        total_monthly_need = sum(costs.values())

        total_earned = ledger.get('total_earned_usd', 0.0)
        shares = ledger.get('distribution_shares_usd', {
            'developer': 0.0,
            'investor': 0.0,
            'personnel': 0.0,
            'system': 0.0
        })

        system_budget = shares.get('system', 0.0)
        # Коэффициент покрытия операционных расходов из доли Системы (25%)
        system_sustainability_ratio = (system_budget / total_monthly_need) if total_monthly_need > 0 else 0.0

        wallets = self.get_public_addresses()

        return {
            'policy': '4_WAY_25_PERCENT_PROFIT_SPLIT',
            'total_earned_all_time_usd': round(total_earned, 2),
            'monthly_operating_cost_usd': round(total_monthly_need, 2),
            'system_sustainability_pct': round(system_sustainability_ratio * 100, 1),
            'wallet_balances_usd': {
                '1_developer_25pct': round(shares.get('developer', 0.0), 2),
                '2_investor_25pct': round(shares.get('investor', 0.0), 2),
                '3_personnel_25pct': round(shares.get('personnel', 0.0), 2),
                '4_system_autonomous_25pct': round(shares.get('system', 0.0), 2)
            },
            'wallets_addresses': wallets
        }


# Совместимость
class AIOSWallet(AIOSWalletManager):
    pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    wm = AIOSWalletManager()
    print('=== AIOS 4-WAY PROFIT DISTRIBUTION SUMMARY ===')
    print(json.dumps(wm.get_financial_summary(), indent=2, ensure_ascii=False))
