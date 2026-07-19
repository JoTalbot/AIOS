#!/usr/bin/env python3
"""
AIOS REST API Server
====================

Runs the AIOS REST API using Starlette/Uvicorn.

Usage:
    python run_rest_api.py [--host HOST] [--port PORT] [--db DB_PATH]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aios_core.api.app import create_app
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="AIOS REST API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind to")
    parser.add_argument("--db", default=":memory:", help="Database path (default: :memory:)")
    parser.add_argument("--constitution-dir", default=None, help="Constitution directory")
    parser.add_argument("--policies-dir", default=None, help="Policies directory")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    constitution_dir = args.constitution_dir or os.path.join(project_root, "docs/constitution")
    policies_dir = args.policies_dir or os.path.join(project_root, "policies")

    print(f"Starting AIOS REST API...")
    print(f"  Constitution: {constitution_dir}")
    print(f"  Policies: {policies_dir}")
    print(f"  Database: {args.db}")
    print(f"  Server: http://{args.host}:{args.port}")
    print(f"  API docs: http://{args.host}:{args.port}/api/v1/")
    print()

    app = create_app(
        db_path=args.db,
        constitution_dir=constitution_dir,
        policies_dir=policies_dir,
    )

    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()