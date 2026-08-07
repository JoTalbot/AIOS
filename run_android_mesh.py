#!/usr/bin/env python3
"""
AIOS Android Mesh Runner v19.3
Управление fleet из N реальных телефонов.

Usage:
  python run_android_mesh.py --status
  python run_android_mesh.py --telegram
  python run_android_mesh.py --register 10.203.0.2:46037 --name G1 --model "Pixel 7" --android 15
  python run_android_mesh.py --register 10.203.0.3:46038 --name G2 --model "Samsung S23" --android 14
  python run_android_mesh.py --list
  python run_android_mesh.py --lease task_123 --app olx
  python run_android_mesh.py --release 10.203.0.2:46037
  python run_android_mesh.py --heartbeat 10.203.0.2:46037 --battery 85
  python run_android_mesh.py --route --app olx --task-id olx_chat_123
  python run_android_mesh.py --daemon --interval 60  # reap stale + health
"""
import sys
import json
import time
import argparse
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from aios_core.android_mesh import AndroidMeshFleet

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AIOS.RunAndroidMesh")

def main():
    parser = argparse.ArgumentParser(description="AIOS Android Mesh v19.3")
    parser.add_argument("--status", action="store_true", help="JSON stats")
    parser.add_argument("--telegram", action="store_true", help="Telegram markdown report")
    parser.add_argument("--list", action="store_true", help="List devices")
    parser.add_argument("--register", type=str, help="Serial IP:port to register")
    parser.add_argument("--name", type=str, default="", help="Device name G1/G2")
    parser.add_argument("--model", type=str, default="", help="Model")
    parser.add_argument("--android", type=str, default="", dest="android_version", help="Android version")
    parser.add_argument("--remove", type=str, help="Remove device serial")
    parser.add_argument("--lease", type=str, help="Lease device for task_id")
    parser.add_argument("--app", type=str, default=None, help="Require app for lease/route (olx, abank, whatsapp)")
    parser.add_argument("--release", type=str, help="Release device serial or task_id")
    parser.add_argument("--heartbeat", type=str, help="Heartbeat serial")
    parser.add_argument("--battery", type=int, default=None, help="Battery pct for heartbeat")
    parser.add_argument("--route", action="store_true", help="Route task (needs --app)")
    parser.add_argument("--task-id", type=str, default=None, dest="task_id", help="Task ID for route")
    parser.add_argument("--daemon", action="store_true", help="Daemon mode")
    parser.add_argument("--interval", type=int, default=60, help="Daemon interval sec")
    args = parser.parse_args()

    fleet = AndroidMeshFleet()

    if args.register:
        dev = fleet.register_device(serial=args.register, name=args.name, model=args.model, android_version=args.android_version)
        print(json.dumps(dev.to_dict(), indent=2, ensure_ascii=False))
        return

    if args.remove:
        ok = fleet.remove_device(args.remove)
        print(json.dumps({"status": "removed" if ok else "not_found", "serial": args.remove}, indent=2, ensure_ascii=False))
        return

    if args.lease:
        dev = fleet.lease_device(task_id=args.lease, require_app=args.app)
        if dev:
            print(json.dumps({"status": "leased", "device": dev.to_dict()}, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"status": "no_device", "error": "No idle device"}, indent=2, ensure_ascii=False))
        return

    if args.release:
        dev = fleet.release_device(args.release)
        print(json.dumps({"status": "released" if dev else "not_found", "device": dev.to_dict() if dev else None}, indent=2, ensure_ascii=False))
        return

    if args.heartbeat:
        ok = fleet.heartbeat(args.heartbeat, battery=args.battery)
        print(json.dumps({"status": "heartbeat_ok" if ok else "not_found", "serial": args.heartbeat}, indent=2, ensure_ascii=False))
        return

    if args.route:
        task = {"id": args.task_id or f"task_{int(time.time())}", "app": args.app}
        res = fleet.route_task(task)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.telegram:
        print(fleet.generate_telegram_report())
        return

    if args.list:
        devices = fleet.list_devices()
        print(json.dumps([d.to_dict() for d in devices], indent=2, ensure_ascii=False))
        return

    if args.status:
        print(json.dumps(fleet.stats(), indent=2, ensure_ascii=False))
        return

    if args.daemon:
        logger.info(f"🚀 Android Mesh daemon interval {args.interval}s")
        while True:
            try:
                stale = fleet.reap_stale(stale_sec=600)
                if stale:
                    logger.warning(f"Reaped stale: {stale}")
                stats = fleet.stats()
                logger.info(f"📱 Mesh stats total {stats['total']} online {stats['online']} idle {stats['idle']} busy {stats['busy']}")
                time.sleep(args.interval)
            except Exception as e:
                logger.error(f"Daemon error: {e}")
                time.sleep(args.interval)
        return

    # default status
    print(json.dumps(fleet.stats(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
