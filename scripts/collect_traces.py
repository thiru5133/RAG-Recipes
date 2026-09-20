"""collect_traces.py — run the real pipeline and log real traces.

Every trace in traces/traces.jsonl comes from this script or from the UI: a real
question goes through real retrieval and a real model call, and whatever the
model said is written down unedited. Nothing here decides in advance what a
failure looks like.

Variety comes from the question bank (each question is asked in several
phrasings, the way a cook would actually type it) crossed with the retrieval
configurations the app really ships: both chunking strategies, all three search
modes, and k of 3 or 5. Pairs are drawn without replacement under a fixed seed.

    python scripts/collect_traces.py --n 400
    python scripts/collect_traces.py --n 50 --resume     # top up an existing log

Groq free tier is rate limited, so calls are throttled and 429s back off. The
log is appended after every call, so an interrupted run keeps everything it got.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from config import REFUSAL_THRESHOLD  # noqa: E402
from eval.question_bank import QUESTION_BANK  # noqa: E402
from tracing import TRACES_FILE, answer_and_trace  # noqa: E402

COLLECTION_SEED = 20260916

STRATEGIES = ["structured", "basic"]
MODES = ["semantic", "hybrid", "bm25"]
KS = [5, 3]


def build_plan(n: int, seed: int = COLLECTION_SEED) -> list[dict]:
    """Every (question phrasing x strategy x mode x k) pair, shuffled, cut to n."""
    plan = [
        {
            "question": phrasing,
            "question_meta": {
                "qid": entry["qid"],
                "class": entry["class"],
                "gold_recipes": entry.get("gold_recipes", []),
                "gold_section": entry.get("gold_section"),
                "gold_answer": entry.get("gold_answer"),
                "why_unanswerable": entry.get("why_unanswerable"),
                "phrasing_index": i,
            },
            "strategy": strategy,
            "mode": mode,
            "k": k,
        }
        for entry in QUESTION_BANK
        for i, phrasing in enumerate(entry["phrasings"])
        for strategy in STRATEGIES
        for mode in MODES
        for k in KS
    ]
    random.Random(seed).shuffle(plan)
    return plan[:n]


def already_logged(path: Path) -> set[tuple]:
    if not path.exists():
        return set()
    done = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            done.add((t["question"], t.get("strategy"), t.get("mode"), t.get("k")))
    return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400, help="how many traces to collect")
    ap.add_argument("--rpm", type=float, default=25.0, help="max model calls per minute")
    ap.add_argument("--resume", action="store_true", help="skip pairs already in the log")
    ap.add_argument("--out", type=Path, default=TRACES_FILE)
    args = ap.parse_args()

    plan = build_plan(args.n if not args.resume else args.n * 4)
    done = already_logged(args.out) if args.resume else set()
    plan = [
        p
        for p in plan
        if (p["question"], p["strategy"], p["mode"], p["k"]) not in done
    ][: args.n]

    print(
        f"collection seed={COLLECTION_SEED}  planned={len(plan)}  "
        f"already logged={len(done)}  out={args.out}"
    )

    min_gap = 60.0 / args.rpm
    written = failures = 0
    for i, step in enumerate(plan, 1):
        started = time.perf_counter()
        try:
            result, trace = answer_and_trace(
                step["question"],
                strategy=step["strategy"],
                mode=step["mode"],
                k=step["k"],
                threshold=REFUSAL_THRESHOLD,
                question_meta=step["question_meta"] | {"source": "collect_traces"},
                path=args.out,
            )
        except Exception as exc:
            failures += 1
            print(f"  {i:4d}/{len(plan)}  EXCEPTION {type(exc).__name__}: {exc}")
            time.sleep(5)
            continue

        written += 1
        err = trace.get("error")
        if err:
            failures += 1
            print(f"  {i:4d}/{len(plan)}  error: {err[:120]}")
            # Rate limits are the common case; give the bucket time to refill.
            if "429" in err or "rate" in err.lower():
                time.sleep(20)
        else:
            flag = "refused" if trace["refused"] else "answered"
            print(
                f"  {i:4d}/{len(plan)}  {step['strategy'][:6]:<6} {step['mode'][:8]:<8} "
                f"k={step['k']}  {flag:<8} {step['question'][:58]}"
            )

        elapsed = time.perf_counter() - started
        if elapsed < min_gap and i < len(plan):
            time.sleep(min_gap - elapsed)

    print(f"\nwrote {written} traces ({failures} with errors) -> {args.out}")


if __name__ == "__main__":
    main()
