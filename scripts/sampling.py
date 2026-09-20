"""sampling.py — the only place a trace sample is ever drawn.

Every deliverable (open coding, taxonomy, replay, prediction check) imports its
sample from here, so the seed printed in notes.md is provably the seed that
produced the rows in taxonomy.md.

Draws are pure functions of (trace file, seed, size). Nothing is filtered,
sorted or curated before the random draw.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACES_FILE = ROOT / "traces" / "traces.jsonl"

# ── the seeded random sample: the 20 traces that produce the taxonomy ─────────
RANDOM_SAMPLE_SEED = 42
RANDOM_SAMPLE_SIZE = 20

# ── the curated demo sample (bonus): the questions shown at reviews ──────────
# The original 8 known-answer questions (Q1–Q8 in eval/questions.py), written up
# results.md and demoed at every review, mapped onto the ids they carry in the
# question bank. Sampling from these is deliberately NOT random over production:
# that is the whole point of the comparison.
DEMO_QIDS = {
    "R001-cream",       # Q1
    "R005-paste",       # Q2
    "R002-chickpeas",   # Q3
    "R003-kcal",        # Q4
    "R003-preheat",     # Q5
    "R001-vegan-sub",   # Q6
    "R006-sauce-simmer",  # Q7
    "AMB-paste",        # Q8
}
DEMO_SAMPLE_SEED = 4242
DEMO_SAMPLE_SIZE = 10


def qid_of(trace: dict) -> str | None:
    return (trace.get("question_meta") or {}).get("qid")


def load_traces(path: Path = TRACES_FILE, include_failed_calls: bool = False) -> list[dict]:
    """The sampling population.

    The one exclusion is records where the API call itself failed — a 401 during
    a key rotation, a dropped connection, or the daily token limit. Those hold no
    model output to read, so they are not traces of the app behaving, and they are
    counted in notes.md rather than silently dropped. No other filter is applied:
    nothing is excluded for looking boring, correct, or already understood.
    """
    with path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if include_failed_calls:
        return rows
    return [r for r in rows if not r.get("error")]


def population_fingerprint(path: Path = TRACES_FILE) -> dict:
    """A seed only reproduces a sample against the same file. The fingerprint
    pins which file state the 20 traces were drawn from."""
    raw = path.read_bytes()
    return {
        "file": path.name,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "records_in_file": len(load_traces(path, include_failed_calls=True)),
        "population": len(load_traces(path)),
    }


def population_report(path: Path = TRACES_FILE) -> dict:
    rows = load_traces(path, include_failed_calls=True)
    failed = [r for r in rows if r.get("error")]
    kinds: dict[str, int] = {}
    for r in failed:
        kind = r["error"].split(":")[0]
        kinds[kind] = kinds.get(kind, 0) + 1
    return {
        "records_in_file": len(rows),
        "failed_calls_excluded": len(failed),
        "failed_call_kinds": kinds,
        "population": len(rows) - len(failed),
    }


def draw_random_sample(
    traces: list[dict],
    n: int = RANDOM_SAMPLE_SIZE,
    seed: int = RANDOM_SAMPLE_SEED,
) -> list[dict]:
    """random.Random(seed).sample over the whole trace file, unfiltered."""
    return random.Random(seed).sample(traces, n)


def draw_demo_sample(
    traces: list[dict],
    n: int = DEMO_SAMPLE_SIZE,
    seed: int = DEMO_SAMPLE_SEED,
    exclude_random_sample: bool = True,
) -> list[dict]:
    """Sample from the curated demo questions only, disjoint from the random 20."""
    drawn_ids = {t["trace_id"] for t in draw_random_sample(traces)} if exclude_random_sample else set()
    pool = [
        t for t in traces if qid_of(t) in DEMO_QIDS and t["trace_id"] not in drawn_ids
    ]
    return random.Random(seed).sample(pool, n)


def by_id(traces: list[dict], trace_id_prefix: str) -> dict:
    for t in traces:
        if t["trace_id"].startswith(trace_id_prefix):
            return t
    raise KeyError(f"no trace starting with {trace_id_prefix!r}")
