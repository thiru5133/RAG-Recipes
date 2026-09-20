"""replay_trace.py — replay one trace from the trace alone.

Replay means: take nothing but the JSON record, rebuild both prompts, send them
to the same model with the same parameters, and put the new output next to the
one the trace recorded.

Three things are checked and reported:

1. the system prompt rebuilt from `prompt_version` hashes to the recorded sha256
2. the user prompt rebuilt from the recorded chunk text hashes to its sha256
3. the refusal gate, replayed from `top_score` and `threshold`, reaches the same
   verdict as the trace

Anything the record cannot supply is listed as a missing field rather than
guessed.

    python scripts/replay_trace.py
    python scripts/replay_trace.py --trace-id 1a2b3c4d
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from generate import (  # noqa: E402
    build_user_prompt,
    complete,
    sha256,
    system_prompt_for,
)
from guardrails import below_threshold, validate_citations  # noqa: E402
from sampling import by_id, draw_random_sample, load_traces  # noqa: E402

# Which of the 20 sampled traces gets replayed is itself a seeded draw, so it is
# not a trace picked because it looked interesting.
REPLAY_PICK_SEED = 11

EVIDENCE_FILE = ROOT / "results" / "replay_evidence.json"
OPTIONAL_FIELDS = ["finish_reason", "usage"]

# Every field a replay needs. Anything absent or null here cannot be replayed.
REQUIRED_FIELDS = [
    "question",
    "prompt_version",
    "system_prompt_sha256",
    "user_prompt_sha256",
    "model",
    "model_params",
    "strategy",
    "mode",
    "k",
    "threshold",
    "top_score",
    "retrieved_chunks",
    "raw_output",
]


def missing_fields(trace: dict) -> list[str]:
    missing = [f for f in REQUIRED_FIELDS if trace.get(f) in (None, [], {})]
    chunks = trace.get("retrieved_chunks") or []
    if chunks and any(not c.get("text") for c in chunks):
        missing.append("retrieved_chunks[].text")
    if chunks and any(c.get("score") is None for c in chunks):
        missing.append("retrieved_chunks[].score")
    return missing


def hits_from_trace(trace: dict) -> list[dict]:
    """Rebuild the hit dicts the generator was given, from the trace alone."""
    return [
        {
            "rank": c["rank"],
            "chunk_id": c["chunk_id"],
            "text": c["text"],
            "score": c["score"],
            "metadata": {
                "recipe_id": c.get("recipe_id"),
                "recipe_title": c.get("recipe_title"),
                "section": c.get("section"),
                "chunk_type": c.get("chunk_type"),
            },
        }
        for c in trace["retrieved_chunks"]
    ]


def replay(trace: dict, call_model: bool = True) -> dict:
    gaps = missing_fields(trace)

    system_prompt = system_prompt_for(trace["prompt_version"])
    system_ok = sha256(system_prompt) == trace.get("system_prompt_sha256")

    hits = hits_from_trace(trace)
    user_prompt = build_user_prompt(trace["question"], hits)
    user_ok = sha256(user_prompt) == trace.get("user_prompt_sha256")

    gate_refuses = below_threshold(hits, trace["threshold"])
    gate_ok = gate_refuses == (trace.get("refused_by") == "score_threshold")

    replayed = {"answer": None, "error": "model call skipped", "latency_ms": None}
    if call_model and not gate_refuses:
        params = trace.get("model_params") or {}
        replayed = complete(
            system_prompt,
            user_prompt,
            model=trace["model"],
            temperature=params.get("temperature", 0),
            max_tokens=params.get("max_tokens", 400),
        )
    elif gate_refuses:
        replayed = {
            "answer": "I cannot answer that from the provided recipe cards.",
            "error": None,
            "latency_ms": 0,
        }

    citation_check = (
        validate_citations(replayed["answer"], hits) if replayed["answer"] else None
    )

    return {
        "trace_id": trace["trace_id"],
        "question": trace["question"],
        "prompt_version": trace["prompt_version"],
        "model": trace["model"],
        "model_params": trace.get("model_params"),
        "strategy": trace.get("strategy"),
        "mode": trace.get("mode"),
        "k": trace.get("k"),
        "threshold": trace.get("threshold"),
        "top_score": trace.get("top_score"),
        "retrieved": [
            {
                "rank": c["rank"],
                "chunk_id": c["chunk_id"],
                "recipe_id": c.get("recipe_id"),
                "section": c.get("section"),
                "score": c["score"],
                "text_chars": len(c.get("text") or ""),
            }
            for c in trace["retrieved_chunks"]
        ],
        "system_prompt_sha256_matches": system_ok,
        "user_prompt_sha256_matches": user_ok,
        "user_prompt_rebuilt": user_prompt,
        "gate_replayed_refuses": gate_refuses,
        "gate_verdict_matches": gate_ok,
        "original_output": trace.get("raw_output"),
        "replayed_output": replayed["answer"],
        "outputs_identical": replayed["answer"] == trace.get("raw_output"),
        "replay_error": replayed["error"],
        "replayed_citation_check": citation_check,
        "missing_fields": gaps,
        "optional_fields_absent": [f for f in OPTIONAL_FIELDS if trace.get(f) is None],
    }


def print_report(r: dict) -> None:
    print("=" * 100)
    print(f"REPLAY  {r['trace_id']}")
    print(f"Q: {r['question']}")
    print(
        f"config: strategy={r['strategy']} mode={r['mode']} k={r['k']} "
        f"threshold={r['threshold']} top_score={r['top_score']}"
    )
    print(f"model : {r['model']} {r['model_params']} prompt={r['prompt_version']}")
    print()
    print(f"system prompt sha256 rebuilt from version : {r['system_prompt_sha256_matches']}")
    print(f"user prompt sha256 rebuilt from chunk text: {r['user_prompt_sha256_matches']}")
    print(f"refusal gate replayed to same verdict     : {r['gate_verdict_matches']}")
    print(f"missing fields                            : {r['missing_fields'] or 'none'}")
    print(f"fields added to the logger afterwards     : {r['optional_fields_absent'] or 'none'}")
    print()
    print("--- original output ---")
    print(r["original_output"])
    print("--- replayed output ---")
    print(r["replayed_output"])
    print(f"--- identical: {r['outputs_identical']} ---")
    if r["replay_error"]:
        print(f"replay error: {r['replay_error']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace-id", default=None)
    ap.add_argument("--no-model", action="store_true", help="skip the model call")
    ap.add_argument("--out", type=Path, default=EVIDENCE_FILE)
    args = ap.parse_args()

    traces = load_traces()
    if args.trace_id:
        trace = by_id(traces, args.trace_id)
    else:
        sample = draw_random_sample(traces)
        trace = random.Random(REPLAY_PICK_SEED).choice(sample)
        print(
            f"picked by random.Random({REPLAY_PICK_SEED}).choice(seeded sample of "
            f"{len(sample)})\n"
        )

    report = replay(trace, call_model=not args.no_model)
    print_report(report)

    out = args.out if args.out.is_absolute() else (ROOT / args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nevidence -> {out}")


if __name__ == "__main__":
    main()
