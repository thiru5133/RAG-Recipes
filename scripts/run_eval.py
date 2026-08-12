"""Search-only evaluation: all 8 questions against both strategies, no LLM."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from config import RESULTS_DIR, STRATEGIES, TOP_K  # noqa: E402
from eval.questions import QUESTIONS, TABLE_QIDS  # noqa: E402
from evaluate import answers_at, evaluate_strategy, hits_at  # noqa: E402
from store import get_collection  # noqa: E402


def run(k: int = TOP_K):
    out = {}
    for strategy, collection_name in STRATEGIES.items():
        coll = get_collection(collection_name)
        out[strategy] = evaluate_strategy(coll, QUESTIONS, k=k)
    return out


def main():
    results = run()
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "search_only.json").write_text(json.dumps(results, indent=2))

    for strategy, res in results.items():
        pq = res["per_question"]
        print(f"\n=== {strategy} ===")
        for r in pq:
            rank = r["first_hit_rank"]
            ans = r["first_answer_rank"]
            print(f"  {r['qid']} ({r['type']:9}) hit@5={'Y' if r['hit'] else 'N'} "
                  f"rank={rank if rank else '-':<3} answer_rank={ans if ans else '-'}")
        print(f"  Hit-in-Top-5 : {res['hits']}/{res['total']}")
        print(f"  Hit-in-Top-3 : {hits_at(pq, 3)}/{res['total']}")
        print(f"  Answer-in-Top-5: {res['answers']}/{res['total']}")
        print(f"  Table questions Hit@5: {hits_at(pq, 5, TABLE_QIDS)}/{len(TABLE_QIDS)}"
              f"  Answer@5: {answers_at(pq, 5, TABLE_QIDS)}/{len(TABLE_QIDS)}")

    print(f"\nWrote {RESULTS_DIR / 'search_only.json'}")


if __name__ == "__main__":
    main()
