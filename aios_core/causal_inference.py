"""Causal Inference Engine for AIOS v10.8.0.

Causal discovery and inference with DAG support,
do-calculus simulation, counterfactual reasoning,
confounder identification, mediation analysis,
intervention effects, and causal validation.

Classes:
    CausalLink     — directed causal relationship
    Intervention   — do-operation specification
    CausalInference — full causal reasoning engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CausalLink:
    """Directed causal relationship with strength."""
    cause: str
    effect: str
    strength: float = 1.0  # 0..1
    mechanism: str = "direct"  # direct, mediated, confounded
    validated: bool = False
    created_at: float = field(default_factory=time.time)


@dataclass
class Intervention:
    """Do-operation specification."""
    variable: str
    value: Any
    description: str = ""


class CausalInference:
    """Full causal reasoning engine.

    Features:
    - DAG-based causal graph construction
    - Do-calculus (intervention-based inference)
    - Counterfactual reasoning
    - Confounder identification
    - Mediation analysis
    - Effect estimation
    - Graph validation (acyclicity check)
    """

    def __init__(self) -> None:
        self.causal_graph: dict[str, list[CausalLink]] = {}  # cause → list of links
        self.nodes: set[str] = set()
        self.confounders: dict[str, list[str]] = {}  # effect → list of confounders
        self.interventions: list[Intervention] = []

    # ── Graph Construction ──────────────────────────────────────────

    def add_causal_link(self, cause: str, effect: str, strength: float = 1.0,
                        mechanism: str = "direct") -> CausalLink:
        """Add a directed causal link."""
        link = CausalLink(cause=cause, effect=effect, strength=strength, mechanism=mechanism)
        if cause not in self.causal_graph:
            self.causal_graph[cause] = []
        self.causal_graph[cause].append(link)
        self.nodes.add(cause)
        self.nodes.add(effect)
        return link

    def remove_causal_link(self, cause: str, effect: str) -> None:
        """Remove a causal link."""
        links = self.causal_graph.get(cause, [])
        self.causal_graph[cause] = [l for l in links if l.effect != effect]

    def add_confounder(self, confounder: str, variables: list[str]) -> None:
        """Register a confounding variable."""
        for var in variables:
            if var not in self.confounders:
                self.confounders[var] = []
            self.confounders[var].append(confounder)

    def get_causes(self, effect: str) -> list[str]:
        """Return all causes of an effect."""
        causes = []
        for cause, links in self.causal_graph.items():
            for link in links:
                if link.effect == effect:
                    causes.append(cause)
        return causes

    def get_effects(self, cause: str) -> list[str]:
        """Return all effects of a cause."""
        links = self.causal_graph.get(cause, [])
        return [link.effect for link in links]

    def get_links(self) -> list[CausalLink]:
        """Return all causal links."""
        all_links = []
        for links in self.causal_graph.values():
            all_links.extend(links)
        return all_links

    # ── Do-Calculus (Intervention) ──────────────────────────────────

    def add_causal_link_old(self, cause: str, effect: str) -> None:
        """Backward-compatible add_causal_link."""
        self.add_causal_link(cause, effect)

    def infer(self, intervention: dict) -> dict:
        """Simple do-calculus simulation (backward-compatible).

        For each intervened variable, trace causal effects downstream.
        """
        effects = {}
        for cause, value in intervention.items():
            downstream = self.get_effects(cause)
            for effect_name in downstream:
                links = self.causal_graph.get(cause, [])
                strength = 0.0
                for link in links:
                    if link.effect == effect_name:
                        strength = max(strength, link.strength)
                effects[effect_name] = {
                    "changed_by": value,
                    "strength": strength,
                    "mechanism": "intervention",
                }
        return effects

    def do_intervention(self, variable: str, value: Any) -> dict[str, Any]:
        """Compute effects of a do-intervention (set variable=value)."""
        intervention = Intervention(variable=variable, value=value)
        self.interventions.append(intervention)

        # Trace downstream effects
        direct_effects = self.get_effects(variable)
        total_effects = {}

        for effect_name in direct_effects:
            links = [l for l in self.causal_graph[variable] if l.effect == effect_name]
            avg_strength = sum(l.strength for l in links) / len(links) if links else 1.0
            total_effects[effect_name] = {
                "value": f"changed_by_{value}",
                "strength": round(avg_strength, 4),
                "path": "direct",
            }
            # Second-order effects
            second_order = self.get_effects(effect_name)
            for so_effect in second_order:
                if so_effect not in total_effects:
                    total_effects[so_effect] = {
                        "value": f"indirectly_changed_by_{value}",
                        "strength": round(avg_strength * 0.5, 4),
                        "path": f"via_{effect_name}",
                    }

        return total_effects

    # ── Counterfactual ──────────────────────────────────────────────

    def counterfactual(self, observed: dict, hypothetical: dict) -> dict[str, Any]:
        """Compute counterfactual: what would happen if hypothetical were true."""
        # Base: compute observed effects
        observed_effects = self.infer(observed)
        # Counterfactual: compute hypothetical effects
        counterfactual_effects = self.infer(hypothetical)

        differences = {}
        for key in counterfactual_effects:
            observed_val = observed_effects.get(key, {})
            counterfactual_val = counterfactual_effects.get(key, {})
            if observed_val != counterfactual_val:
                differences[key] = {
                    "observed": observed_val,
                    "counterfactual": counterfactual_val,
                }

        return {
            "differences": differences,
            "observed_keys": list(observed_effects.keys()),
            "counterfactual_keys": list(counterfactual_effects.keys()),
        }

    # ── Mediation Analysis ──────────────────────────────────────────

    def mediating_effect(self, cause: str, mediator: str, effect: str) -> dict[str, Any]:
        """Compute indirect (mediated) and direct effects."""
        # Total effect
        total_links = [l for l in self.causal_graph.get(cause, []) if l.effect == effect]
        total_strength = sum(l.strength for l in total_links) / len(total_links) if total_links else 0.0

        # Indirect effect (cause → mediator → effect)
        cause_to_med = [l for l in self.causal_graph.get(cause, []) if l.effect == mediator]
        med_to_eff = [l for l in self.causal_graph.get(mediator, []) if l.effect == effect]

        if cause_to_med and med_to_eff:
            indirect = (sum(l.strength for l in cause_to_med) / len(cause_to_med)) * \
                       (sum(l.strength for l in med_to_eff) / len(med_to_eff))
            direct = total_strength - indirect
            return {
                "total": round(total_strength, 4),
                "direct": round(direct, 4),
                "indirect": round(indirect, 4),
                "mediated_proportion": round(indirect / total_strength if total_strength > 0 else 0, 4),
            }

        return {"total": round(total_strength, 4), "direct": round(total_strength, 4), "indirect": 0.0}

    # ── Validation ──────────────────────────────────────────────────

    def is_acyclic(self) -> bool:
        """Check if the causal graph is acyclic (valid DAG)."""
        visited = set()
        in_progress = set()

        def dfs(node: str) -> bool:
            if node in in_progress:
                return False  # cycle detected
            if node in visited:
                return True
            in_progress.add(node)
            for effect in self.get_effects(node):
                if not dfs(effect):
                    return False
            in_progress.remove(node)
            visited.add(node)
            return True

        for node in self.nodes:
            if node not in visited:
                if not dfs(node):
                    return False
        return True

    def validate(self) -> dict[str, Any]:
        """Validate the causal graph."""
        return {
            "acyclic": self.is_acyclic(),
            "nodes": len(self.nodes),
            "links": len(self.get_links()),
            "confounders_registered": sum(len(v) for v in self.confounders.values()),
        }

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        links = self.get_links()
        avg_strength = sum(l.strength for l in links) / len(links) if links else 0.0
        return {
            "causal_links": len(links),
            "nodes": len(self.nodes),
            "avg_link_strength": round(avg_strength, 4),
            "acyclic": self.is_acyclic(),
            "confounders": sum(len(v) for v in self.confounders.values()),
        }
