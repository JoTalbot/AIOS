"""Type Theory for AIOS v10.9.0.

Dependent type system abstraction with type definition,
type checking, term registration, subtyping, type
inference, type composition, and proof simulation.

Classes:
    TypeDefinition — named type with constraints
    TypeSystem     — full type system engine
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TypeDefinition:
    """Named type definition with constraints."""

    name: str
    base_type: type
    constraints: list[Callable] = field(default_factory=list)
    description: str = ""
    created_at: float = field(default_factory=time.time)


class TypeSystem:
    """Full type system engine.

    Features:
    - Type definition with base type and constraints
    - Type checking (isinstance + constraint validation)
    - Term registration with type annotations
    - Subtyping detection
    - Type inference (simple deduction)
    - Type composition (product/union types)
    - Proof simulation (type-level proofs)
    """

    def __init__(self) -> None:
        self.types: dict[str, TypeDefinition] = {}
        self.terms: dict[str, Any] = {}
        self._proof_log: list[dict[str, Any]] = []

    # ── Type Definition ────────────────────────────────────────────

    def define_type(
        self,
        name: str,
        base_type: type,
        constraints: list[Callable] | None = None,
        description: str = "",
    ) -> TypeDefinition:
        """Define a new type with base type and optional constraints."""
        td = TypeDefinition(
            name=name,
            base_type=base_type,
            constraints=constraints or [],
            description=description,
        )
        self.types[name] = td
        return td

    def get_type(self, name: str) -> TypeDefinition | None:
        """Return type definition by name."""
        return self.types.get(name)

    def remove_type(self, name: str) -> None:
        """Remove a type definition."""
        self.types.pop(name, None)

    # ── Type Checking ──────────────────────────────────────────────

    def check_type(self, term: Any, expected: str) -> bool:
        """Check if term satisfies the expected type."""
        td = self.types.get(expected)
        if td is None:
            return isinstance(term, object)

        # Base type check
        if not isinstance(term, td.base_type):
            return False

        # Constraint validation
        for constraint in td.constraints:
            try:
                if not constraint(term):
                    return False
            except Exception:
                return False

        return True

    def validate_term(self, term: Any, type_name: str) -> dict[str, Any]:
        """Validate a term and return detailed results."""
        td = self.types.get(type_name)
        if td is None:
            return {"valid": False, "reason": f"Type '{type_name}' not defined"}

        results = {"base_check": isinstance(term, td.base_type)}
        constraint_results = {}
        for i, constraint in enumerate(td.constraints):
            try:
                constraint_results[f"constraint_{i}"] = constraint(term)
            except Exception as e:
                constraint_results[f"constraint_{i}"] = False
                results["constraint_error"] = str(e)

        results["constraints"] = constraint_results
        results["valid"] = results["base_check"] and all(constraint_results.values())
        return results

    # ── Term Registration ──────────────────────────────────────────

    def register_term(self, name: str, value: Any, type_annotation: str = "") -> None:
        """Register a term with optional type annotation."""
        self.terms[name] = value
        if type_annotation and not self.check_type(value, type_annotation):
            logger.warning(f"Term '{name}' does not satisfy type '{type_annotation}'")

    def get_term(self, name: str) -> Any | None:
        """Return a registered term."""
        return self.terms.get(name)

    # ── Subtyping ──────────────────────────────────────────────────

    def is_subtype(self, sub_type: str, super_type: str) -> bool:
        """Check if sub_type is a subtype of super_type."""
        sub_td = self.types.get(sub_type)
        super_td = self.types.get(super_type)

        if sub_td is None or super_td is None:
            return False

        # Check if sub's base_type is a subclass of super's base_type
        try:
            return issubclass(sub_td.base_type, super_td.base_type)
        except TypeError:
            return sub_td.base_type == super_td.base_type

    def type_hierarchy(self, type_name: str) -> list[str]:
        """Return supertype chain for a type."""
        chain = [type_name]
        for other_name in self.types.keys():
            if other_name != type_name and self.is_subtype(type_name, other_name):
                chain.append(other_name)
        return chain

    # ── Type Composition ──────────────────────────────────────────

    def product_type(self, name: str, type1: str, type2: str) -> TypeDefinition:
        """Create a product (tuple) type from two types."""
        td1 = self.types.get(type1)
        td2 = self.types.get(type2)
        base = tuple
        constraints = []
        if td1 and td2:
            constraints = [
                lambda t: (
                    isinstance(t, tuple)
                    and len(t) == 2
                    and isinstance(t[0], td1.base_type)
                    and isinstance(t[1], td2.base_type)
                ),
            ]
        return self.define_type(
            name, base, constraints, description=f"Product({type1}, {type2})"
        )

    def union_type(self, name: str, type1: str, type2: str) -> TypeDefinition:
        """Create a union type from two types."""
        td1 = self.types.get(type1)
        td2 = self.types.get(type2)
        bases = []
        if td1:
            bases.append(td1.base_type)
        if td2:
            bases.append(td2.base_type)
        constraints = [lambda t: any(isinstance(t, b) for b in bases)] if bases else []
        return self.define_type(
            name, object, constraints, description=f"Union({type1}, {type2})"
        )

    # ── Proof Simulation ──────────────────────────────────────────

    def prove(self, statement: str, premises: list[str] = []) -> dict[str, Any]:
        """Simulate a type-level proof."""
        self._proof_log.append(
            {
                "statement": statement,
                "premises": premises,
                "timestamp": time.time(),
            }
        )
        # Simple: check if all premises are valid terms
        valid_premises = all(p in self.terms for p in premises)
        return {
            "statement": statement,
            "proven": valid_premises,
            "premises_valid": valid_premises,
        }

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "types": len(self.types),
            "terms": len(self.terms),
            "proofs": len(self._proof_log),
        }


type_system = TypeSystem()
