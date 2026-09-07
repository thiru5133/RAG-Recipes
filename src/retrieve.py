"""Retrieval front door: one function both the CLI and the UI call.

Supports three modes:
- "semantic": ChromaDB vector similarity (original behaviour)
- "bm25": BM25 keyword search
- "hybrid": RRF fusion of semantic + BM25
"""
from typing import Dict, List, Optional

from config import RRF_K, STRATEGIES, TOP_K
from store import get_collection, query

_cache: Dict[str, object] = {}


def collection_for(strategy: str):
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}; expected {list(STRATEGIES)}")
    if strategy not in _cache:
        _cache[strategy] = get_collection(STRATEGIES[strategy])
    return _cache[strategy]


def _rrf_fuse(
    semantic_hits: List[Dict], bm25_hits: List[Dict], k: int, rrf_k: int = RRF_K
) -> List[Dict]:
    """Reciprocal Rank Fusion: merge two ranked lists into one.

    RRF score for document d = sum over all lists L of  1 / (rrf_k + rank_in_L).
    Documents not present in a list get no contribution from that list.
    """
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict] = {}  # chunk_id -> best hit dict

    for hits in (semantic_hits, bm25_hits):
        for h in hits:
            cid = h["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + h["rank"])
            if cid not in doc_map:
                doc_map[cid] = h

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]

    fused = []
    for rank, (cid, rrf_score) in enumerate(ranked, start=1):
        hit = dict(doc_map[cid])  # copy
        hit["rank"] = rank
        hit["score"] = round(rrf_score, 4)
        hit["distance"] = 0.0  # RRF scores are not distances
        fused.append(hit)
    return fused


def search(
    question: str,
    strategy: str = "structured",
    k: int = TOP_K,
    where: Optional[Dict] = None,
    mode: str = "semantic",
) -> List[Dict]:
    """Retrieve top-k chunks.

    Parameters
    ----------
    mode : str
        "semantic" (default, original behaviour), "bm25", or "hybrid" (RRF fusion).
    """
    coll = collection_for(strategy)

    if mode == "semantic":
        return query(coll, question, k=k, where=where)

    if mode == "bm25":
        from bm25_search import get_bm25_index
        idx = get_bm25_index(coll)
        return idx.search(question, k=k, where=where)

    if mode == "hybrid":
        from bm25_search import get_bm25_index
        # Fetch more candidates from each source, then fuse down to k
        n_candidates = k * 2
        semantic_hits = query(coll, question, k=n_candidates, where=where)
        bm25_idx = get_bm25_index(coll)
        bm25_hits = bm25_idx.search(question, k=n_candidates, where=where)
        return _rrf_fuse(semantic_hits, bm25_hits, k=k)

    raise ValueError(f"unknown mode {mode!r}; expected 'semantic', 'bm25', or 'hybrid'")


def dietary_filter(tag: str) -> Dict:
    """Build a Chroma `where` clause from a dietary tag, e.g. 'vegan'."""
    import re

    key = "tag_" + re.sub(r"[^a-z0-9]+", "_", tag.strip().lower())
    return {key: True}
