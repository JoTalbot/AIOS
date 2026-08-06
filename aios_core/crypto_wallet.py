"""
AIOS Multi-Chain Crypto Wallet & Self-Funding Budget Manager
Модуль криптокошелька и автономной финансовой самообеспеченности AIOS.
Управляет балансами (EVM/TRC20/Solana), vault-хранилищем, отслеживанием доходов/расходов
и автоматическим перераспределением средств на оплату VPS и LLM API.
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
    """Управление Web3/Крипто-кошельками и бюджетом самообеспечения AIOS."""

    def __init__(self, data_dir: str = '/root/AIOS/data'):
        self.data_dir = Path(data_dir)
        self.vault_file = self.data_dir / '.wallet_vault.json'
        self.ledger_file = self.data_dir / 'self_funding_ledger.json'
        self._ensure_files()

    def _ensure_files(self):
        """Создание файлов хранения при их отсутствии."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.vault_file.exists():
            default_vault = {
                'evm_address': '0x00000000000000000000000000000000000AIOS',
                'trc20_address': 'T_AIOS_SELF_FUNDING_TRC20_ADDRESS',
                'solana_address': 'AIOS_SOLANA_SELF_FUNDING_ADDRESS',
                'networks': {
                    'polygon': {'enabled': True},
                    'arbitrum': {'enabled': True},
                    'base': {'enabled': True}
                },
                'keys_encrypted': False,
                'private_key': ''
            }
            with open(self.vault_file, 'w', encoding='utf-8') as f:
                json.dump(default_vault, f, indent=2, ensure_ascii=False)
            os.chmod(self.vault_file, 0o600)

        if not self.ledger_file.exists():
            default_ledger = {
                'total_earned_usd': 0.0,
                'total_spent_usd': 0.0,
                'llm_balance_allocated_usd': 0.0,
                'server_reserve_usd': 0.0,
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
            return {'total_earned_usd': 0.0, 'total_spent_usd': 0.0, 'transactions': []}

    def save_ledger(self, ledger: Dict[str, Any]):
        """Сохранение реестра доходов/расходов."""
        with open(self.ledger_file, 'w', encoding='utf-8') as f:
            json.dump(ledger, f, indent=2, ensure_ascii=False)

    def get_public_addresses(self) -> Dict[str, str]:
        """Возвращает публичные адреса кошельков для получения оплаты."""
        vault = self.load_vault()
        return {
            'EVM (ETH/Polygon/Arbitrum/Base/BSC)': vault.get('evm_address', ''),
            'TRC20 (USDT Tron)': vault.get('trc20_address', ''),
            'Solana': vault.get('solana_address', '')
        }

    def check_evm_balance(self, network: str = 'polygon') -> Dict[str, Any]:
        """Проверка баланса на EVM-сети через публичные RPC."""
        vault = self.load_vault()
        address = vault.get('evm_address', '')
        if not address or address.endswith('AIOS'):
            return {
                'network': network,
                'address': address,
                'native_balance': 0.0,
                'symbol': 'ETH' if network != 'polygon' else 'MATIC',
                'is_mock': True
            }

        rpc_urls = PUBLIC_RPC_NODES.get(network, PUBLIC_RPC_NODES['polygon'])
        for rpc in rpc_urls:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 5}))
                if w3.is_connected():
                    balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
                    balance_eth = balance_wei / 10**18
                    symbol = 'MATIC' if network == 'polygon' else ('BNB' if network == 'bsc' else 'ETH')
                    return {
                        'network': network,
                        'address': address,
                        'native_balance': float(balance_eth),
                        'symbol': symbol,
                        'is_mock': False
                    }
            except Exception as e:
                logger.warning(f'⚠️ RPC {rpc} недоступен: {e}')

        return {
            'network': network,
            'address': address,
            'native_balance': 0.0,
            'symbol': 'ETH',
            'is_mock': True,
            'error': 'All RPCs timed out'
        }

    def record_income(self, amount_usd: float, source: str, task_id: str, network_token: str = 'USDT') -> Dict[str, Any]:
        """Фиксация заработанных денег от выполненной фриланс-задачи."""
        ledger = self.load_ledger()
        ledger['total_earned_usd'] = ledger.get('total_earned_usd', 0.0) + amount_usd

        # Перераспределение доходов по правилам бюджета
        llm_share = amount_usd * 0.50     # 50% на LLM API
        server_share = amount_usd * 0.50  # 50% в резерв сервера

        ledger['llm_balance_allocated_usd'] = ledger.get('llm_balance_allocated_usd', 0.0) + llm_share
        ledger['server_reserve_usd'] = ledger.get('server_reserve_usd', 0.0) + server_share

        tx = {
            'type': 'INCOME',
            'amount_usd': amount_usd,
            'source': source,
            'task_id': task_id,
            'token': network_token,
            'llm_share_usd': llm_share,
            'server_share_usd': server_share,
            'timestamp': time.time(),
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        if 'transactions' not in ledger:
            ledger['transactions'] = []
        ledger['transactions'].append(tx)
        self.save_ledger(ledger)

        logger.info(f'💰 [CryptoWallet] Зачислено ${amount_usd:.2f} ({source}). Резерв LLM: +${llm_share:.2f}, Резерв VPS: +${server_share:.2f}')
        return tx

    def allocate_budget_for_llm(self, amount_usd: Optional[float] = None) -> Dict[str, Any]:
        """Выделение средств из баланса на оплату LLM API."""
        ledger = self.load_ledger()
        available = ledger.get('llm_balance_allocated_usd', 0.0)

        if amount_usd is None:
            amount_usd = min(available, 10.0)

        if available < amount_usd and available <= 0:
            return {
                'status': 'insufficient_funds',
                'requested': amount_usd,
                'available': available,
                'message': f'Недостаточно накопленных средств в резерве LLM (${available:.2f})'
            }

        actual_spent = min(available, amount_usd)
        ledger['llm_balance_allocated_usd'] -= actual_spent
        ledger['total_spent_usd'] = ledger.get('total_spent_usd', 0.0) + actual_spent

        tx = {
            'type': 'EXPENSE_LLM',
            'amount_usd': actual_spent,
            'timestamp': time.time(),
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        if 'transactions' not in ledger:
            ledger['transactions'] = []
        ledger['transactions'].append(tx)
        self.save_ledger(ledger)

        rem = ledger['llm_balance_allocated_usd']
        logger.info(f'💸 [CryptoWallet] Выделен бюджет на LLM API: ${actual_spent:.2f}. Остаток LLM резерва: ${rem:.2f}')
        return {
            'status': 'success',
            'allocated_usd': actual_spent,
            'remaining_llm_reserve': rem
        }

    def get_financial_summary(self) -> Dict[str, Any]:
        """Формирует сводку о финансовом состоянии и уровне самообеспечения AIOS."""
        ledger = self.load_ledger()
        costs = ledger.get('monthly_costs', DEFAULT_COSTS)
        total_monthly_need = sum(costs.values())

        total_earned = ledger.get('total_earned_usd', 0.0)
        total_spent = ledger.get('total_spent_usd', 0.0)
        llm_reserve = ledger.get('llm_balance_allocated_usd', 0.0)
        server_reserve = ledger.get('server_reserve_usd', 0.0)

        # Коэффициент автономной самообеспеченности (Self-Sufficiency Index)
        self_sustainability_ratio = (total_earned / total_monthly_need) if total_monthly_need > 0 else 0.0

        addresses = self.get_public_addresses()

        return {
            'self_sustainability_pct': round(self_sustainability_ratio * 100, 1),
            'total_earned_usd': round(total_earned, 2),
            'total_spent_usd': round(total_spent, 2),
            'llm_reserve_usd': round(llm_reserve, 2),
            'server_reserve_usd': round(server_reserve, 2),
            'monthly_operating_need_usd': round(total_monthly_need, 2),
            'addresses': addresses
        }


# Совместимость со старым API
class AIOSWallet(AIOSWalletManager):
    def check_balance(self):
        res = self.check_evm_balance('polygon')
        return res.get('native_balance', 0.0)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    wm = AIOSWalletManager()
    print('=== AIOS CRYPTO WALLET SUMMARY ===')
    print(json.dumps(wm.get_financial_summary(), indent=2, ensure_ascii=False))
