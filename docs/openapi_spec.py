"""AIOS OpenAPI 3.0 Specification Generator.

Auto-generates OpenAPI 3.0 spec from Starlette route definitions
and AIOS module metadata. Provides Swagger UI integration helpers.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = ["OpenAPIGenerator"]


class OpenAPIGenerator:
    """Generates OpenAPI 3.0 specification for AIOS REST API.

    Features:
    - Auto-generation from route definitions
    - Module metadata inclusion
    - Swagger UI HTML generation
    - Schema definitions for AIOS data models
    - Version tracking
    """

    def __init__(self, title: str = "AIOS API", version: str = "10.15.0"):
        """Initialize OpenAPIGenerator."""
        self.title = title
        self.version = version
        self._paths: dict[str, dict[str, Any]] = {}
        self._schemas: dict[str, dict[str, Any]] = {}
        self._tags: list[dict[str, Any]] = []

    def add_path(self, path: str, method: str, summary: str = "", responses: dict[int, dict] | None = None) -> None:
        """Register an API endpoint."""
        if path not in self._paths:
            self._paths[path] = {}
        self._paths[path][method.lower()] = {
            "summary": summary,
            "operationId": f"{method.lower()}_{path.replace('/', '_').strip('_')}",
            "responses": responses or {200: {"description": "Success"}},
            "tags": [path.split("/")[1] if len(path.split("/")) > 1 else "default"],
        }

    def add_schema(self, name: str, properties: dict[str, Any], description: str = "") -> None:
        """Register a data model schema."""
        self._schemas[name] = {
            "type": "object",
            "description": description,
            "properties": properties,
        }

    def add_tag(self, name: str, description: str = "") -> None:
        """Register an API tag group."""
        self._tags.append({"name": name, "description": description})

    def generate_spec(self) -> dict[str, Any]:
        """Generate full OpenAPI 3.0 specification."""
        return {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "AIOS — Autonomous Intelligent Operating System API",
                "contact": {"name": "AIOS Team", "email": "jo.talbot@gmail.com"},
                "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
            },
            "servers": [{"url": "http://localhost:8000", "description": "Development server"}],
            "paths": self._paths,
            "components": {"schemas": self._schemas},
            "tags": self._tags,
        }

    def generate_json(self) -> str:
        """Return OpenAPI spec as JSON string."""
        return json.dumps(self.generate_spec(), indent=2, ensure_ascii=False)

    def generate_swagger_ui_html(self, spec_url: str = "/openapi.json") -> str:
        """Generate Swagger UI HTML page."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.title} - Swagger UI</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
    SwaggerUIBundle({{
        url: "{spec_url}",
        dom_id: '#swagger-ui',
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
        layout: "BaseLayout"
    }})
    </script>
</body>
</html>"""

    # Auto-register AIOS standard endpoints
    def register_aios_endpoints(self) -> None:
        """Register standard AIOS API endpoints."""
        # Health
        self.add_path("/health", "GET", "Health check", {200: {"description": "System health status"}})
        self.add_path("/stats", "GET", "System statistics", {200: {"description": "Aggregated system stats"}})
        self.add_path("/version", "GET", "Get version", {200: {"description": "Current AIOS version"}})

        # Tasks
        self.add_path("/tasks", "GET", "List tasks", {200: {"description": "All task entries"}})
        self.add_path("/tasks", "POST", "Create task", {201: {"description": "Task created"}})
        self.add_path("/tasks/{id}", "GET", "Get task", {200: {"description": "Single task"}})

        # Events
        self.add_path("/events", "GET", "List events", {200: {"description": "Event history"}})

        # Tags
        self.add_tag("system", "System management endpoints")
        self.add_tag("tasks", "Task management endpoints")
        self.add_tag("events", "Event bus endpoints")

        # Schemas
        self.add_schema("HealthResponse", {
            "status": {"type": "string"},
            "version": {"type": "string"},
            "uptime_seconds": {"type": "number"},
        }, "Health check response")
        self.add_schema("StatsResponse", {
            "total_tasks": {"type": "integer"},
            "total_events": {"type": "integer"},
            "version": {"type": "string"},
        }, "System statistics response")
        self.add_schema("Task", {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "status": {"type": "string"},
        }, "Task object")
