#!/usr/bin/env python3
"""
AIOS Web Administrator & SRE Self-Healing Entrypoint
Периодический аудит аптайма веб-служб и автоматическое SRE-самовосстановление.
"""

import sys
import os
import argparse
import logging
import json
from pathlib import Path

# Убедимся, что корень проекта импортируем
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aios_core.web_administrator import AIOSWebAdministrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunDevOps")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS SRE Autopilot & Web Administrator")
    parser.add_argument("--probe", action="store_true", help="Провести активное HTTP зондирование служб (по умолчанию)")
    parser.add_argument("--heal", action="store_true", help="Запустить автоматическое выявление и исправление сбоев")
    args = parser.parse_args()

    admin = AIOSWebAdministrator()

    if args.heal:
        logger.info("🛠 [RunDevOps] Запуск SRE-контура авто-выявления и исправления сбоев...")
        probes = admin.probe_services()
        healed_actions = []
        
        for p in probes:
            if not p["is_healthy"]:
                logger.warning(f"🚨 [RunDevOps] Обнаружен сбой службы {p['service_name']} (HTTP {p['status_code']})!")
                heal_res = admin.run_self_healing_action(p["service_name"], p["error"])
                healed_actions.append(heal_res)
                
        print("\n=== AIOS SELF-HEALING EXECUTION SUMMARY ===")
        print(json.dumps(healed_actions, indent=2, ensure_ascii=False))
    else:
        # По умолчанию - опрашиваем баланс/аптайм
        logger.info("🔎 [RunDevOps] Запуск активного HTTP-зондирования веб-служб...")
        res = admin.probe_services()
        print("\n=== AIOS SERVICES PROBING REPORT ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
