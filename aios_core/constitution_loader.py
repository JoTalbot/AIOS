"""AIOS Constitution Loader v3.0.0

Loads and parses constitutional articles from markdown files into structured rules.
Extracts MUST / MUST NOT / MAY / SHOULD directives and binds them to articles.
"""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

__all__ = ["Article", "ConstitutionLoader", "ConstitutionalRule", "ObligationLevel"]


class ObligationLevel(Enum):
    """Constitutional obligation levels extracted from directive keywords."""

    MUST = "must"
    MUST_NOT = "must_not"
    MAY = "may"
    SHOULD = "should"
    SHOULD_NOT = "should_not"
    UNKNOWN = "unknown"


@dataclass
class ConstitutionalRule:
    """A single extracted constitutional rule."""

    article_id: str
    article_title: str
    section_number: int
    section_title: str
    obligation: ObligationLevel
    text: str
    status: str  # e.g. "Immutable Core Law"
    scope: str  # e.g. "All AIOS components"
    raw_line: str


@dataclass
class Article:
    """A parsed constitutional article."""

    article_id: str
    title: str
    status: str
    level: str
    scope: str
    sections: list[dict] = field(default_factory=list)
    rules: list[ConstitutionalRule] = field(default_factory=list)
    raw_content: str = ""


# Patterns for extracting structured metadata from article headers
_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(.+)", re.IGNORECASE)
_LEVEL_RE = re.compile(r"\*\*Level:\*\*\s*(.+)", re.IGNORECASE)
_SCOPE_RE = re.compile(r"\*\*Scope:\*\*\s*(.+)", re.IGNORECASE)

# Patterns for extracting keywords from rule text
_KEYWORD_PATTERN = re.compile(r"\b[A-Z][A-Za-z]{3,}\b", re.IGNORECASE)


class ConstitutionLoader:
    def __init__(self, constitution_dir: str):
        self.constitution_dir = constitution_dir
        self.articles = {}
        self.rules = []

    def load_constitution(self):
        for root, dirs, files in os.walk(self.constitution_dir):
            for file in files:
                if file.endswith(".md"):
                    article_path = os.path.join(root, file)
                    with open(article_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        self.parse_article(content, article_path)

    def parse_article(self, content: str, article_path: str):
        title_match = re.search(r"## (.+)", content)
        if title_match:
            title = title_match.group(1).strip("# ")
        else:
            title = "Untitled"

        level_match = re.search(r"\*\*Level:\*\*\s*(.+)", content)
        scope_match = re.search(r"\*\*Scope:\*\*\s*(.+)", content)

        article_id = f"ARTICLE-{title.lower().replace(' ', '-')}"
        article = Article(
            article_id=article_id,
            title=title,
            status="Draft",
            level=level_match.group(1) if level_match else "Unknown",
            scope=scope_match.group(1) if scope_match else "Unknown",
        )

        self.articles[article_id] = article

        for line in content.split("\n"):
            if line.startswith("##"):
                continue
            match = re.search(r"### (.+)", line)
            if match:
                section_title = match.group(1).strip("# ")
                section_number = len(article.sections) + 1
                article.sections.append({"title": section_title, "number": section_number})
                continue

            match = self._extract_keywords(line)
            if match:
                for keyword in match:
                    rule_text = line.strip(keyword)
                    rule = ConstitutionalRule(
                        article_id=article_id,
                        article_title=title,
                        section_number=len(article.sections),
                        section_title=section_title,
                        obligation="UNKNOWN",
                        text=rule_text,
                        status="Draft",
                        scope="Unknown",
                        raw_line=line,
                    )
                    self.rules.append(rule)
                    article.rules.append(rule)

    def _extract_keywords(self, line: str) -> list[str]:
        return [kw for kw in self._keyword_pattern.findall(line) if len(kw) > 3]

    # --- Query API ---

    def get_article(self, article_id: str) -> Article | None:
        return self.articles.get(article_id)

    def get_rules(self, obligation: ObligationLevel | None = None) -> list[ConstitutionalRule]:
        if obligation is None:
            return list(self.rules)
        return [rule for rule in self._rules_by_obligation.get(obligation, [])]

    def get_must_rules(self) -> list[ConstitutionalRule]:
        return self.get_rules(ObligationLevel.MUST)

    def get_must_not_rules(self) -> list[ConstitutionalRule]:
        return self.get_rules(ObligationLevel.MUST_NOT)

    def get_may_rules(self) -> list[ConstitutionalRule]:
        return self.get_rules(ObligationLevel.MAY)

    def get_should_rules(self) -> list[ConstitutionalRule]:
        return self.get_rules(ObligationLevel.SHOULD)

    def search_rules(self, keyword: str) -> list[ConstitutionalRule]:
        keyword_upper = keyword.upper()
        results = [rule for rule in self.rules if keyword_upper in rule.text.upper()]
        return results

    def rules_for_topic(self, topic: str) -> list[ConstitutionalRule]:
        results = []
        seen = set()
        # Direct keyword match
        for rule in self._rules_by_keyword.get(topic, []):
            if id(rule) not in seen:
                results.append(rule)
                seen.add(id(rule))
        # Case-insensitive search in text
        topic_lower = topic.lower()
        for rule in self.rules:
            if id(rule) not in seen and topic_lower in rule.text.lower():
                results.append(rule)
                seen.add(id(rule))
        return results

    # Words too generic to use as relevance signals
    _NOISE_WORDS = frozenset(
        {
            "system",
            "should",
            "cannot",
            "without",
            "through",
            "however",
            "operation",
            "every",
            "component",
            "process",
            "mechanism",
            "structure",
            "capability",
            "function",
            "result",
            "require",
            "provide",
            "maintain",
            "support",
            "preserve",
            "ensure",
            "allow",
            "enable",
            "control",
            "protect",
            "record",
            "produce",
            "verify",
            "receive",
            "external",
            "internal",
            "sufficient",
            "available",
        }
    )

    def _is_relevant(self, action_text: str, rule_text: str) -> bool:
        """Check if an action is relevant to a rule using multi-word heuristic.

        Requires at least 2 non-noise words (len > 5) from the action to
        appear in the rule text, to reduce false positives from generic terms.
        """
        action_words = set()
        for w in action_text.split():
            w_clean = w.strip(".,;:!?()[]{}\"'-").lower()
            if len(w_clean) > 5 and w_clean not in self._NOISE_WORDS:
                action_words.add(w_clean)

        if not action_words:
            return False

        rule_text_lower = rule_text.lower()
        matches = sum(1 for w in action_words if w in rule_text_lower)
        return matches >= 2

    def check_action(self, action: dict) -> list[dict]:
        """Check an action against all MUST and MUST NOT rules.

        Returns a list of potential violations and requirements.
        Uses a multi-word relevance heuristic to reduce false positives.
        """
        results = []

        action_text = " ".join(str(v) for v in action.values()).lower()

        # Check MUST NOT rules for potential violations
        for rule in self.get_must_not_rules():
            if self._is_relevant(action_text, rule.text):
                results.append(  # noqa: PERF401
                    {
                        "type": "prohibition",
                        "article": rule.article_id,
                        "section": rule.section_title,
                        "rule": rule.text,
                        "obligation": "MUST NOT",
                    }
                )

        # Check MUST rules for unmet requirements
        for rule in self.get_must_rules():
            if self._is_relevant(action_text, rule.text):
                results.append(  # noqa: PERF401
                    {
                        "type": "requirement",
                        "article": rule.article_id,
                        "section": rule.section_title,
                        "rule": rule.text,
                        "obligation": "MUST",
                    }
                )

        return results

    def stats(self) -> dict:
        """Return statistics about the loaded constitution."""
        return {
            "total_articles": len(self.articles),
            "total_rules": len(self.rules),
            "must_count": len(self._rules_by_obligation[ObligationLevel.MUST]),
            "must_not_count": len(self._rules_by_obligation[ObligationLevel.MUST_NOT]),
            "may_count": len(self._rules_by_obligation[ObligationLevel.MAY]),
            "should_count": len(self._rules_by_obligation[ObligationLevel.SHOULD]),
            "articles_with_rules": sum(1 for a in self.articles.values() if a.rules),
            "constitution_dir": self.constitution_dir,
        }