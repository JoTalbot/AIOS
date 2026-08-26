from dataclasses import dataclass


@dataclass
class UpdatePlan:

    version: str
    changes: list


class SelfUpdateEngine:

    def create_plan(self, version, changes):
        return UpdatePlan(
            version=version,
            changes=changes
        )

    def validate(self, plan):
        return bool(plan.version and plan.changes)
