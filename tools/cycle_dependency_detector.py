"""Cycle dependency detector foundation for AIOS clean-code audit.

Detects dependency cycles from a module graph representation.
"""

from collections import defaultdict


class CycleDependencyDetector:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_dependency(self, source: str, target: str):
        self.graph[source].append(target)

    def find_cycles(self):
        cycles = []
        visited = set()
        stack = []
        active = set()

        def visit(node):
            visited.add(node)
            active.add(node)
            stack.append(node)

            for dependency in self.graph[node]:
                if dependency not in visited:
                    visit(dependency)
                elif dependency in active:
                    index = stack.index(dependency)
                    cycles.append(stack[index:] + [dependency])

            stack.pop()
            active.remove(node)

        for node in list(self.graph):
            if node not in visited:
                visit(node)

        return cycles
