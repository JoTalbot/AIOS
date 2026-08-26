class DependencyGraph:
    def __init__(self):
        self.dependencies = {}

    def add(self, component, requires=None):
        self.dependencies[component] = requires or []

    def resolve(self):
        resolved = []
        visiting = set()

        def visit(name):
            if name in resolved:
                return
            if name in visiting:
                raise RuntimeError("Circular component dependency")

            visiting.add(name)
            for dependency in self.dependencies.get(name, []):
                visit(dependency)
            visiting.remove(name)
            resolved.append(name)

        for component in self.dependencies:
            visit(component)

        return resolved

    def startup_order(self):
        return self.resolve()

    def shutdown_order(self):
        return list(reversed(self.resolve()))
