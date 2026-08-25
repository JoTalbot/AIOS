"""
Import Graph Scanner

Production cleanup utility for AIOS architecture audit.
Builds a lightweight dependency map from Python imports.
"""

from pathlib import Path
import ast
from dataclasses import dataclass, field


@dataclass
class ModuleNode:
    name: str
    imports: list[str] = field(default_factory=list)


class ImportGraphScanner:
    def __init__(self, root: str):
        self.root = Path(root)
        self.nodes: dict[str, ModuleNode] = {}

    def scan(self):
        for file in self.root.rglob("*.py"):
            module = self._module_name(file)
            self.nodes[module] = ModuleNode(
                name=module,
                imports=self._extract_imports(file),
            )
        return self.nodes

    def _extract_imports(self, file: Path):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        result = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                result.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                result.append(node.module)
        return sorted(set(result))

    def _module_name(self, file: Path):
        return ".".join(file.with_suffix("").parts)


if __name__ == "__main__":
    scanner = ImportGraphScanner(".")
    graph = scanner.scan()
    for name, node in graph.items():
        print(name, "->", node.imports)
