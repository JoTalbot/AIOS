"""Run AIOS Dashboard"""

import argparse
import os

import uvicorn

from aios_core.container import container
from aios_core.dashboard import create_dashboard


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("AIOS_DASH_HOST", "0.0.0.0"))
    parser.add_argument("--port", default=int(os.environ.get("AIOS_DASH_PORT", "8580")), type=int)
    args = parser.parse_args()

    container.db()
    orch = container.orchestrator()

    app = create_dashboard(orch)
    print(f"🌐 Starting AIOS Dashboard on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


_app = None


def _get_app():
    global _app
    if _app is None:
        container.db()
        orch = container.orchestrator()
        _app = create_dashboard(orch)
    return _app


app = _get_app()
if __name__ == "__main__":
    main()
