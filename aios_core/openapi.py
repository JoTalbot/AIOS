"""OpenAPI Documentation Generator for AIOS v10.9.0.

OpenAPI 3.0 spec generation with path registration,
schema definitions, security schemes, version
management, and spec validation.

Classes:
    APIEndpoint   — registered API endpoint
    OpenAPISpec   — spec builder
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class APIEndpoint:
    """Registered API endpoint."""

    path: str
    method: str = "get"
    summary: str = ""
    description: str = ""
    request_body: dict[str, Any] = field(default_factory=dict)
    responses: dict[str, str] = field(default_factory=dict)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    security: list[str] = field(default_factory=list)


class OpenAPISpec:
    """OpenAPI specification builder.

    Features:
    - Path/endpoint registration
    - Schema definition management
    - Security scheme registration
    - Version tracking
    - Spec generation
    - Validation
    """

    def __init__(self, title: str = "AIOS API", version: str = "10.9.0") -> None:
        self.title = title
        self.version = version
        self._endpoints: list[APIEndpoint] = []
        self._schemas: dict[str, dict[str, Any]] = {}
        self._security_schemes: dict[str, dict[str, Any]] = {}

    def add_endpoint(
        self,
        path: str,
        method: str = "get",
        summary: str = "",
        responses: dict[str, str] | None = None,
    ) -> None:
        """Add an API endpoint."""
        endpoint = APIEndpoint(
            path=path,
            method=method,
            summary=summary,
            responses=responses or {"200": "OK"},
        )
        self._endpoints.append(endpoint)

    def add_schema(self, name: str, schema: dict[str, Any]) -> None:
        """Add a schema definition."""
        self._schemas[name] = schema

    def add_security_scheme(self, name: str, scheme: dict[str, Any]) -> None:
        """Add a security scheme."""
        self._security_schemes[name] = scheme

    def generate_spec(self) -> dict[str, Any]:
        """Generate full OpenAPI 3.0 specification."""
        paths = {}
        for ep in self._endpoints:
            if ep.path not in paths:
                paths[ep.path] = {}
            paths[ep.path][ep.method] = {
                "summary": ep.summary,
                "description": ep.description,
                "responses": ep.responses,
                "parameters": ep.parameters,
                "tags": ["default"],
            }

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "Self-evolving Distributed Operating System API",
            },
            "paths": paths,
            "components": {
                "schemas": self._schemas,
                "securitySchemes": self._security_schemes
                or {
                    "BearerAuth": {"type": "http", "scheme": "bearer"},
                },
            },
        }
        return spec

    def validate_spec(self) -> dict[str, Any]:
        """Validate the generated spec."""
        spec = self.generate_spec()
        issues = []
        if not spec.get("openapi"):
            issues.append("Missing openapi version")
        if not spec.get("info"):
            issues.append("Missing info section")
        if not spec.get("paths"):
            issues.append("No paths defined")
        return {"valid": len(issues) == 0, "issues": issues}

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "endpoints": len(self._endpoints),
            "schemas": len(self._schemas),
            "security_schemes": len(self._security_schemes),
            "version": self.version,
        }


def generate_openapi_spec() -> dict[str, Any]:
    """Generate basic OpenAPI 3.0 spec (backward-compatible)."""
    builder = OpenAPISpec()
    builder.add_endpoint("/health", "get", "Health check", {"200": "OK"})
    builder.add_endpoint("/api/v1/stats", "get", "System statistics", {"200": "Stats"})
    builder.add_endpoint(
        "/api/v1/tasks", "post", "Create task", {"201": "Task created"}
    )
    builder.add_security_scheme("BearerAuth", {"type": "http", "scheme": "bearer"})
    return builder.generate_spec()
