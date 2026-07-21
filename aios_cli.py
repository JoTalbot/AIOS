#!/usr/bin/env python3
"""
AIOS Command Line Interface v4.1
"""

import argparse
import asyncio
from aios_core import Orchestrator, Database
from aios_core.dashboard import create_dashboard
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="AIOS CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Run server
    run_parser = subparsers.add_parser("run", help="Run REST API")
    run_parser.add_argument("--host", default="127.0.0.1")
    run_parser.add_argument("--port", type=int, default=8000)

    # Run dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Run Web Dashboard")
    dash_parser.add_argument("--port", type=int, default=8080)

    # Demo
    subparsers.add_parser("demo", help="Run v4.1 demo")

    # Stats
    subparsers.add_parser("stats", help="Show system stats")

    args = parser.parse_args()

    if args.command == "run":
        from run_rest_api import main as run_main
        run_main()
    elif args.command == "dashboard":
        db = Database("aios.sqlite")
        orch = Orchestrator(db=db)
        app = create_dashboard(orch)
        print(f"Starting Dashboard on http://127.0.0.1:{args.port}")
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    elif args.command == "demo":
        from demo_v41 import main as demo_main
        demo_main()
    elif args.command == "stats":
        db = Database("aios.sqlite")
        orch = Orchestrator(db=db)
        import json
        print(json.dumps(orch.stats(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()