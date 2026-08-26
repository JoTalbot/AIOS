"""Sandbox execution boundary for evolution changes."""


class SandboxRunner:
    def run(self, mutation):
        return {
            "mutation": mutation,
            "validated": False,
            "environment": "sandbox",
        }
