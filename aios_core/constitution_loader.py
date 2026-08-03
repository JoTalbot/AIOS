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

# Patterns for obligation keywords
_MUST_NOT_RE = re.compile(r"\bMUST\s+NOT\b", re.IGNORECASE)
_MUST_RE = re.compile(r"\bMUST\b(?!\s+NOT\b)", re.IGNORECASE)
_SHOULD_NOT_RE = re.compile(r"\bSHOULD\s+NOT\b", re.IGNORECASE)
_SHOULD_RE = re.compile(r"\bSHOULD\b(?!\s+NOT\b)", re.IGNORECASE)
_MAY_RE = re.compile(r"\bMAY\b(?!\s+NOT\b)", re.IGNORECASE)


def _roman_to_int(roman: str) -> int:
    """Convert a Roman numeral string to an integer."""
    roman = roman.upper()
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(roman):
        val = values.get(ch, 0)
        if val < prev:
            total -= val
        else:
            total += val
        prev = val
    return total


def _detect_obligation(text: str) -> ObligationLevel:
    """Detect the strongest obligation keyword in a line of text.

    Priority: MUST NOT > MUST > SHOULD NOT > SHOULD > MAY
    """
    if _MUST_NOT_RE.search(text):
        return ObligationLevel.MUST_NOT
    if _MUST_RE.search(text):
        return ObligationLevel.MUST
    if _SHOULD_NOT_RE.search(text):
        return ObligationLevel.SHOULD_NOT
    if _SHOULD_RE.search(text):
        return ObligationLevel.SHOULD
    if _MAY_RE.search(text):
        return ObligationLevel.MAY
    return ObligationLevel.UNKNOWN


# Article filename pattern: ARTICLE-I-IDENTITY.md, ARTICLE-V-SECURITY.md
_ARTICLE_FILENAME_RE = re.compile(
    r"ARTICLE-(?P<roman>[IVXLCDM]+)-(?P<name>[\w-]+)\.md", re.IGNORECASE
)

# Section headers: "# 1. Title" / "## 1. Title" / "### 1. Title"
_SECTION_HEADER_RE = re.compile(r"^#{1,3}\s+(\d+)\.\s+(.+)$")


def _parse_article_id(filename: str) -> tuple[str, str, int] | None:
    """Extract (roman, name, number) from an ARTICLE-<roman>-<name>.md filename."""
    match = _ARTICLE_FILENAME_RE.match(os.path.basename(filename))
    if not match:
        return None
    roman = match.group("roman")
    name = match.group("name").replace("-", " ").title()
    num = _roman_to_int(roman)
    return (roman, name, num)


class ConstitutionLoader:
    def __init__(self, constitution_dir: str | None = None):
        if constitution_dir is None:
            this_dir = Path(__file__).resolve().parent.parent
            constitution_dir = str(this_dir / "docs" / "constitution")
        self.constitution_dir = constitution_dir
        self.articles: dict[str, Article] = {}
        self.rules: list[ConstitutionalRule] = []
        self._rules_by_obligation: dict[ObligationLevel, list[ConstitutionalRule]] = {
            level: [] for level in ObligationLevel
        }
        self._rules_by_keyword: dict[str, list[ConstitutionalRule]] = {}
        if os.path.isdir(constitution_dir):
            self.load_constitution()

    def load_constitution(self):
        if os.path.isdir(self.constitution_dir):
            self.articles = {}
            self.rules = []
            self._rules_by_obligation = {level: [] for level in ObligationLevel}
            self._rules_by_keyword = {}
        for root, dirs, files in os.walk(self.constitution_dir):
            for file in files:
                if file.endswith(".md"):
                    article_path = os.path.join(root, file)
                    with open(article_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        self.parse_article(content, article_path)

    def parse_article(self, content: str, article_path: str):
        """Parse one article markdown file.

        Article id берётся из имени файла (ARTICLE-<рим>-<имя>.md),
        секции — из заголовков «# N. Title», правила — из строк с MUST/MAY/SHOULD.
        """
        id_info = _parse_article_id(article_path)
        if id_info is not None:
            _roman, name, _num = id_info
            article_id = f"ARTICLE-{_roman}"
            default_title = name
        else:
            title_match = re.search(r"## (.+)", content)
            if title_match:
                default_title = title_match.group(1).strip("# ")
                article_id = f"ARTICLE-{default_title.lower().replace(' ', '-')}"
            else:
                default_title = "Untitled"
                article_id = "ARTICLE-UNKNOWN"

        # метаданные из первых строк файла
        status = "Unknown"
        level = "Unknown"
        scope = "General"
        for line in content.split("\n")[:15]:
            m = _STATUS_RE.search(line)
            if m:
                status = m.group(1).strip()
            m = _LEVEL_RE.search(line)
            if m:
                level = m.group(1).strip()
            m = _SCOPE_RE.search(line)
            if m:
                scope = m.group(1).strip()

        article = Article(
            article_id=article_id,
            title=default_title,
            status=status,
            level=level,
            scope=scope,
            raw_content=content,
        )

        self.articles[article_id] = article

        section_title = ""
        section_number = 0
        for line in content.split("\n"):
            section_match = _SECTION_HEADER_RE.match(line)
            if section_match:
                section_number = int(section_match.group(1))
                section_title = section_match.group(2).strip()
                article.sections.append({"number": section_number, "title": section_title})
                continue

            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("---"):
                continue

            obligation = _detect_obligation(stripped)
            if obligation == ObligationLevel.UNKNOWN:
                continue

            rule = ConstitutionalRule(
                article_id=article_id,
                article_title=default_title,
                section_number=section_number,
                section_title=section_title,
                obligation=obligation,
                text=stripped,
                status=status,
                scope=scope,
                raw_line=line,
            )
            self.rules.append(rule)
            article.rules.append(rule)
            self._rules_by_obligation.setdefault(obligation, []).append(rule)
            for kw in self._extract_keywords(stripped):
                self._rules_by_keyword.setdefault(kw.lower(), []).append(rule)

    def _extract_keywords(self, line: str) -> list[str]:
        return [kw for kw in _KEYWORD_PATTERN.findall(line) if len(kw) > 3]

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
            "must_count": len(self._rules_by_obligation.get(ObligationLevel.MUST, [])),
            "must_not_count": len(self._rules_by_obligation.get(ObligationLevel.MUST_NOT, [])),
            "may_count": len(self._rules_by_obligation.get(ObligationLevel.MAY, [])),
            "should_count": len(self._rules_by_obligation.get(ObligationLevel.SHOULD, [])),
            "articles_with_rules": sum(1 for a in self.articles.values() if a.rules),
            "constitution_dir": self.constitution_dir,
        }