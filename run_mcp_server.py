#!/usr/bin/env python3
"""
MCP Gateway Server
==================

Runs the AIOS MCP Gateway as an HTTP server for JSON-RPC 2.0 requests.

Usage:
    python run_mcp_server.py [--host HOST] [--port PORT] [--db DB_PATH]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aios_core.mcp.gateway import MCPGateway, GatewayConfig
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from aios_core.api.security import APIKeyAuthMiddleware
import uvicorn


async def rpc_endpoint(request: Request, gateway: MCPGateway):
    """Handle JSON-RPC requests via HTTP POST."""
    body = await request.body()
    try:
        raw = body.decode("utf-8")
    except Exception:
        raw = "{}"

    response_str = gateway.handle_request(raw)
    if response_str is None:
        return JSONResponse({"processed": True})
    import json
    return JSONResponse(json.loads(response_str), media_type="application/json")


async def health(request: Request):
    return JSONResponse({"status": "ok", "service": "aios-mcp-gateway"})


def create_starlette_app(gateway: MCPGateway) -> Starlette:
    async def rpc_handler(request: Request):
        return await rpc_endpoint(request, gateway)

    routes = [
        Route("/health", health, methods=["GET"]),
        Route("/rpc", rpc_handler, methods=["POST"]),
    ]
    return Starlette(
        routes=routes,
        middleware=[
            Middleware(APIKeyAuthMiddleware, enabled=True),
            Middleware(CORSMiddleware, allow_origins=[], allow_methods=["POST"], allow_headers=["Authorization", "Content-Type"]),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="AIOS MCP Gateway Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", default=8471, type=int, help="Port to bind to")
    parser.add_argument("--db", default=":memory:", help="Database path (default: :memory:)")
    parser.add_argument("--constitution-dir", default=None, help="Constitution directory")
    parser.add_argument("--policies-dir", default=None, help="Policies directory")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    constitution_dir = args.constitution_dir or os.path.join(project_root, "docs/constitution")
    policies_dir = args.policies_dir or os.path.join(project_root, "policies")

    print(f"Starting AIOS MCP Gateway...")
    print(f"  Constitution: {constitution_dir}")
    print(f"  Policies: {policies_dir}")
    print(f"  Database: {args.db}")
    print(f"  Server: http://{args.host}:{args.port}")
    print(f"  RPC endpoint: http://{args.host}:{args.port}/rpc")
    print()

    gateway = MCPGateway(GatewayConfig(
        host=args.host,
        port=args.port,
        constitution_dir=constitution_dir,
        policies_dir=policies_dir,
        db_path=args.db,
    ))

    app = create_starlette_app(gateway)

    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        gateway.close()


if __name__ == "__main__":
    main()
