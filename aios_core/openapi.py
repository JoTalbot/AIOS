"""OpenAPI Documentation Generator for AIOS"""

from typing import Dict, Any


def generate_openapi_spec() -> Dict[str, Any]:
    """Generate basic OpenAPI 3.0 spec for AIOS API."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "AIOS API",
            "version": "9.0.0-alpha.22",
            "description": "Self-evolving Distributed Operating System API"
        },
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/api/v1/stats": {
                "get": {
                    "summary": "System statistics",
                    "responses": {"200": {"description": "Stats"}}
                }
            },
            "/api/v1/tasks": {
                "post": {
                    "summary": "Create task",
                    "responses": {"201": {"description": "Task created"}}
                }
            }
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer"
                }
            }
        }
    }