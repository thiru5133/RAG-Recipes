"""verify_prediction.py — settles the prediction filed in notes.md section 5.

The prediction was: after the refusal gate stops comparing RRF scores against a
cosine threshold, hybrid-mode traces refused at the score gate go from 6/20 (30%)
to 0/20, and refusals of answerable questions go from 7/20 (35%) to under 3/20.

This counts both numbers on a fresh seed-43 draw and prints whether each holds.
It takes no argument that could soften the test: the seed, the sample size and
the two thresholds are constants, and the only input is the trace file.

    python scripts/verify_prediction.py                       # after the fix
    python scripts/verify_prediction.py --baseline            # the seed-42 sample it was filed against
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from sampling import (  # noqa: E402
    RANDOM_SAMPLE_SIZE,
    TRACES_FILE,
    draw_random_sample,
    load_traces,
)

VERIFY_SEED = 43

# The two claims, exactly as filed.
CLAIM_HYBRID_GATE_REFUSALS = 0        # must be exactly this
CLAIM_ANSWERABLE_REFUSALS_UNDER = 3   # must be strictly below this


def draw(traces: list[dict], seed: int, n: int) -> list[dict]:
    if len(traces) < n:
        raise SystemExit(f"only {len(traces)} traces; need {n}")
    return random.Random(seed).sample(traces, n)


def count(sample: list[dict]) -> dict:
    hybrid_gate = [
        t for t in sample
        if t["mode"] == "hybrid" and t.get("refused_by") == "score_threshold"
    ]
    answerable_refused = [
        t for t in sample
        if t["refused"] and (t.get("question_meta") or {}).get("class") == "answerable"
    ]
    return {
        "n": len(sample),
        "hybrid_traces": len([t for t in sample if t["mode"] == "hybrid"]),
        "hybrid_gate_refusals": len(hybrid_gate),
        "answerable_refusals": len(answerable_refused),
        "hybrid_gate_ids": [t["trace_id"][:8] for t in hybrid_gate],
        "answerable_refused_ids": [t["trace_id"][:8] for t in answerable_refused],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", type=Path, default=TRACES_FILE)
    ap.add_argument(
        "--baseline",
        action="store_true",
        help="count the seed-42 sample the prediction was filed against",
    )
    args = ap.parse_args()

    traces = load_traces(args.traces)
    if args.baseline:
        sample, label = draw_random_sample(traces), "baseline (seed 42, as filed)"
    else:
        sample, label = draw(traces, VERIFY_SEED, RANDOM_SAMPLE_SIZE), f"seed {VERIFY_SEED}"

    c = count(sample)
    print(f"{label} — {c['n']} traces, {c['hybrid_traces']} of them hybrid\n")
    print(f"hybrid traces refused at the score gate : {c['hybrid_gate_refusals']} "
          f"{c['hybrid_gate_ids']}")
    print(f"answerable questions refused            : {c['answerable_refusals']} "
          f"{c['answerable_refused_ids']}")

    if args.baseline:
        return

    print()
    first = c["hybrid_gate_refusals"] == CLAIM_HYBRID_GATE_REFUSALS
    second = c["answerable_refusals"] < CLAIM_ANSWERABLE_REFUSALS_UNDER
    print(f"claim 1, hybrid gate refusals == {CLAIM_HYBRID_GATE_REFUSALS}        : "
          f"{'HELD' if first else 'FAILED'}")
    print(f"claim 2, answerable refusals < {CLAIM_ANSWERABLE_REFUSALS_UNDER}          : "
          f"{'HELD' if second else 'FAILED'}")
    print(f"\nprediction: {'HELD' if first and second else 'WRONG'}")


if __name__ == "__main__":
    main()
