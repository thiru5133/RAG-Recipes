"""Trace logging: one JSON object per answered question, appended to traces/traces.jsonl."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import GROQ_MODEL, REFUSAL_THRESHOLD, TOP_K
from generate import PROMPT_VERSION, SYSTEM_PROMPT, sha256
from guardrails import answer_question
from retrieve import dietary_filter, search

ROOT = Path(__file__).resolve().parent.parent
TRACES_FILE = Path(os.environ.get("TRACES_FILE", ROOT / "traces" / "traces.jsonl"))

TRACE_SCHEMA_VERSION = 2


def _chunk_record(hit: Dict) -> Dict:
    meta = hit.get("metadata") or {}
    record = {
        "rank": hit["rank"],
        "chunk_id": hit["chunk_id"],
        "recipe_id": meta.get("recipe_id"),
        "recipe_title": meta.get("recipe_title"),
        "section": meta.get("section"),
        "chunk_type": meta.get("chunk_type"),
        "score": hit["score"],
        "text": hit["text"],
    }
    if "rrf_score" in hit:
        record["rrf_score"] = hit["rrf_score"]
    if "gate_score" in hit:
        record["gate_score"] = hit["gate_score"]
    if "rerank_score" in hit:
        record["rerank_score"] = hit["rerank_score"]
        record["rerank_bm25"] = hit.get("rerank_bm25")
        record["retrieve_rank"] = hit.get("retrieve_rank")
    return record


def build_trace(
    question: str,
    hits: List[Dict],
    result: Dict,
    *,
    strategy: str,
    mode: str,
    k: int,
    threshold: float,
    where: Optional[Dict] = None,
    rerank: bool = False,
    question_meta: Optional[Dict] = None,
) -> Dict:
    gen = result.get("generation") or {}
    citations = result.get("citations") or {}
    return {
        "trace_id": str(uuid.uuid4()),
        "trace_schema_version": TRACE_SCHEMA_VERSION,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "question_meta": question_meta or {},
        "prompt_version": gen.get("prompt_version", PROMPT_VERSION),
        "system_prompt_sha256": gen.get("system_prompt_sha256", sha256(SYSTEM_PROMPT)),
        "user_prompt_sha256": gen.get("user_prompt_sha256"),
        "model": gen.get("model", GROQ_MODEL),
        "model_params": gen.get("model_params"),
        "strategy": strategy,
        "mode": mode,
        "k": k,
        "rerank": rerank,
        "threshold": threshold,
        "where": where,
        "retrieved_chunks": [_chunk_record(h) for h in hits],
        "raw_output": result.get("answer"),
        "finish_reason": gen.get("finish_reason"),
        "usage": gen.get("usage"),
        "refused": result.get("refused"),
        "refused_by": result.get("refused_by"),
        "top_score": result.get("top_score"),
        "citations": [
            {"chunk_id": c[0], "recipe_id": c[1]} for c in citations.get("cited", [])
        ],
        "citation_check": (
            None
            if not citations
            else {
                "unknown_chunk_ids": citations.get("unknown_chunk_ids"),
                "recipe_id_mismatches": citations.get("recipe_id_mismatches"),
                "valid": citations.get("valid"),
            }
        ),
        "latency_ms": gen.get("latency_ms"),
        "error": result.get("error"),
    }


def append_trace(trace: Dict, path: Path = TRACES_FILE) -> Dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace, ensure_ascii=False) + "\n")
    return trace


def answer_and_trace(
    question: str,
    *,
    strategy: str = "structured",
    mode: str = "semantic",
    k: int = TOP_K,
    threshold: float = REFUSAL_THRESHOLD,
    tag: Optional[str] = None,
    rerank: bool = False,
    question_meta: Optional[Dict] = None,
    path: Path = TRACES_FILE,
) -> tuple[Dict, Dict]:
    """Answer one question through the real path and log the trace. Returns
    (result, trace)."""
    where = dietary_filter(tag) if tag else None
    hits = search(question, strategy=strategy, k=k, where=where, mode=mode, rerank=rerank)
    result = answer_question(question, hits, threshold=threshold)
    trace = build_trace(
        question,
        hits,
        result,
        strategy=strategy,
        mode=mode,
        k=k,
        threshold=threshold,
        where=where,
        rerank=rerank,
        question_meta=question_meta,
    )
    append_trace(trace, path=path)
    return result, trace
