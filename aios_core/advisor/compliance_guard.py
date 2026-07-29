"""Compliance Guard — проверка черновиков на соответствие Конституции AIOS."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComplianceViolation:
    article: str
    message: str
    severity: str  # 'critical', 'warning'

class ComplianceGuard:
    def __init__(self):
        self.rules = {
            "article_23": {
                "keywords": ["гарантия", "100% оригинал", "точно работает"],
                "message": "Статья 23: Запрещены абсолютные гарантии без подтверждения",
                "severity": "critical"
            },
            "article_45": {
                "keywords": ["предоплата", "advance payment"],
                "message": "Статья 45: Требуется явное указание условий возврата предоплаты",
                "severity": "warning"
            }
        }

    def check(self, draft_text: str, context: dict) -> list[ComplianceViolation]:
        violations = []
        text_lower = draft_text.lower()
        
        for article, rule in self.rules.items():
            for keyword in rule["keywords"]:
                if keyword in text_lower:
                    violations.append(ComplianceViolation(
                        article=article,
                        message=rule["message"],
                        severity=rule["severity"]
                    ))
                    break
        
        return violations
