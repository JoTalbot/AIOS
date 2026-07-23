#!/usr/bin/env python3
"""Run AIOS Dashboard"""

import uvicorn
from aios_core import Orchestrator, Database
from aios_core.dashboard import create_dashboard

def main():
    db = Database("aios.sqlite")
    orch = Orchestrator(db=db)

    app = create_dashboard(orch)
    print("🌐 Starting AIOS Dashboard on http://127.0.0.1:8080")
    uvicorn.run(app, host="127.0.0.1", port=8080)

if __name__ == "__main__":
    main()
