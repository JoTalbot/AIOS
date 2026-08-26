from .models import Decision, DecisionContext


class DecisionEngine:
    """Selects execution actions from runtime context."""

    def decide(self, context: DecisionContext) -> Decision:
        options = context.options

        if not options:
            return Decision(
                action="abort",
                confidence=0.9,
                explanation="No valid actions available",
            )

        if context.state.get("recovery_required"):
            return Decision(
                action="recover",
                confidence=0.85,
                explanation="Runtime reported recovery requirement",
                fallback="abort",
            )

        return Decision(
            action=options[0],
            confidence=0.6,
            explanation="Selected highest priority available action",
        )
