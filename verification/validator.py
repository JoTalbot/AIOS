from dataclasses import dataclass


@dataclass
class ValidationResult:
    valid: bool
    details: dict


class RuntimeValidator:

    def validate(self, state):
        return ValidationResult(
            valid=state.get("healthy", False),
            details=state
        )
