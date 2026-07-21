"""AIOS Web Dashboard v4.0.0-alpha

Simple web interface for monitoring and controlling AIOS.
Built on Starlette (same as the main API).
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route, Mount
from starlette.requests import Request

from .orchestrator import Orchestrator


class AIOSDashboard:
    """Lightweight web dashboard for AIOS."""

    def __init__(self, orchestrator: Orchestrator):
        self.orch = orchestrator

    async def index(self, request: Request):
        """Main dashboard page."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AIOS Dashboard v4.0</title>
            <style>
                body {{ font-family: system-ui, sans-serif; margin: 40px; background: #0f172a; color: #e2e8f0; }}
                .card {{ background: #1e2937; padding: 20px; border-radius: 12px; margin-bottom: 20px; }}
                h1 {{ color: #60a5fa; }}
                .stat {{ display: inline-block; margin: 10px 20px; }}
                .label {{ color: #94a3b8; font-size: 0.9rem; }}
                .value {{ font-size: 1.8rem; font-weight: 600; }}
            </style>
        </head>
        <body>
            <h1>🚀 AIOS Dashboard</h1>
            <p>Version: {self.orch.version}</p>

            <div class="card">
                <h2>System Stats</h2>
                <div id="stats"></div>
            </div>

            <div class="card">
                <h2>Quick Actions</h2>
                <button onclick="location.reload()">Refresh</button>
                <button onclick="runHealthCheck()">Health Check</button>
            </div>

            <script>
                async function loadStats() {{
                    const res = await fetch('/api/stats');
                    const data = await res.json();
                    const container = document.getElementById('stats');
                    container.innerHTML = `
                        <div class="stat"><div class="label">Tasks</div><div class="value">${{data.total_tasks || 0}}</div></div>
                        <div class="stat"><div class="label">Active</div><div class="value">${{data.active_tasks || 0}}</div></div>
                        <div class="stat"><div class="label">Memory Items</div><div class="value">${{data.memory_items || 0}}</div></div>
                        <div class="stat"><div class="label">Federation Nodes</div><div class="value">${{data.subsystems?.federation?.total_nodes || 0}}</div></div>
                    `;
                }}
                loadStats();

                async function runHealthCheck() {{
                    const res = await fetch('/health');
                    alert('Health: ' + (await res.json()).status);
                }}

                setInterval(loadStats, 15000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)

    async def api_stats(self, request: Request):
        return JSONResponse(self.orch.stats())

    def create_app(self):
        routes = [
            Route("/", self.index),
            Route("/api/stats", self.api_stats),
        ]
        return Starlette(routes=routes)


def create_dashboard(orchestrator: Orchestrator):
    """Factory function."""
    dashboard = AIOSDashboard(orchestrator)
    return dashboard.create_app()