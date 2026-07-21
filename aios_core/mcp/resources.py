"""AIOS MCP Resource Registry v1.0.0

Registration and serving of MCP resources.
Resources are read-only data sources that agents can read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .protocol import MCPResource, MCPResourceContent


@dataclass
class ResourceDefinition:
    """Definition of an MCP resource."""

    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"
    provider: Optional[Callable[[], str]] = None  # Function that returns resource content
    category: str = "general"


class ResourceRegistry:
    """Registry for MCP resources.

    Resources are read-only data sources identified by URI.
    Each resource has a provider function that generates its content
    when read.
    """

    def __init__(self):
        self._resources: dict[str, ResourceDefinition] = {}

    def register(self, resource: ResourceDefinition) -> None:
        """Register a resource.

        Args:
            resource: The ResourceDefinition to register.

        Raises:
            ValueError: If a resource with the same URI is already registered.
        """
        if resource.uri in self._resources:
            raise ValueError(f"Resource already registered: {resource.uri}")
        self._resources[resource.uri] = resource

    def unregister(self, uri: str) -> bool:
        """Unregister a resource by URI.

        Args:
            uri: Resource URI to remove.

        Returns:
            True if found and removed, False otherwise.
        """
        if uri in self._resources:
            del self._resources[uri]
            return True
        return False

    def get(self, uri: str) -> Optional[ResourceDefinition]:
        """Get a resource definition by URI.

        Args:
            uri: Resource URI to look up.

        Returns:
            The ResourceDefinition or None if not found.
        """
        return self._resources.get(uri)

    def list_resources(self) -> list[dict]:
        """List all resources as MCP resource descriptors.

        Returns:
            List of dicts with keys: uri, name, description, mimeType.
        """
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mimeType": r.mime_type,
            }
            for r in self._resources.values()
        ]

    def read(self, uri: str) -> Optional[MCPResourceContent]:
        """Read a resource's content.

        Args:
            uri: Resource URI to read.

        Returns:
            MCPResourceContent with the resource data, or None if not found.
        """
        resource = self._resources.get(uri)
        if resource is None:
            return None

        text = ""
        if resource.provider is not None:
            try:
                text = resource.provider()
                if not isinstance(text, str):
                    text = str(text)
            except Exception:
                text = ""

        return MCPResourceContent(
            uri=resource.uri,
            mime_type=resource.mime_type,
            text=text,
        )

    def read_many(self, uris: list[str]) -> list[MCPResourceContent]:
        """Read multiple resources.

        Args:
            uris: List of resource URIs to read.

        Returns:
            List of MCPResourceContent for found resources. Unknown URIs are
            silently skipped.
        """
        results = []
        for uri in uris:
            content = self.read(uri)
            if content is not None:
                results.append(content)
        return results

    def stats(self) -> dict:
        """Registry statistics.

        Returns:
            Dict with total count and category breakdown.
        """
        by_category: dict[str, int] = {}
        for resource in self._resources.values():
            by_category[resource.category] = by_category.get(resource.category, 0) + 1

        return {
            "total": len(self._resources),
            "by_category": by_category,
        }