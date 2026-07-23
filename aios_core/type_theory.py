"""Type Theory for AIOS"""

from typing import Any, Callable, Dict, Type


class TypeSystem:
    """Dependent type system abstraction."""

    def __init__(self):
        self.types: Dict[str, Type] = {}
        self.terms: dict[str, Any] = {}

    def define_type(self, name: str, base_type: Type) -> None:
        """Execute define type."""
        self.types[name] = base_type

    def check_type(self, term: Any, expected: str) -> bool:
        """Execute check type."""
        return isinstance(term, self.types.get(expected, object))

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"types": len(self.types), "terms": len(self.terms)}


type_system = TypeSystem()
