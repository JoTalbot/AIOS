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

import uvicorn

from aios_core.api.app import create_app


def main():
    parser = argparse.ArgumentParser(description="AIOS REST API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind to")
    parser.add_argument("--db", default="aios.sqlite", help="Database path (default: aios.sqlite)")
    parser.add_argument("--constitution-dir", default=None, help="Constitution directory")
    parser.add_argument("--policies-dir", default=None, help="Policies directory")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    constitution_dir = args.constitution_dir or os.path.join(project_root, "docs/constitution")
    policies_dir = args.policies_dir or os.path.join(project_root, "policies")

    print("Starting AIOS REST API...")
    print(f"  Constitution: {constitution_dir}")
    print(f"  Policies: {policies_dir}")
    print(f"  Database: {args.db}")
    print(f"  Server: http://{args.host}:{args.port}")
    print(f"  API docs: http://{args.host}:{args.port}/docs")
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


# Gunicorn-compatible entry point
# Usage: gunicorn run_rest_api:app --bind 0.0.0.0:8000 --workers 4 -k uvicorn.workers.UvicornWorker
_app = None


def _get_app():
    """Create or return the cached Starlette application."""
    global _app
    if _app is None:
        import os
        root = os.path.dirname(os.path.abspath(__file__))
        const_dir = os.environ.get("AIOS_CONSTITUTION_DIR", os.path.join(root, "docs/constitution"))
        pol_dir = os.environ.get("AIOS_POLICIES_DIR", os.path.join(root, "policies"))
        db_path = os.environ.get("AIOS_DB_PATH", os.path.join(root, "aios.sqlite"))
        _app = create_app(
            db_path=db_path,
            constitution_dir=const_dir,
            policies_dir=pol_dir,
        )
    return _app
# Exported app for gunicorn/uvicorn discovery
app = _get_app()


if __name__ == "__main__":
    main()
