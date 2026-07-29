import random
from dataclasses import dataclass


@dataclass
class Arm:
    id: str
    impressions: int
    conversions: int

    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.impressions if self.impressions > 0 else 0.0


class ThompsonSamplingBandit:
    def __init__(self):
        self.arms: dict[str, Arm] = {}

    def add_arm(self, arm_id: str):
        if arm_id not in self.arms:
            self.arms[arm_id] = Arm(id=arm_id, impressions=0, conversions=0)

    def select_arm(self) -> str:
        if not self.arms:
            raise ValueError("No arms available")

        samples = {}
        for arm_id, arm in self.arms.items():
            alpha = arm.conversions + 1
            beta = arm.impressions - arm.conversions + 1
            samples[arm_id] = random.betavariate(alpha, beta)

        return max(samples, key=samples.get)

    def record_impression(self, arm_id: str):
        if arm_id in self.arms:
            self.arms[arm_id].impressions += 1

    def record_conversion(self, arm_id: str):
        if arm_id in self.arms:
            self.arms[arm_id].conversions += 1

    def get_stats(self) -> list[dict]:
        return [
            {
                "id": arm.id,
                "impressions": arm.impressions,
                "conversions": arm.conversions,
                "conversion_rate": round(arm.conversion_rate, 4),
            }
            for arm in self.arms.values()
        ]


bandit = ThompsonSamplingBandit()
