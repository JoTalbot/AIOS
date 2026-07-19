"""AIOS Reasoning Engine Layer v2.1.1

Builds explainable reasoning chains from rules, knowledge and constraints.
"""


class ReasoningEngine:
    """Builds explainable reasoning chains."""

    def __init__(self):
        self.traces = []

    def reason(self, decision: str, rules: list, sources: list) -> dict:
        """Build a reasoning trace.
        
        Args:
            decision: Decision to justify
            rules: Rules applied
            sources: Knowledge sources used
            
        Returns:
            Reasoning trace with explanation
        """
        trace = {
            "decision": decision,
            "rules_applied": rules,
            "knowledge_sources": sources,
            "confidence": self._calculate_confidence(rules, sources)
        }
        self.traces.append(trace)
        return trace

    def _calculate_confidence(self, rules: list, sources: list) -> float:
        """Calculate confidence in reasoning."""
        base_confidence = 0.5
        rule_boost = len(rules) * 0.1
        source_boost = len(sources) * 0.15
        return min(0.95, base_confidence + rule_boost + source_boost)

    def last_trace(self) -> dict:
        """Get last reasoning trace."""
        return self.traces[-1] if self.traces else None
