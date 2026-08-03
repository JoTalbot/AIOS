"""CLI для отладки/демонстрации автономии (без реальных действий).

Примеры:
  python -m aios_core.autonomy.cli --sim "сколько стоит фара?"
  python -m aios_core.autonomy.cli --sim "могу уступить? скидку сделай, фару возьму за 1500"
  python -m aios_core.autonomy.cli --decision "привет"
  python -m aios_core.autonomy.cli --status
"""
from __future__ import annotations

import argparse
import json


def _main() -> None:
    ap = argparse.ArgumentParser(description="AIOS Autonomy CLI")
    ap.add_argument("--sim", help="Прогнать вход покупателя через петлю (без реальных действий)")
    ap.add_argument("--decision", help="Показать guardrail-решение для действия/текста")
    ap.add_argument("--status", action="store_true", help="Статус политики и журнала")
    args = ap.parse_args()

    from . import AutonomyCore, AutonomyPolicy, Journal
    core = AutonomyCore()
    policy = core.policy

    if args.status:
        print(json.dumps({
            "enabled": policy.enabled,
            "floor_global": policy.floor_global,
            "max_auto_discount_pct": policy.max_auto_discount_pct,
            "allowed_schemes": policy.allowed_schemes,
            "floors": policy.floors.get("items", {}),
            "journal": Journal().summary(),
        }, ensure_ascii=False, indent=2))
        return

    if args.decision:
        # создать временный proposal из интента
        from .planner import Planner
        proposal = Planner(policy).propose("olx", "demo", args.decision, owner=False)
        dec = core.guardrails.evaluate(proposal, {"customer_trust": "new"})
        print(json.dumps({"proposal": proposal, "decision": {
            "verdict": dec.verdict, "reason": dec.reason,
            "rules": dec.matched_rules, "meta": dec.meta,
        }}, ensure_ascii=False, indent=2))
        return

    if args.sim:
        out = core.process_customer("olx", "sim_chat", args.sim, msg_id="sim1")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    ap.print_help()


if __name__ == "__main__":
    _main()
