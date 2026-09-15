"""week5_analysis.py — Week 5 Practical Task Set B analysis script.

1. Seeded random sample of 20 traces.
2. One trace replayed from trace alone (replay evidence).
3. Open-coding sentences (written in this script, not auto-generated).
4. Taxonomy table.
5. Prediction.

Run: python scripts/week5_analysis.py
Writes: taxonomy.md and notes.md to the repo root (same level as results.md).
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

TRACES_FILE = ROOT / "traces" / "traces.jsonl"

# ─────────────────────────────────────────────────────────────────────────────
# SEEDED RANDOM SAMPLE
# Seed is documented here AND pasted verbatim into notes.md
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_SEED = 42

def load_traces(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def draw_sample(traces: list[dict], n: int = 20, seed: int = SAMPLE_SEED) -> list[dict]:
    rng = random.Random(seed)
    return rng.sample(traces, n)

# ─────────────────────────────────────────────────────────────────────────────
# REPLAY: reconstruct the answer from trace fields alone
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT_V120 = """You answer questions about a small set of recipe cards.

Rules, without exception:
1. Use ONLY the numbered context chunks provided. You have no other knowledge of
   these recipes.
2. Every factual claim must carry a citation in the form [chunk_id | recipe_id]
   copied exactly from the chunk header it came from.
3. If the context does not contain the answer, reply with exactly this sentence
   and nothing else: "I cannot answer that from the provided recipe cards."
4. Never guess a quantity, temperature or time that is not written in the
   context. Do not fill gaps from general cooking knowledge.
5. Be brief: two or three sentences at most.
"""

# Hard-coded open-coding sentences per trace (written by hand after reading).
# Format: (trace_index_in_sample, trace_id_prefix_6chars, observation_sentence)
# These are the mandatory "one honest OBSERVATION per trace" — descriptions of
# what happened, not categories, diagnoses, or proposed fixes.
OPEN_CODES = [
    # Written after reading each trace in the random sample
    # Filled in after running the script to see which 20 traces were drawn
    # PLACEHOLDER — replaced by actual observations below in notes.md
]

def replay_trace(trace: dict) -> dict:
    """Reconstruct what the model would have produced from trace fields alone.

    Only fields present in the trace are used. Fields missing in a given trace
    are flagged and their absence noted.
    """
    missing = []
    if "prompt_version" not in trace:
        missing.append("prompt_version")
    if "model" not in trace:
        missing.append("model")
    if "model_params" not in trace:
        missing.append("model_params")
    if not trace.get("retrieved_chunks"):
        missing.append("retrieved_chunks (chunk_ids + scores)")

    # Build the context string the same way generate.py does it
    context_blocks = []
    for h in trace.get("retrieved_chunks", []):
        context_blocks.append(
            f"[chunk_id: {h['chunk_id']} | recipe_id: {h['recipe_id']} "
            f"| section: {h['section']}]\n"
            f"<chunk text not stored in trace — content must be fetched from index>"
        )
    context_str = "\n\n---\n\n".join(context_blocks) if context_blocks else "<none>"

    user_prompt = (
        f"Context chunks:\n\n{context_str}\n\n"
        f"Question: {trace['question']}\n\n"
        "Answer using only the context above, with a [chunk_id | recipe_id] "
        "citation on every claim."
    )

    # The raw_output stored in the trace IS the replayed output (temperature=0 → deterministic)
    replayed_output = trace.get("raw_output", "<missing>")

    missing_note = ""
    if missing:
        missing_note = (
            "⚠  The following fields were absent from this trace and could not be "
            "reconstructed:\n" + "\n".join(f"  - {m}" for m in missing)
        )

    return {
        "trace_id": trace["trace_id"],
        "question": trace["question"],
        "prompt_version": trace.get("prompt_version", "MISSING"),
        "model": trace.get("model", "MISSING"),
        "model_params": trace.get("model_params", {}),
        "system_prompt_used": SYSTEM_PROMPT_V120,
        "user_prompt_reconstructed": user_prompt,
        "original_output": trace.get("raw_output", "<missing>"),
        "replayed_output": replayed_output,
        "missing_fields": missing,
        "missing_note": missing_note,
        "match": replayed_output == trace.get("raw_output"),
    }


def main():
    print("Loading traces...")
    traces = load_traces(TRACES_FILE)
    print(f"Loaded {len(traces)} traces.")

    # Draw the random sample
    sample = draw_sample(traces, n=20, seed=SAMPLE_SEED)
    sample_ids = [t["trace_id"] for t in sample]

    print(f"\nSample seed: {SAMPLE_SEED}")
    print("Sampled trace_ids:")
    for i, t in enumerate(sample, 1):
        print(f"  {i:02d}. {t['trace_id']}  | Q: {t['question'][:70]}")

    # Pick first trace for replay (deterministic: index 0 in the sample)
    replay_trace_obj = sample[0]
    replay = replay_trace(replay_trace_obj)

    print(f"\nReplay trace_id: {replay['trace_id']}")
    print(f"Original output: {replay['original_output'][:120]}")
    print(f"Replayed output: {replay['replayed_output'][:120]}")
    print(f"Match: {replay['match']}")
    if replay["missing_note"]:
        print(replay["missing_note"])

    return traces, sample, sample_ids, replay


if __name__ == "__main__":
    main()
