"""Kernel state validation before runtime startup."""


class KernelValidation:
    def validate(self, state, registry):
        errors = []

        if state is None:
            errors.append("missing kernel state")

        if registry is None:
            errors.append("missing kernel registry")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
