"""AIOS Policy Loader.

Loads all YAML policy definitions from the ``policies/`` directory into a single
registry keyed by policy name. Used by the constitution and approval engines so
that behavioural rules live in ``policies/`` rather than being hard-coded.
"""

import os
import glob

try:
    import yaml
except ImportError:  # pragma: no cover - yaml optional at import time
    yaml = None


class PolicyLoader:
    """Loads and exposes AIOS policy definitions."""

    def __init__(self, policy_dir: str = None):
        if policy_dir is None:
            policy_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "policies"
            )
        self.policy_dir = policy_dir
        self.policies = {}
        self.load()

    def load(self):
        """(Re)load every ``*.yaml`` policy from the policy directory."""
        self.policies = {}
        if yaml is None:
            return
        for path in sorted(glob.glob(os.path.join(self.policy_dir, "*.yaml"))):
            name = os.path.splitext(os.path.basename(path))[0]
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh) or {}
            except (OSError, yaml.YAMLError):
                continue
            # Store the top-level mapping, preferring the inner keyed block.
            self.policies[name] = data

    def get(self, name: str, default=None):
        return self.policies.get(name, default)

    def __getitem__(self, name: str):
        return self.policies[name]

    def __contains__(self, name: str) -> bool:
        return name in self.policies

    def keys(self):
        return self.policies.keys()

    # --- Convenience accessors used by the engines -------------------------

    @property
    def safety_threat_levels(self) -> dict:
        """Return the ``threat_levels`` map from ``security_policy``."""
        sec = self.policies.get("security_policy", {})
        sec = sec.get("security_policy", sec)
        return sec.get("threat_levels", {}) or {}

    @property
    def approval_required_scopes(self) -> list:
        """Scopes that always require human approval (from ``governance_policy``)."""
        gov = self.policies.get("governance_policy", {})
        gov = gov.get("governance", gov)
        required = []
        if gov.get("human_oversight"):
            required.append("global")
            required.append("constitution")
        return required
