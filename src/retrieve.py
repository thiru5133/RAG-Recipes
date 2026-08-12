"""Retrieval front door: one function both the CLI and the UI call."""
from typing import Dict, List, Optional

from config import STRATEGIES, TOP_K
from store import get_collection, query

_cache: Dict[str, object] = {}


def collection_for(strategy: str):
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}; expected {list(STRATEGIES)}")
    if strategy not in _cache:
        _cache[strategy] = get_collection(STRATEGIES[strategy])
    return _cache[strategy]


def search(
    question: str,
    strategy: str = "structured",
    k: int = TOP_K,
    where: Optional[Dict] = None,
) -> List[Dict]:
    return query(collection_for(strategy), question, k=k, where=where)


def dietary_filter(tag: str) -> Dict:
    """Build a Chroma `where` clause from a dietary tag, e.g. 'vegan'."""
    import re

    key = "tag_" + re.sub(r"[^a-z0-9]+", "_", tag.strip().lower())
    return {key: True}
