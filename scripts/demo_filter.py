"""Metadata filtering demo: dietary_tags changes which recipe wins Top-1."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from retrieve import dietary_filter, search  # noqa: E402

DEMO_QUERY = "how much green curry paste do I need?"
DEMO_TAG = "vegan"


def run(query: str = DEMO_QUERY, tag: str = DEMO_TAG, strategy: str = "structured", k: int = 5):
    unfiltered = search(query, strategy=strategy, k=k)
    where = dietary_filter(tag)
    filtered = search(query, strategy=strategy, k=k, where=where)
    return {
        "query": query,
        "tag": tag,
        "where": where,
        "strategy": strategy,
        "unfiltered": unfiltered,
        "filtered": filtered,
        "top1_changed": bool(unfiltered and filtered)
        and unfiltered[0]["chunk_id"] != filtered[0]["chunk_id"],
    }


def _show(title, hits):
    print(f"\n{title}")
    for h in hits:
        m = h["metadata"]
        print(f"  {h['rank']}. [{h['chunk_id']}] {m['recipe_id']} {m['recipe_title'][:34]:<34} "
              f"{m['section']:<12} score={h['score']:.4f}")


def main():
    r = run()
    print(f"Query: {r['query']!r}   filter: {r['where']}")
    _show("UNFILTERED", r["unfiltered"])
    _show(f"FILTERED (dietary_tags contains {r['tag']})", r["filtered"])
    print(f"\nTop-1 changed: {r['top1_changed']}")


if __name__ == "__main__":
    main()
