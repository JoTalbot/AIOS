"""AIOS Policy Loader v3.0.0

Loads YAML policy files, validates their schema, and provides
structured access to policy rules and threat-level escalation actions.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


class PolicyValidationError(Exception):
    """Raised when a policy file fails schema validation."""

    def __init__(self, policy_name: str, message: str):
        """Initialize PolicyValidationError."""
        self.policy_name = policy_name
        self.message = message
        super().__init__(f"Policy '{policy_name}' validation error: {message}")


@dataclass
class ThreatLevelConfig:
    """Configuration for a single threat level."""

    name: str
    action: str
    escalation: str
    raw: dict = field(default_factory=dict)


@dataclass
class PolicyRule:
    """A named boolean policy rule."""

    name: str
    enabled: bool


@dataclass
class PolicyRequirement:
    """A named policy requirement with a value."""

    name: str
    value: Any


@dataclass
class Policy:
    """A loaded and validated policy."""

    name: str
    version: str
    requirements: list[PolicyRequirement] = field(default_factory=list)
    rules: list[PolicyRule] = field(default_factory=list)
    threat_levels: dict[str, ThreatLevelConfig] = field(default_factory=dict)
    extra_sections: dict[str, Any] = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


# Expected top-level keys for each policy type
_POLICY_SCHEMAS = {
    "security_policy": {
        "required_keys": ["requirements", "rules", "threat_levels"],
        "optional_keys": ["version"],
    },
    "federation_policy": {
        "required_keys": ["requirements", "rules"],
        "optional_keys": [
            "version",
            "sync_frequency",
            "local_autonomy",
            "offline_operation",
        ],
    },
    "evolution_policy": {
        "required_keys": ["requirements", "stages", "restrictions"],
        "optional_keys": ["version", "rollback"],
    },
}


def _validate_policy_structure(name: str, data: dict) -> list[str]:
    """Validate policy data against expected schema. Returns list of errors."""
    errors = []
    schema = _POLICY_SCHEMAS.get(name)
    if schema is None:
        # Unknown policy type — accept with warning
        return errors

    for key in schema["required_keys"]:
        if key not in data:
            errors.append(f"Missing required key: '{key}'")

    if "requirements" in data and not isinstance(data["requirements"], dict):
        errors.append("'requirements' must be a mapping")

    if "rules" in data and not isinstance(data["rules"], dict):
        errors.append("'rules' must be a mapping")

    if "threat_levels" in data and not isinstance(data["threat_levels"], dict):
        errors.append("'threat_levels' must be a mapping")

    if "stages" in data and not isinstance(data["stages"], list):
        errors.append("'stages' must be a list")

    if "restrictions" in data and not isinstance(data["restrictions"], dict):
        errors.append("'restrictions' must be a mapping")

    return errors


def _parse_threat_levels(data: dict) -> dict[str, ThreatLevelConfig]:
    """Parse threat_levels section into structured configs."""
    levels = {}
    if "threat_levels" not in data:
        return levels

    for level_name, config in data["threat_levels"].items():
        if not isinstance(config, dict):
            continue
        levels[level_name] = ThreatLevelConfig(
            name=level_name,
            action=config.get("action", "standard_operation"),
            escalation=config.get("escalation", "background_monitoring"),
            raw=config,
        )
    return levels


def _parse_requirements(data: dict) -> list[PolicyRequirement]:
    """Parse requirements section."""
    reqs = []
    if "requirements" not in data:
        return reqs

    for name, value in data["requirements"].items():
        reqs.append(PolicyRequirement(name=name, value=value))
    return reqs


def _parse_rules(data: dict) -> list[PolicyRule]:
    """Parse rules section."""
    rules = []
    if "rules" not in data:
        return rules

    for name, value in data["rules"].items():
        if isinstance(value, bool):
            rules.append(PolicyRule(name=name, enabled=value))
        else:
            rules.append(PolicyRule(name=name, enabled=bool(value)))
    return rules


def _parse_evolution_stages(data: dict) -> list[str]:
    """Parse evolution stages."""
    stages = data.get("stages", [])
    if isinstance(stages, list):
        return [str(s) for s in stages]
    return []


def _parse_evolution_restrictions(data: dict) -> dict[str, str]:
    """Parse evolution restrictions."""
    restrictions = data.get("restrictions", {})
    if isinstance(restrictions, dict):
        return {k: str(v) for k, v in restrictions.items()}
    return {}


def _parse_rollback(data: dict) -> dict:
    """Parse rollback configuration."""
    return data.get("rollback", {})


class PolicyLoader:
    """Loads, validates, and provides access to AIOS YAML policies.

    Supports security, federation, and evolution policies.
    """

    def __init__(self, policies_dir: str | None = None):
        """Initialize loader.

        Args:
            policies_dir: Path to directory containing YAML policy files.
                         If None, uses default path relative to this module.
        """
        if policies_dir is None:
            this_dir = Path(__file__).resolve().parent.parent
            policies_dir = str(this_dir / "policies")

        self.policies_dir = policies_dir
        self.policies: dict[str, Policy] = {}
        self._load_all()

    def _load_all(self):
        """Load and validate all YAML policy files."""
        if not os.path.isdir(self.policies_dir):
            raise FileNotFoundError(f"Policies directory not found: {self.policies_dir}")

        for filename in os.listdir(self.policies_dir):
            if not filename.endswith((".yaml", ".yml")):
                continue

            filepath = os.path.join(self.policies_dir, filename)
            self._load_policy(filepath)

    def _load_policy(self, filepath: str):
        """Load and validate a single policy file."""
        policy_name = Path(filepath).stem  # e.g. "security_policy"

        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise PolicyValidationError(
                policy_name, "Policy file does not contain a valid YAML mapping"
            )

        version = str(data.get("version", "unknown"))

        # Flatten: if the file has a top-level key matching the filename,
        # merge it into the top level for uniform access
        policy_data = data.get(policy_name)
        if isinstance(policy_data, dict):
            data = {**data, **policy_data}

        errors = _validate_policy_structure(policy_name, data)
        if errors:
            raise PolicyValidationError(policy_name, "; ".join(errors))

        # Parse structured components
        requirements = _parse_requirements(data)
        rules = _parse_rules(data)
        threat_levels = _parse_threat_levels(data)

        # Collect extra sections not covered by standard parsing
        known_keys = {
            "version",
            "requirements",
            "rules",
            "threat_levels",
            "stages",
            "restrictions",
            "rollback",
        }
        # Also exclude the policy name key
        known_keys.add(policy_name)
        extra = {k: v for k, v in data.items() if k not in known_keys}

        policy = Policy(
            name=policy_name,
            version=version,
            requirements=requirements,
            rules=rules,
            threat_levels=threat_levels,
            extra_sections=extra,
            raw=data,
        )

        # Parse evolution-specific fields
        if policy_name == "evolution_policy":
            policy.extra_sections["stages"] = _parse_evolution_stages(data)
            policy.extra_sections["restrictions"] = _parse_evolution_restrictions(data)
            policy.extra_sections["rollback"] = _parse_rollback(data)

        # Parse federation-specific fields
        if policy_name == "federation_policy":
            policy.extra_sections["sync_frequency"] = data.get("sync_frequency", {})
            policy.extra_sections["local_autonomy"] = data.get("local_autonomy", False)
            policy.extra_sections["offline_operation"] = data.get("offline_operation", False)

        self.policies[policy_name] = policy

    # --- Query API ---

    def get_policy(self, name: str) -> Optional[Policy]:
        """Get a loaded policy by name."""
        return self.policies.get(name)

    def get_security_policy(self) -> Optional[Policy]:
        """Get the security policy."""
        return self.get_policy("security_policy")

    def get_federation_policy(self) -> Optional[Policy]:
        """Get the federation policy."""
        return self.get_policy("federation_policy")

    def get_evolution_policy(self) -> Optional[Policy]:
        """Get the evolution policy."""
        return self.get_policy("evolution_policy")

    def get_threat_action(self, threat_level: str) -> str | None:
        """Get the action for a given threat level from security policy."""
        sec = self.get_security_policy()
        if sec and threat_level in sec.threat_levels:
            return sec.threat_levels[threat_level].action
        return None

    def get_threat_escalation(self, threat_level: str) -> str | None:
        """Get the escalation for a given threat level from security policy."""
        sec = self.get_security_policy()
        if sec and threat_level in sec.threat_levels:
            return sec.threat_levels[threat_level].escalation
        return None

    def is_rule_enabled(self, policy_name: str, rule_name: str) -> bool:
        """Check if a specific rule is enabled in a policy."""
        policy = self.get_policy(policy_name)
        if policy is None:
            return False
        for rule in policy.rules:
            if rule.name == rule_name:
                return rule.enabled
        return False

    def is_requirement_met(self, policy_name: str, req_name: str) -> bool | None:
        """Check if a requirement is set in a policy. Returns None if not found."""
        policy = self.get_policy(policy_name)
        if policy is None:
            return None
        for req in policy.requirements:
            if req.name == req_name:
                return bool(req.value)
        return None

    def get_evolution_stages(self) -> list[str]:
        """Get the evolution pipeline stages."""
        evo = self.get_evolution_policy()
        if evo:
            return evo.extra_sections.get("stages", [])
        return []

    def get_evolution_restrictions(self) -> dict[str, str]:
        """Get evolution restrictions."""
        evo = self.get_evolution_policy()
        if evo:
            return evo.extra_sections.get("restrictions", {})
        return {}

    def list_policies(self) -> list[str]:
        """List all loaded policy names."""
        return list(self.policies.keys())

    def stats(self) -> dict:
        """Return statistics about loaded policies."""
        result = {
            "total_policies": len(self.policies),
            "policies": {},
        }
        for name, policy in self.policies.items():
            result["policies"][name] = {
                "version": policy.version,
                "requirements_count": len(policy.requirements),
                "rules_count": len(policy.rules),
                "threat_levels_count": len(policy.threat_levels),
            }
        return result
