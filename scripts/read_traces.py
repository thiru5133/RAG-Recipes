"""read_traces.py — the tool used to READ traces by hand during open coding.

Prints one sampled trace per screen block with every field that matters for
reading: question, all retrieved chunks with scores, raw output, refusal flag
and reason, citations, and the run config. It changes nothing and writes
nothing, which is the point: the open-coding step applies zero fixes.

    python scripts/read_traces.py                # the seeded random sample of 20
    python scripts/read_traces.py --set demo     # the curated demo sample of 10
    python scripts/read_traces.py --id fc9c535e  # one trace by id prefix
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from sampling import (  # noqa: E402
    DEMO_QIDS,
    DEMO_SAMPLE_SEED,
    DEMO_SAMPLE_SIZE,
    RANDOM_SAMPLE_SEED,
    RANDOM_SAMPLE_SIZE,
    draw_demo_sample,
    draw_random_sample,
    load_traces,
    qid_of,
)


def show(trace: dict, label: str = "") -> None:
    meta = trace.get("question_meta") or {}
    print("=" * 100)
    print(f"{label}{trace['trace_id']}   [{qid_of(trace)}]  {trace['timestamp']}")
    print(f"Q: {trace['question']}")
    if meta:
        print(
            f"class={meta.get('class')}  gold={meta.get('gold_answer') or meta.get('why_unanswerable')}"
            f"  gold_section={meta.get('gold_section')}"
        )
    print(
        f"config: strategy={trace.get('strategy')} mode={trace.get('mode')} "
        f"k={trace.get('k')} threshold={trace.get('threshold')} "
        f"prompt={trace.get('prompt_version')} model={trace.get('model')} "
        f"params={trace.get('model_params')}"
    )
    print("retrieved:")
    for c in trace.get("retrieved_chunks", []):
        print(
            f"   {c['rank']}. {c['chunk_id']:<10} {c.get('recipe_id')}  "
            f"{str(c.get('section')):<12} {c['score']:.4f}"
        )
    print(f"output : {trace['raw_output']}")
    print(
        f"refused: {trace.get('refused')}  by={trace.get('refused_by')}  "
        f"citations={[(c['chunk_id'], c['recipe_id']) for c in trace.get('citations', [])]}  "
        f"citation_check={trace.get('citation_check')}"
    )
    if trace.get("error"):
        print(f"error  : {trace['error']}")
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["random", "demo"], default="random")
    ap.add_argument("--id", default=None, help="show a single trace by trace_id prefix")
    args = ap.parse_args()

    traces = load_traces()

    if args.id:
        for t in traces:
            if t["trace_id"].startswith(args.id):
                show(t)
        return

    if args.set == "random":
        sample = draw_random_sample(traces)
        print(
            f"RANDOM SAMPLE — seed={RANDOM_SAMPLE_SEED}, n={RANDOM_SAMPLE_SIZE}, "
            f"population={len(traces)} traces\n"
        )
        prefix = "T"
    else:
        sample = draw_demo_sample(traces)
        print(
            f"DEMO SAMPLE — seed={DEMO_SAMPLE_SEED}, n={DEMO_SAMPLE_SIZE}, "
            f"restricted to demo question ids {sorted(DEMO_QIDS)}, "
            f"disjoint from the random 20\n"
        )
        prefix = "D"

    for i, t in enumerate(sample, 1):
        show(t, label=f"{prefix}{i:02d}  ")


if __name__ == "__main__":
    main()
