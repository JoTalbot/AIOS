"""
AIOS Kraken Exchange Integration Client
Модуль взаимодействия с международной биржей Kraken через официальный REST API.
"""
from __future__ import annotations

import os
import json
import time
import hmac
import hashlib
import base64
import urllib.request
import urllib.parse
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger("AIOS.Kraken")


class AIOSKrakenClient:
    """Облегченный, безопасный клиент для работы с биржей Kraken."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        # Умное разрешение путей (Docker/Host)
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.data_dir = Path(data_dir)
        self.api_key = "6RSeDhMbOhHUrIj1MpjchdYyeaqPtXi4wjM2pkOpNw9hl/8SNtjlR3Jz"
        self.api_secret = "kR1xeitjapqjmDZCIxwGUgOz5+DStIA1QPFMacjDrRpICyCCy5RzTmOc7s2BJm7YTcKQej5DkBiLSWxq7DNCOg=="

    def _get_signature(self, urlpath: str, data: dict) -> str:
        """Расчет HMAC-SHA512 подписи для приватных запросов."""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def _query(self, category: str, endpoint: str, data: dict = {}) -> Dict[str, Any]:
        """Универсальный метод выполнения запросов к API Kraken."""
        urlpath = f"/0/{category}/{endpoint}"
        url = f"https://api.kraken.com{urlpath}"
        
        headers = {
            "User-Agent": "AIOS-Kraken-Client/1.0",
        }

        if category == "private":
            data['nonce'] = int(1000 * time.time())
            headers["API-Key"] = self.api_key
            headers["API-Sign"] = self._get_signature(urlpath, data)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            postdata = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(url, data=postdata, headers=headers, method="POST")
        else:
            if data:
                url += "?" + urllib.parse.urlencode(data)
            req = urllib.request.Request(url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Ошибка API Kraken ({endpoint}): {e}")
            return {"error": [str(e)]}

    def get_account_balance(self) -> Dict[str, Any]:
        """Запрашивает реальные балансы всех удерживаемых активов на аккаунте Kraken."""
        res = self._query("private", "Balance")
        if res.get("error"):
            return {"status": "error", "error": res["error"]}
        
        # Фильтруем нулевые балансы
        raw_balances = res.get("result", {})
        active_balances = {}
        for asset, amount in raw_balances.items():
            amt = float(amount)
            if amt > 0:
                active_balances[asset] = amt
                
        return {
            "status": "success",
            "balances": active_balances,
            "raw_result": raw_balances
        }

    def get_ticker(self, pair: str = "XXBTZUSD") -> Dict[str, Any]:
        """Запрашивает живые котировки по торговой паре (например, BTCUSD)."""
        res = self._query("public", "Ticker", {"pair": pair.upper()})
        if res.get("error"):
            return {"status": "error", "error": res["error"]}
        return {
            "status": "success",
            "ticker": res.get("result", {})
        }

    def add_market_order(self, pair: str, side: str, volume: float) -> Dict[str, Any]:
        """Создает и исполняет реальный рыночный (Market) ордер купли-продажи на бирже Kraken."""
        params = {
            "pair": pair.upper(),
            "type": side.lower(), # buy или sell
            "ordertype": "market",
            "volume": str(volume)
        }
        res = self._query("private", "AddOrder", params)
        if res.get("error"):
            return {"status": "error", "error": res["error"]}
        return {
            "status": "success",
            "tx_ids": res.get("result", {}).get("txid", []),
            "description": res.get("result", {}).get("descr", {}).get("order", "")
        }
