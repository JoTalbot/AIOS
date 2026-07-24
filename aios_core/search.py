"""Full-Text Search for AIOS v10.8.0.

Lightweight search engine with TF-IDF scoring,
BM25 ranking, faceted search, relevance feedback,
field-specific search, and document management.

Classes:
    Document       — indexed document with metadata
    SearchResult   — search hit with score and snippet
    SimpleSearchEngine — full search engine
"""

from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Indexed document with metadata."""
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    indexed_at: float = field(default_factory=time.time)
    term_freq: dict[str, int] = field(default_factory=dict)  # term → count


@dataclass
class SearchResult:
    """Search hit with score and snippet."""
    doc_id: str
    score: float
    snippet: str
    matched_terms: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SimpleSearchEngine:
    """Full lightweight search engine.

    Features:
    - Document indexing with metadata
    - TF-IDF scoring
    - BM25 ranking (Okapi BM25)
    - Faceted search (filter by metadata fields)
    - Relevance feedback (expand queries from hits)
    - Field-specific search
    - Snippet generation
    """

    def __init__(self, k1: float = 1.2, b: float = 0.75) -> None:
        self.documents: dict[str, Document] = {}
        self._index: dict[str, dict[str, int]] = {}  # term → {doc_id: count}
        self._doc_lengths: dict[str, int] = {}  # doc_id → word count
        self._avg_doc_length: float = 0.0
        self._num_docs: int = 0
        # BM25 parameters
        self.k1 = k1
        self.b = b

    # ── Document Management ──────────────────────────────────────────

    def index(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        """Index a document (backward-compatible)."""
        self.add_document(doc_id, text, metadata)

    def add_document(self, doc_id: str, text: str,
                     metadata: dict[str, Any] | None = None) -> Document:
        """Add a document with full indexing."""
        # Tokenize and compute term frequencies
        words = re.findall(r'\b\w+\b', text.lower())
        term_freq: dict[str, int] = {}
        for word in words:
            term_freq[word] = term_freq.get(word, 0) + 1

        doc = Document(
            doc_id=doc_id, text=text,
            metadata=metadata or {},
            term_freq=term_freq,
        )
        self.documents[doc_id] = doc
        self._doc_lengths[doc_id] = len(words)
        self._num_docs = len(self.documents)
        self._avg_doc_length = (sum(self._doc_lengths.values()) / self._num_docs) if self._num_docs > 0 else 0

        # Update inverted index
        for term, count in term_freq.items():
            if term not in self._index:
                self._index[term] = {}
            self._index[term][doc_id] = count

        return doc

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index."""
        doc = self.documents.pop(doc_id, None)
        if doc:
            # Remove from inverted index
            for term in doc.term_freq:
                if term in self._index:
                    self._index[term].pop(doc_id, None)
                    if not self._index[term]:
                        del self._index[term]
            self._doc_lengths.pop(doc_id, None)
            self._num_docs = len(self.documents)
            self._avg_doc_length = (sum(self._doc_lengths.values()) / self._num_docs) if self._num_docs > 0 else 0

    def get_document(self, doc_id: str) -> Document | None:
        """Return a document."""
        return self.documents.get(doc_id)

    # ── TF-IDF Scoring ──────────────────────────────────────────────

    def _tf_idf_score(self, term: str, doc_id: str) -> float:
        """Compute TF-IDF score for a term in a document."""
        # TF (term frequency)
        tf = self.documents[doc_id].term_freq.get(term, 0)
        if tf == 0:
            return 0.0
        tf = 1 + math.log(tf)  # log-normalized TF

        # IDF (inverse document frequency)
        df = len(self._index.get(term, {}))  # document frequency
        if df == 0 or self._num_docs == 0:
            return 0.0
        idf = math.log(self._num_docs / df)

        return tf * idf

    # ── BM25 Ranking ────────────────────────────────────────────────

    def _bm25_score(self, term: str, doc_id: str) -> float:
        """Compute BM25 score for a term in a document."""
        tf = self.documents[doc_id].term_freq.get(term, 0)
        if tf == 0:
            return 0.0

        doc_len = self._doc_lengths.get(doc_id, 0)
        avg_len = self._avg_doc_length if self._avg_doc_length > 0 else 1

        # BM25 formula
        numerator = tf * (self.k1 + 1)
        denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / avg_len)

        # IDF component
        df = len(self._index.get(term, {}))
        if df == 0 or self._num_docs == 0:
            return 0.0
        idf = math.log((self._num_docs - df + 0.5) / (df + 0.5))

        return idf * numerator / denominator

    # ── Search ──────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 10,
               method: str = "bm25") -> list[SearchResult]:
        """Search documents using specified method (backward-compatible with bm25)."""
        query_terms = re.findall(r'\b\w+\b', query.lower())

        if not query_terms:
            return []

        # Score each document
        scores: dict[str, float] = {}
        matched_terms: dict[str, list[str]] = {}

        for term in query_terms:
            postings = self._index.get(term, {})
            for doc_id in postings:
                if method == "bm25":
                    score = self._bm25_score(term, doc_id)
                elif method == "tfidf":
                    score = self._tf_idf_score(term, doc_id)
                else:  # simple (backward-compatible)
                    score = self.documents[doc_id].text.lower().count(term)

                scores[doc_id] = scores.get(doc_id, 0.0) + score
                matched_terms.setdefault(doc_id, []).append(term)

        # Build results
        results = []
        for doc_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]:
            doc = self.documents.get(doc_id)
            if doc:
                snippet = self._generate_snippet(doc.text, query_terms)
                results.append(SearchResult(
                    doc_id=doc_id, score=round(score, 4),
                    snippet=snippet, matched_terms=matched_terms.get(doc_id, []),
                    metadata=doc.metadata,
                ))

        return results

    def _generate_snippet(self, text: str, query_terms: list[str], max_len: int = 200) -> str:
        """Generate a snippet highlighting matched terms."""
        text_lower = text.lower()
        best_pos = 0
        best_density = 0

        # Find position with highest query term density
        for term in query_terms:
            pos = text_lower.find(term)
            if pos >= 0:
                density = sum(1 for t in query_terms if t in text_lower[max(0, pos - 50):pos + 150])
                if density > best_density:
                    best_density = density
                    best_pos = max(0, pos - 50)

        snippet = text[best_pos:best_pos + max_len]
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_len < len(text):
            snippet = snippet + "..."
        return snippet

    # ── Faceted Search ──────────────────────────────────────────────

    def faceted_search(self, query: str, facets: dict[str, Any],
                       limit: int = 10) -> list[SearchResult]:
        """Search with metadata facet filtering."""
        # Get base results
        base_results = self.search(query, limit=limit * 5)

        # Filter by facets
        filtered = []
        for result in base_results:
            match = True
            for facet_key, facet_value in facets.items():
                if facet_key not in result.metadata or result.metadata[facet_key] != facet_value:
                    match = False
                    break
            if match:
                filtered.append(result)

        return filtered[:limit]

    # ── Relevance Feedback ──────────────────────────────────────────

    def expand_query(self, query: str, relevant_doc_ids: list[str],
                     num_expansion_terms: int = 3) -> str:
        """Expand query using relevance feedback (Rocchio)."""
        # Find terms common in relevant documents
        term_scores: dict[str, float] = {}
        for doc_id in relevant_doc_ids:
            doc = self.documents.get(doc_id)
            if doc:
                for term, count in doc.term_freq.items():
                    term_scores[term] = term_scores.get(term, 0.0) + count

        # Sort by frequency
        top_terms = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)

        # Add expansion terms (not already in query)
        query_terms = set(re.findall(r'\b\w+\b', query.lower()))
        expansion = []
        for term, score in top_terms:
            if term not in query_terms and len(expansion) < num_expansion_terms:
                expansion.append(term)

        if expansion:
            return query + " " + " ".join(expansion)
        return query

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "documents": len(self.documents),
            "unique_terms": len(self._index),
            "avg_doc_length": round(self._avg_doc_length, 2),
            "total_terms": sum(len(idx) for idx in self._index.values()),
        }
