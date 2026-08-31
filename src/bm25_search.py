"""BM25 keyword search over the same chunks stored in ChromaDB.

Provides exact-term matching (ingredient names, codes, IDs) that
semantic embeddings can miss.
"""
import re
from typing import Dict, List, Optional

from rank_bm25 import BM25Okapi


def _tokenise(text: str) -> List[str]:
    """Lowercase whitespace-and-punctuation split, good enough for BM25."""
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25Index:
    """Lazy BM25 index built from a ChromaDB collection."""

    def __init__(self, collection):
        data = collection.get(include=["documents", "metadatas"])
        self._ids: List[str] = data["ids"]
        self._docs: List[str] = data["documents"]
        self._metas: List[Dict] = data["metadatas"]
        corpus = [_tokenise(doc) for doc in self._docs]
        self._bm25 = BM25Okapi(corpus)

    def search(self, question: str, k: int = 5, where: Optional[Dict] = None) -> List[Dict]:
        """Return top-k BM25 hits in the same dict format as store.query()."""
        tokens = _tokenise(question)
        scores = self._bm25.get_scores(tokens)

        # Build (index, score) pairs, optionally filtered
        candidates = []
        for i, s in enumerate(scores):
            if where:
                meta = self._metas[i]
                if not all(meta.get(wk) == wv for wk, wv in where.items()):
                    continue
            candidates.append((i, float(s)))

        # Sort descending by score, take top-k
        candidates.sort(key=lambda x: x[1], reverse=True)
        top = candidates[:k]

        hits = []
        for rank, (idx, score) in enumerate(top, start=1):
            hits.append({
                "rank": rank,
                "chunk_id": self._ids[idx],
                "text": self._docs[idx],
                "metadata": self._metas[idx],
                "distance": 0.0,  # BM25 has no cosine distance
                "score": round(score, 4),
            })
        return hits


# Module-level cache: one BM25Index per collection name
_bm25_cache: Dict[str, BM25Index] = {}


def get_bm25_index(collection) -> BM25Index:
    """Return a cached BM25Index for a ChromaDB collection."""
    name = collection.name
    if name not in _bm25_cache:
        _bm25_cache[name] = BM25Index(collection)
    return _bm25_cache[name]


def reset_bm25_cache():
    """Clear the BM25 cache (call after re-ingesting)."""
    _bm25_cache.clear()
