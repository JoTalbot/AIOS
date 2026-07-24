"""Vector search engine — lightweight semantic product matching without external dependencies.

Uses TF-IDF-like term frequency vectors for product similarity:
- Tokenizes product titles and descriptions
- Builds vocabulary from all stored products
- Computes cosine similarity between product vectors
- Finds nearest neighbors for a query or reference product

No external embedding model required — pure Python implementation
suitable for offline / embedded deployment on Android devices.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from aios_core.modules.olx.storage import OLXStorage


@dataclass
class SearchResult:
    """A single search result with similarity score."""

    fingerprint: str
    title: str
    price: float | None
    score: float
    platform: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "fingerprint": self.fingerprint,
            "title": self.title,
            "price": self.price,
            "score": round(self.score, 4),
            "platform": self.platform,
            "url": self.url,
        }


class VectorSearchEngine:
    """Lightweight TF-IDF vector search for product matching.

    Build vocabulary from stored products, compute term vectors,
    and find nearest neighbors via cosine similarity.
    """

    def __init__(
        self,
        storage: OLXStorage | None = None,
        min_term_freq: int = 2,
        max_vocab_size: int = 5000,
    ) -> None:
        """Initialize VectorSearchEngine.

        Args:
            storage: OLXStorage (or subclass) to index products from.
            min_term_freq: Minimum term frequency to include in vocabulary.
            max_vocab_size: Maximum vocabulary size (top-K by frequency).
        """
        self.storage = storage
        self.min_term_freq = min_term_freq
        self.max_vocab_size = max_vocab_size
        self._vocab: dict[str, int] = {}  # term → index
        self._idf: dict[str, float] = {}  # term → IDF weight
        self._vectors: dict[str, list[float]] = {}  # fingerprint → vector
        self._titles: dict[str, str] = {}  # fingerprint → title
        self._prices: dict[str, float | None] = {}  # fingerprint → price
        self._urls: dict[str, str | None] = {}  # fingerprint → url
        self._indexed = False

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into normalized lowercase terms."""
        # Simple whitespace + punctuation split
        import re

        tokens = re.findall(r"\b[a-zа-яієїґ0-9]{2,}\b", text.lower())
        return tokens

    def build_index(self) -> int:
        """Build TF-IDF index from all products in storage.

        Returns:
            Number of indexed products.
        """
        if not self.storage:
            return 0

        ads = self.storage.get_ads()
        n_docs = len(ads)
        if n_docs == 0:
            self._indexed = True
            return 0

        # Step 1: Collect all term frequencies across documents
        doc_freq: Counter = Counter()  # How many docs contain each term
        doc_tokens: dict[str, list[str]] = {}

        for ad in ads:
            tokens = self._tokenize(ad.title)
            if ad.url:
                tokens += self._tokenize(str(ad.url))
            doc_tokens[ad.fingerprint] = tokens
            unique_tokens = set(tokens)
            for t in unique_tokens:
                doc_freq[t] += 1

            self._titles[ad.fingerprint] = ad.title
            self._prices[ad.fingerprint] = ad.price
            self._urls[ad.fingerprint] = ad.url

        # Step 2: Build vocabulary (filter by min_term_freq, limit by max_vocab_size)
        filtered = {t: f for t, f in doc_freq.items() if f >= self.min_term_freq}
        sorted_terms = sorted(filtered.items(), key=lambda x: -x[1])
        top_terms = sorted_terms[: self.max_vocab_size]

        self._vocab = {t: i for i, (t, _) in enumerate(top_terms)}
        vocab_size = len(self._vocab)

        # Step 3: Compute IDF weights
        self._idf = {}
        for t, f in top_terms:
            self._idf[t] = math.log(n_docs / f) + 1.0  # smooth IDF

        # Step 4: Compute TF-IDF vectors for each product
        self._vectors = {}
        for fp, tokens in doc_tokens.items():
            tf: Counter = Counter(tokens)
            vector = [0.0] * vocab_size
            for t in tf:
                if t in self._vocab:
                    idx = self._vocab[t]
                    vector[idx] = tf[t] * self._idf.get(t, 1.0)
            # Normalize
            norm = math.sqrt(sum(v * v for v in vector))
            if norm > 0:
                vector = [v / norm for v in vector]
            self._vectors[fp] = vector

        self._indexed = True
        return len(self._vectors)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search for products matching a text query.

        Args:
            query: Search query text.
            limit: Maximum number of results.

        Returns:
            List of SearchResult sorted by similarity score (descending).
        """
        if not self._indexed:
            self.build_index()

        if not self._vectors:
            return []

        # Compute query vector
        tokens = self._tokenize(query)
        vocab_size = len(self._vocab)
        tf: Counter = Counter(tokens)
        q_vector = [0.0] * vocab_size
        for t in tf:
            if t in self._vocab:
                idx = self._vocab[t]
                q_vector[idx] = tf[t] * self._idf.get(t, 1.0)
        norm = math.sqrt(sum(v * v for v in q_vector))
        if norm > 0:
            q_vector = [v / norm for v in q_vector]

        # Compute cosine similarity with all indexed products
        results: list[SearchResult] = []
        for fp, p_vector in self._vectors.items():
            score = self._cosine(q_vector, p_vector)
            if score > 0.01:  # Skip very low scores
                results.append(
                    SearchResult(
                        fingerprint=fp,
                        title=self._titles.get(fp, ""),
                        price=self._prices.get(fp),
                        score=score,
                        url=self._urls.get(fp),
                    )
                )

        results.sort(key=lambda r: -r.score)
        return results[:limit]

    def find_similar(self, fingerprint: str, limit: int = 10) -> list[SearchResult]:
        """Find products similar to a reference product.

        Args:
            fingerprint: Reference product fingerprint.
            limit: Maximum number of similar products.

        Returns:
            List of SearchResult sorted by similarity (descending).
        """
        if not self._indexed:
            self.build_index()

        ref_vector = self._vectors.get(fingerprint)
        if not ref_vector:
            return []

        results: list[SearchResult] = []
        for fp, p_vector in self._vectors.items():
            if fp == fingerprint:
                continue
            score = self._cosine(ref_vector, p_vector)
            if score > 0.01:
                results.append(
                    SearchResult(
                        fingerprint=fp,
                        title=self._titles.get(fp, ""),
                        price=self._prices.get(fp),
                        score=score,
                        url=self._urls.get(fp),
                    )
                )

        results.sort(key=lambda r: -r.score)
        return results[:limit]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
