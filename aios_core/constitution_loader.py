"""AIOS Constitution Loader v3.0.0

Loads and parses constitutional articles from markdown files into structured rules.
Extracts MUST / MUST NOT / MAY / SHOULD directives and binds them to articles.
"""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


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

# Patterns for section headers: "# 1. Title" or "## 1. Title"
_SECTION_HEADER_RE = re.compile(r"^#{1,3}\s+(\d+)\.\s+(.+)$")

# Patterns for obligation keywords
_MUST_NOT_RE = re.compile(r"\bMUST\s+NOT\b", re.IGNORECASE)
_MUST_RE = re.compile(r"\bMUST\b(?!\s+NOT\b)", re.IGNORECASE)
_MAY_RE = re.compile(r"\bMAY\b(?!\s+NOT\b)", re.IGNORECASE)
_SHOULD_NOT_RE = re.compile(r"\bSHOULD\s+NOT\b", re.IGNORECASE)
_SHOULD_RE = re.compile(r"\bSHOULD\b(?!\s+NOT\b)", re.IGNORECASE)

# Article filename pattern: ARTICLE-I-IDENTITY.md, ARTICLE-XXXII-SECURITY.md
_ARTICLE_FILENAME_RE = re.compile(
    r"ARTICLE-(?P<roman>[IVXLCDM]+)-(?P<name>[\w-]+)\.md", re.IGNORECASE
)


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


def _parse_article_id(filename: str) -> Optional[tuple[str, str, int]]:
    """Extract article ID, name, and numeric index from filename."""
    match = _ARTICLE_FILENAME_RE.match(os.path.basename(filename))
    if not match:
        return None
    roman = match.group("roman")
    name = match.group("name").replace("-", " ").title()
    num = _roman_to_int(roman)
    return (roman, name, num)


def _extract_bullet_items(text: str) -> list[str]:
    """Extract bullet point items from markdown text."""
    items = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            items.append(stripped[2:].strip())
    return items


def _parse_article(filepath: str) -> Optional[Article]:
    """Parse a single constitutional article from a markdown file."""
    id_info = _parse_article_id(filepath)
    if id_info is None:
        return None

    roman, name, num = id_info
    article_id = f"ARTICLE-{roman}"

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract metadata from the first few lines
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

    # Parse sections and extract rules
    sections = []
    rules = []
    current_section_num = 0
    current_section_title = ""

    for line in content.split("\n"):
        section_match = _SECTION_HEADER_RE.match(line)
        if section_match:
            current_section_num = int(section_match.group(1))
            current_section_title = section_match.group(2).strip()
            sections.append(
                {
                    "number": current_section_num,
                    "title": current_section_title,
                }
            )
            continue

        # Extract rules from lines with obligation keywords
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue

        obligation = _detect_obligation(stripped)
        if obligation != ObligationLevel.UNKNOWN:
            rule = ConstitutionalRule(
                article_id=article_id,
                article_title=name,
                section_number=current_section_num,
                section_title=current_section_title,
                obligation=obligation,
                text=stripped,
                status=status,
                scope=scope,
                raw_line=line,
            )
            rules.append(rule)

    return Article(
        article_id=article_id,
        title=name,
        status=status,
        level=level,
        scope=scope,
        sections=sections,
        rules=rules,
        raw_content=content,
    )


class ConstitutionLoader:
    """Loads and indexes all constitutional articles from a directory.

    Provides structured access to articles, rules, and obligation-based queries.
    """

    def __init__(self, constitution_dir: Optional[str] = None):
        """Initialize loader.

        Args:
            constitution_dir: Path to directory containing ARTICLE-*.md files.
                             If None, uses default path relative to this module.
        """
        if constitution_dir is None:
            this_dir = Path(__file__).resolve().parent.parent
            constitution_dir = str(this_dir / "docs" / "constitution")

        self.constitution_dir = constitution_dir
        self.articles: dict[str, Article] = {}
        self.rules: list[ConstitutionalRule] = []
        self._rules_by_obligation: dict[ObligationLevel, list[ConstitutionalRule]] = {
            level: [] for level in ObligationLevel
        }
        self._rules_by_article: dict[str, list[ConstitutionalRule]] = {}
        self._rules_by_keyword: dict[str, list[ConstitutionalRule]] = {}

        self._load_all()

    def _load_all(self):
        """Load and parse all article files from the constitution directory."""
        if not os.path.isdir(self.constitution_dir):
            raise FileNotFoundError(f"Constitution directory not found: {self.constitution_dir}")

        filenames = sorted(os.listdir(self.constitution_dir))
        article_files = [f for f in filenames if _ARTICLE_FILENAME_RE.match(f)]

        for filename in article_files:
            filepath = os.path.join(self.constitution_dir, filename)
            article = _parse_article(filepath)
            if article is not None:
                self.articles[article.article_id] = article
                self.rules.extend(article.rules)
                self._rules_by_article[article.article_id] = article.rules

                for rule in article.rules:
                    self._rules_by_obligation[rule.obligation].append(rule)

                    # Index by significant keywords in rule text
                    for keyword in self._extract_keywords(rule.text):
                        self._rules_by_keyword.setdefault(keyword, []).append(rule)

        # Build keyword index
        self._build_keyword_index()

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract significant keywords from rule text for indexing."""
        # Extract capitalized words that are likely domain terms
        keywords = re.findall(r"\b[A-Z][A-Za-z]{3,}\b", text)
        # Filter out common words
        stop_words = {
            "MUST",
            "MAY",
            "SHOULD",
            "Every",
            "When",
            "Before",
            "After",
            "This",
            "That",
            "These",
            "Those",
            "Which",
            "Where",
            "What",
            "Each",
            "Both",
            "Such",
            "From",
            "With",
            "Have",
            "Being",
            "AIOS",
            "The",
            "For",
            "And",
            "Not",
            "But",
            "Are",
            "Can",
            "Has",
            "Its",
            "New",
            "All",
            "Any",
            "How",
            "Who",
            "Why",
            "Security",
            "Evolution",
            "Autonomy",
            "Constitutional",
            "Constitution",
            "Article",
            "End",
            "Final",
            "Constitutional",
        }
        return [kw for kw in keywords if kw not in stop_words and len(kw) > 3]

    def _build_keyword_index(self):
        """Build a comprehensive keyword-to-rules index."""
        self._rules_by_keyword = {}
        for rule in self.rules:
            for keyword in self._extract_keywords(rule.text):
                self._rules_by_keyword.setdefault(keyword, []).append(rule)

    # --- Query API ---

    def get_article(self, article_id: str) -> Optional[Article]:
        """Get a parsed article by its ID (e.g. 'ARTICLE-V')."""
        return self.articles.get(article_id)

    def get_rules(self, obligation: Optional[ObligationLevel] = None) -> list[ConstitutionalRule]:
        """Get rules, optionally filtered by obligation level."""
        if obligation is None:
            return list(self.rules)
        return list(self._rules_by_obligation.get(obligation, []))

    def get_must_rules(self) -> list[ConstitutionalRule]:
        """Get all MUST rules (mandatory requirements)."""
        return self.get_rules(ObligationLevel.MUST)

    def get_must_not_rules(self) -> list[ConstitutionalRule]:
        """Get all MUST NOT rules (prohibitions)."""
        return self.get_rules(ObligationLevel.MUST_NOT)

    def get_may_rules(self) -> list[ConstitutionalRule]:
        """Get all MAY rules (permissions)."""
        return self.get_rules(ObligationLevel.MAY)

    def get_should_rules(self) -> list[ConstitutionalRule]:
        """Get all SHOULD rules (recommendations)."""
        return self.get_rules(ObligationLevel.SHOULD)

    def search_rules(self, keyword: str) -> list[ConstitutionalRule]:
        """Search rules by keyword in text."""
        keyword_upper = keyword.upper()
        results = []
        for rule in self.rules:
            if keyword_upper in rule.text.upper():
                results.append(rule)
        return results

    def rules_for_topic(self, topic: str) -> list[ConstitutionalRule]:
        """Find rules related to a topic using keyword index."""
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
                results.append(
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
                results.append(
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
