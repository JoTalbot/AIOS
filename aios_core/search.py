"""Full-Text Search for AIOS Memory/Knowledge"""

import re
from typing import List, Dict, Any


class SimpleSearchEngine:
    """Lightweight full-text search engine."""

    def __init__(self):
        self.documents: Dict[str, str] = {}

    def index(self, doc_id: str, text: str):
        self.documents[doc_id] = text.lower()

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        q = query.lower()
        results = []
        for doc_id, text in self.documents.items():
            if q in text:
                score = text.count(q)
                results.append({"id": doc_id, "score": score, "snippet": text[:200]})
        return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]

    def stats(self) -> dict:
        return {"documents": len(self.documents)}