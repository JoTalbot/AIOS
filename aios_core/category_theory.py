"""Category Theory Abstractions for AIOS"""

from typing import Any, Callable, Dict


class Category:
    """Abstract category with objects and morphisms."""

    def __init__(self, name: str):
        self.name = name
        self.objects: set = set()
        self.morphisms: Dict = {}

    def add_object(self, obj: Any) -> None:
        """Execute add object."""
        self.objects.add(obj)

    def add_morphism(self, source: Any, target: Any, func: Callable) -> None:
        """Execute add morphism."""
        self.morphisms[(source, target)] = func

    def compose(self, f: Callable, g: Callable) -> Callable:
        """Execute compose."""
        return lambda x: f(g(x))

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"objects": len(self.objects), "morphisms": len(self.morphisms)}


class Functor:
    """Functor between categories."""

    def __init__(self, source: Category, target: Category, mapping: Callable):
        self.source = source
        self.target = target
        self.mapping = mapping

    def apply(self, obj: Any) -> Any:
        """Execute apply."""
        return self.mapping(obj)
