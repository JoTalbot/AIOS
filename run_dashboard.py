"""Run AIOS Dashboard"""

import uvicorn

from aios_core.container import container
from aios_core.dashboard import create_dashboard


def main():
    container.db()
    orch = container.orchestrator()

    app = create_dashboard(orch)
    print("🌐 Starting AIOS Dashboard on http://127.0.0.1:8080")
    uvicorn.run(app, host="127.0.0.1", port=8080)


# Gunicorn-compatible entry point
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
