"""GraphQL Support for AIOS v10.7.0.

GraphQL-like query executor with schema definition, field resolvers,
nested queries, type system, query parsing, mutation support,
and introspection.

Classes:
    GraphQLField   — field definition with resolver and args
    GraphQLType    — type definition with fields
    GraphQLSchema  — full schema with query execution and introspection
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GraphQLField:
    """Field definition with resolver and arguments."""

    name: str
    resolver: Callable
    type: str = "String"
    args: dict[str, str] = field(default_factory=dict)  # arg_name → arg_type
    description: str = ""


@dataclass
class GraphQLType:
    """Type definition with fields."""

    name: str
    fields: dict[str, GraphQLField] = field(default_factory=dict)

    def add_field(self, field_def: GraphQLField) -> None:
        """Add a field to the type."""
        self.fields[field_def.name] = field_def


class GraphQLSchema:
    """Full GraphQL schema with query execution and introspection.

    Features:
    - Field registration with resolvers
    - Nested query execution
    - Argument support
    - Mutation support
    - Type system
    - Introspection (__schema query)
    - Error handling
    """

    def __init__(self) -> None:
        self.resolvers: dict[str, Callable] = {}
        self.types: dict[str, GraphQLType] = {}
        self.mutations: dict[str, Callable] = {}
        self._query_count: int = 0

    # ── Field Registration ────────────────────────────────────────

    def register(self, field_name: str, resolver: Callable) -> None:
        """Register a field resolver (backward-compatible)."""
        self.resolvers[field_name] = resolver

    def register_type(self, type_def: GraphQLType) -> None:
        """Register a type definition."""
        self.types[type_def.name] = type_def
        # Also register all field resolvers
        for fld in type_def.fields.values():
            self.resolvers[fld.name] = fld.resolver

    def register_mutation(self, name: str, resolver: Callable) -> None:
        """Register a mutation resolver."""
        self.mutations[name] = resolver

    # ── Query Execution ──────────────────────────────────────────

    def execute(
        self, query: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GraphQL-like query string.

        Parses field names from the query and resolves them.
        Supports nested fields and arguments.
        """
        self._query_count += 1
        context = context or {}
        errors: list[str] = []

        # Parse query fields
        fields = self._parse_fields(query)
        if not fields:
            # Try simple keyword matching (backward-compatible)
            for key in self.resolvers:
                if key in query:
                    fields = [key]
                    break

        if not fields:
            return {"data": {}, "errors": ["No valid fields in query"]}

        data: dict[str, Any] = {}
        for field_name in fields:
            resolver = self.resolvers.get(field_name)
            if resolver is None:
                errors.append(f"Field '{field_name}' not found")
                continue

            try:
                # Extract arguments from query
                args = self._parse_args(query, field_name)
                if args:
                    result = resolver(context=context, **args)
                else:
                    result = resolver(context=context)
                data[field_name] = result
            except Exception as e:
                errors.append(f"Error resolving '{field_name}': {e!s}")

        result: dict[str, Any] = {"data": data}
        if errors:
            result["errors"] = errors
        return result

    def execute_mutation(
        self, mutation: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a mutation."""
        context = context or {}
        # Parse mutation name
        name = self._parse_mutation_name(mutation)
        if name and name in self.mutations:
            try:
                result = self.mutations[name](context=context)
                return {"data": {name: result}}
            except Exception as e:
                return {"data": {}, "errors": [str(e)]}
        return {"data": {}, "errors": ["Unknown mutation"]}

    # ── Introspection ────────────────────────────────────────────

    def introspect(self) -> dict[str, Any]:
        """Return schema introspection (like __schema)."""
        return {
            "types": [
                {
                    "name": t.name,
                    "fields": [
                        {
                            "name": f.name,
                            "type": f.type,
                            "args": f.args,
                            "description": f.description,
                        }
                        for f in t.fields.values()
                    ],
                }
                for t in self.types.values()
            ],
            "query_fields": list(self.resolvers.keys()),
            "mutations": list(self.mutations.keys()),
        }

    # ── Parsing ──────────────────────────────────────────────────

    def _parse_fields(self, query: str) -> list[str]:
        """Extract field names from GraphQL query."""
        # Extract word tokens from original query (not cleaned/removed)
        # This correctly handles single-field and multi-field queries like
        # { stats }, { stats health }, { name }
        tokens = re.findall(r"\b([a-zA-Z_]\w*)\b", query)
        # Remove GraphQL keywords
        keywords = {"query", "mutation", "fragment", "on", "subscription"}
        return [t for t in tokens if t not in keywords and t in self.resolvers]

    def _parse_args(self, query: str, field_name: str) -> dict[str, Any]:
        """Extract arguments from query for a field."""
        # Match (key: value) patterns near field_name
        pattern = rf"{field_name}\s*\(([^)]+)\)"
        match = re.search(pattern, query)
        if not match:
            return {}
        args_str = match.group(1)
        args: dict[str, Any] = {}
        for pair in args_str.split(","):
            parts = pair.strip().split(":")
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip().strip('"').strip("'")
                # Try to parse as number
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                args[key] = value
        return args

    def _parse_mutation_name(self, mutation: str) -> str | None:
        """Extract mutation name."""
        pattern = r"mutation\s+(\w+)"
        match = re.search(pattern, mutation)
        if match:
            return match.group(1)
        # Fallback: first word after mutation
        for name in self.mutations:
            if name in mutation:
                return name
        return None

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "fields": len(self.resolvers),
            "types": len(self.types),
            "mutations": len(self.mutations),
            "queries_executed": self._query_count,
        }


graphql = GraphQLSchema()
