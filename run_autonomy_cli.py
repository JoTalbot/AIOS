#!/usr/bin/env python3
"""
AIOS Autonomy CLI — работа с автономным контуром вручную / по расписанию.

Примеры:
  python run_autonomy_cli.py sim "сколько стоит фара?"        # прогнать вход покупателя
  python run_autonomy_cli.py owner "продал фару за 2000"      # выполнить команду владельца
  python run_autonomy_cli.py owner "что на складе"
  python run_autonomy_cli.py status                            # статус политики
  python run_autonomy_cli.py resolve <id> --approve|--reject   # подтвердить/отклонить
  python run_autonomy_cli.py olx --once                        # один цикл OLX-автоответа
  python run_autonomy_cli.py olx --loop --interval 300         # демон OLX-автоответа
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _main() -> None:
    ap = argparse.ArgumentParser(description="AIOS Autonomy CLI")
    sub = ap.add_subparsers(dest="cmd")

    p_sim = sub.add_parser("sim", help="Прогнать сообщение покупателя через петлю")
    p_sim.add_argument("text")

    p_own = sub.add_parser("owner", help="Выполнить команду владельца")
    p_own.add_argument("text")

    p_st = sub.add_parser("status", help="Статус политики/журнала")

    p_res = sub.add_parser("resolve", help="Подтвердить/отклонить approval")
    p_res.add_argument("id")
    p_res.add_argument("--approve", action="store_true")
    p_res.add_argument("--reject", action="store_true")

    p_olx = sub.add_parser("olx", help="Цикл OLX-автоответа")
    p_olx.add_argument("--once", action="store_true")
    p_olx.add_argument("--loop", action="store_true")
    p_olx.add_argument("--interval", type=int, default=300)

    args = ap.parse_args()

    from aios_core.autonomy import AutonomyCore, AutonomyPolicy, Journal

    if args.cmd == "status":
        p = AutonomyPolicy()
        print(json.dumps({
            "enabled": p.enabled,
            "floor_global": p.floor_global,
            "max_auto_discount_pct": p.max_auto_discount_pct,
            "allowed_schemes": p.allowed_schemes,
            "always_manual": [k for k, v in p.esc_all.items() if v],
            "floors": p.floors.get("items", {}),
            "journal": Journal().summary(),
        }, ensure_ascii=False, indent=2))
        return

    core = AutonomyCore()

    if args.cmd == "sim":
        out = core.process_customer("olx", "cli_sim", args.text, msg_id=f"cli_{time.time()}")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if args.cmd == "owner":
        out = core.process_owner("cli_owner", args.text)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if args.cmd == "resolve":
        if not (args.approve or args.reject):
            print("Укажите --approve или --reject"); sys.exit(1)
        print(json.dumps(core.confirm(args.id, approve=args.approve), ensure_ascii=False, indent=2))
        return

    if args.cmd == "olx":
        import run_olx_autoreply as _oa
        if args.once:
            sys.exit(_oa.main())
        if args.loop:
            print(f"🔁 OLX-автоответ: loop каждые {args.interval}с (Ctrl+C для выхода)")
            while True:
                try:
                    _oa.main()
                except Exception as e:
                    print(f"  [olx-loop] error: {e}")
                time.sleep(args.interval)
        return

    ap.print_help()


if __name__ == "__main__":
    _main()
