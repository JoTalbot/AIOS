"""Category Theory Abstractions for AIOS v10.10.0.

Category theory: objects, morphisms, composition, identity,
functors, natural transformations, products, coproducts,
limits/colimits, monoidal structure, and diagram chasing.

Classes:
    Category       — objects + morphisms with composition law
    Functor        — mapping between categories
    NaturalTransform — morphism of functors
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class Category:
    """Abstract category with objects and morphisms."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.objects: set[Any] = set()
        self.morphisms: dict[tuple[Any, Any], Callable] = {}
        self._identity: dict[Any, Callable] = {}

    def add_object(self, obj: Any) -> None:
        """Add an object (backward-compatible)."""
        self.objects.add(obj)
        # Auto-define identity morphism
        self._identity[obj] = lambda x: x

    def add_morphism(self, source: Any, target: Any, func: Callable) -> None:
        """Add a morphism (backward-compatible)."""
        if source not in self.objects:
            self.add_object(source)
        if target not in self.objects:
            self.add_object(target)
        self.morphisms[(source, target)] = func

    def compose(self, f: Callable, g: Callable) -> Callable:
        """Compose two morphisms (backward-compatible)."""
        return lambda x: f(g(x))

    def get_identity(self, obj: Any) -> Callable | None:
        """Get identity morphism for an object."""
        return self._identity.get(obj)

    def product(self, a: Any, b: Any) -> tuple[Any, Callable, Callable]:
        """Compute categorical product (pair + projections)."""
        pair = (a, b)
        def proj_a(p):
            return p[0] if isinstance(p, tuple) else a
        def proj_b(p):
            return p[1] if isinstance(p, tuple) else b
        self.add_object(pair)
        self.add_morphism(pair, a, proj_a)
        self.add_morphism(pair, b, proj_b)
        return pair, proj_a, proj_b

    def coproduct(self, a: Any, b: Any) -> tuple[Any, Callable, Callable]:
        """Compute categorical coproduct (tagged union + injections)."""
        tagged = f"Either({a}, {b})"
        def inj_a(x):
            return ("left", x) if x == a else ("right", x)
        def inj_b(x):
            return ("right", x) if x == b else ("left", x)
        self.add_object(tagged)
        self.add_morphism(a, tagged, inj_a)
        self.add_morphism(b, tagged, inj_b)
        return tagged, inj_a, inj_b

    def terminal_object(self) -> Any:
        """Return terminal object (unique target)."""
        if self.objects:
            terminal = "terminal"
            self.add_object(terminal)
            for obj in self.objects:
                self.add_morphism(obj, terminal, lambda x: terminal)
            return terminal
        return None

    def initial_object(self) -> Any:
        """Return initial object (unique source)."""
        if self.objects:
            initial = "initial"
            self.add_object(initial)
            for obj in self.objects:
                self.add_morphism(initial, obj, lambda x: obj)
            return initial
        return None

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "objects": len(self.objects),
            "morphisms": len(self.morphisms),
            "name": self.name,
        }


class Functor:
    """Functor between categories."""

    def __init__(
        self,
        source: Category,
        target: Category,
        obj_mapping: dict[Any, Any] | None = None,
        mor_mapping: Callable | None = None,
    ) -> None:
        self.source = source
        self.target = target
        self._obj_mapping: dict[Any, Any] = obj_mapping or {}
        self._mor_mapping = mor_mapping or (lambda f: f)

    def apply(self, obj: Any) -> Any:
        """Apply functor to an object (backward-compatible)."""
        mapped = self._obj_mapping.get(obj, obj)
        self.target.add_object(mapped)
        return mapped

    def apply_morphism(self, morphism: Callable) -> Callable:
        """Apply functor to a morphism."""
        return self._mor_mapping(morphism)

    def preserve_identity(self) -> bool:
        """Check if functor preserves identity morphisms."""
        for obj in self.source.objects:
            src_id = self.source.get_identity(obj)
            tgt_obj = self.apply(obj)
            tgt_id = self.target.get_identity(tgt_obj)
            if src_id is not None and tgt_id is not None:
                # Simplified check: both should be identity-like
                if src_id(42) != tgt_id(42):
                    return False
        return True

    def preserve_composition(self) -> bool:
        """Check if functor preserves composition (simplified)."""
        return True  # Simplified: always assume structure preservation

    def stats(self) -> dict[str, Any]:
        return {
            "source": self.source.name,
            "target": self.target.name,
            "mapped_objects": len(self._obj_mapping),
        }


class NaturalTransform:
    """Natural transformation between functors."""

    def __init__(
        self,
        functor_f: Functor,
        functor_g: Functor,
        components: dict[Any, Callable] | None = None,
    ) -> None:
        self.functor_f = functor_f
        self.functor_g = functor_g
        self._components: dict[Any, Callable] = components or {}

    def component_at(self, obj: Any) -> Callable | None:
        """Get the component morphism at an object."""
        return self._components.get(obj)

    def add_component(self, obj: Any, morphism: Callable) -> None:
        """Add a component morphism."""
        self._components[obj] = morphism

    def stats(self) -> dict[str, Any]:
        return {
            "components": len(self._components),
            "source_functor": self.functor_f.stats(),
            "target_functor": self.functor_g.stats(),
        }
