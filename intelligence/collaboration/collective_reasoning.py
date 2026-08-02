class CollectiveReasoning:
    """Shared reasoning between agents foundation."""

    def combine(self, opinions):
        return {
            "opinions": opinions,
            "consensus": None
        }
