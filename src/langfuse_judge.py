"""Send the week-6 judge rows to Langfuse.

One generation per case, per prompt version. The human label is a numeric
score named human_agreement (1 = same verdict, 0 = not). Missing keys skip
the export; the eval still prints.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

from dotenv import load_dotenv

from config import GROQ_MODEL, ROOT
from judge import build_user_prompt, load_prompt

load_dotenv(ROOT / ".env")


def langfuse_enabled() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))


def _client():
    if not os.environ.get("LANGFUSE_BASE_URL") and os.environ.get("LANGFUSE_HOST"):
        os.environ["LANGFUSE_BASE_URL"] = os.environ["LANGFUSE_HOST"]
    from langfuse import get_client

    return get_client()


def export_week6(
    items: list[dict],
    labels: dict,
    v1: Optional[dict],
    v2: Optional[dict],
) -> str:
    """Upload cached or fresh judge results. Returns one status line."""
    if not langfuse_enabled():
        return (
            "Langfuse: skipped (set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env, "
            "then run python scripts/run_week6.py again)"
        )
    try:
        from langfuse import propagate_attributes
    except ImportError:
        return "Langfuse: keys are set but the package is missing. pip install -r requirements.txt"

    human = {row["qid"]: (row.get("human") or "").upper() for row in labels.get("labels", [])}
    by_qid = {it["qid"]: it for it in items}
    try:
        client = _client()
    except Exception as exc:
        return f"Langfuse: client failed ({type(exc).__name__}: {exc})"

    sent = 0
    try:
        for version, bundle in (("v1", v1), ("v2", v2)):
            if not bundle:
                continue
            prompt = load_prompt(version)
            for row in bundle.get("per") or []:
                _one(client, propagate_attributes, version, prompt, by_qid, human, row)
                sent += 1
        client.flush()
    except Exception as exc:
        return f"Langfuse: export failed after {sent} rows ({type(exc).__name__}: {exc})"
    return (
        f"Langfuse: sent {sent} judge traces. "
        "In the project, filter session week6-judge and tags judge-v1 / judge-v2. "
        "Score human_agreement is 0 on S05 and S19 for v1, and 1 for v2."
    )


def _one(client, propagate_attributes, version: str, prompt: str, by_qid: Dict, human: Dict, row: dict) -> None:
    qid = row["qid"]
    item = by_qid.get(qid) or {"qid": qid}
    verdict = (row.get("verdict") or "").upper()
    label = human.get(qid) or ""
    agrees = bool(label) and verdict == label
    raw = row.get("raw") or row.get("error") or ""
    with propagate_attributes(session_id="week6-judge", tags=[f"judge-{version}", qid]):
        with client.start_as_current_observation(
            as_type="generation",
            name=f"judge-{version}",
            model=os.environ.get("GROQ_MODEL", GROQ_MODEL),
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": build_user_prompt(item)},
            ],
            metadata={
                "prompt_version": version,
                "qid": qid,
                "human": label,
                "verdict": verdict or "UNPARSED",
                "latency_ms": row.get("latency_ms"),
            },
        ) as generation:
            generation.update(output=raw)
            client.score_current_span(
                name="human_agreement",
                value=1.0 if agrees else 0.0,
                data_type="NUMERIC",
                comment=f"human={label or 'missing'} judge={verdict or 'UNPARSED'}",
            )
