"""Ad-hoc retrieval check, no LLM.

    python scripts/search.py "how much cream?"
    python scripts/search.py --strategy basic --k 3 "how much cream?"
    python scripts/search.py --tag vegan "how much curry paste?"
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from retrieve import dietary_filter, search  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+")
    ap.add_argument("--strategy", default="structured", choices=["structured", "basic"])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--mode", default="semantic", choices=["semantic", "bm25", "hybrid"])
    ap.add_argument(
        "--rerank",
        action="store_true",
        help="second stage: BM25 + coverage + section prior over a wider pool",
    )
    ap.add_argument("--tag", default=None, help="filter on a dietary_tags value, e.g. vegan")
    args = ap.parse_args()

    question = " ".join(args.question)
    where = dietary_filter(args.tag) if args.tag else None
    hits = search(
        question,
        strategy=args.strategy,
        k=args.k,
        where=where,
        mode=args.mode,
        rerank=args.rerank,
    )

    print(
        f"Q: {question!r}  strategy={args.strategy} mode={args.mode} "
        f"k={args.k} rerank={args.rerank} where={where}"
    )
    if not hits:
        print("  (nothing matched)")
    for h in hits:
        m = h["metadata"]
        was = f" was #{h['retrieve_rank']}" if h.get("retrieve_rank") else ""
        extra = f" rerank={h['rerank_score']:.4f}" if h.get("rerank_score") is not None else ""
        print(
            f"  {h['rank']}. [{h['chunk_id']}] {m['recipe_id']} {m['section']:<12} "
            f"score={h['score']:.4f}{extra}{was}  {' '.join(h['text'].split())[:80]!r}"
        )


if __name__ == "__main__":
    main()
