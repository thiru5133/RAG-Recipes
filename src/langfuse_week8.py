"""Send the saved week-8 runs to Langfuse (no API calls to the model).

One trace per request per phase. Each tool call in the trajectory is a child
span; a call the sandbox blocked shows as an ERROR span. Scores are attached
to the trace: outcome_pass, trajectory_pass, gap, tricked.

Sessions: week8-baseline, week8-after, week8-attack, week8-defended.
Missing keys skip the export; the eval still prints.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from config import ROOT

load_dotenv(ROOT / ".env")

WEEK8 = ROOT / "eval" / "week8"


def langfuse_enabled() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))


def _load(name: str) -> list[dict]:
    path = WEEK8 / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _phase_rows() -> list[tuple[str, dict]]:
    rows = [("week8-baseline", r) for r in _load("baseline_full.json")]
    rows += [("week8-after", r) for r in _load("after_full.json")]
    for r in _load("injection.json"):
        rows.append(("week8-defended" if r.get("defended") else "week8-attack", r))
    return rows


def export_week8() -> str:
    if not langfuse_enabled():
        return "Langfuse: skipped (set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env)"
    try:
        from langfuse import get_client, propagate_attributes
    except ImportError:
        return "Langfuse: package missing. pip install -r requirements.txt"
    if not os.environ.get("LANGFUSE_BASE_URL") and os.environ.get("LANGFUSE_HOST"):
        os.environ["LANGFUSE_BASE_URL"] = os.environ["LANGFUSE_HOST"]

    sent = 0
    try:
        client = get_client()
        for session, row in _phase_rows():
            _one(client, propagate_attributes, session, row)
            sent += 1
        client.flush()
    except Exception as exc:
        return f"Langfuse: export failed after {sent} traces ({type(exc).__name__}: {exc})"
    return (
        f"Langfuse: sent {sent} week-8 traces. Filter Sessions week8-baseline / week8-after / "
        "week8-attack / week8-defended."
    )


def _one(client, propagate_attributes, session: str, row: dict) -> None:
    rid = row["id"]
    tags = [rid, row.get("class") or "", *(row.get("failure_modes") or [])]
    tags = [t for t in tags if t]
    with propagate_attributes(session_id=session, tags=tags):
        with client.start_as_current_observation(
            as_type="span",
            name=f"{session}:{rid}",
            input={"id": rid, "expected": row.get("expected"), "notes": row.get("notes")},
            metadata={
                "stopped_by": row.get("stopped_by"),
                "laps": row.get("laps"),
                "tokens": row.get("tokens"),
                "cost_usd": row.get("cost_usd"),
                "latency_ms": row.get("latency_ms"),
                "failure_modes": row.get("failure_modes"),
            },
        ) as root:
            for step in row.get("trajectory_raw") or []:
                err = step.get("error")
                with client.start_as_current_observation(
                    as_type="tool",
                    name=step.get("tool", "unknown"),
                    input=step.get("args"),
                    level="ERROR" if err else "DEFAULT",
                    status_message=str(err) if err else None,
                    metadata={"lap": step.get("lap")},
                ) as tool:
                    tool.update(output={"error": err} if err else "ok")
            root.update(output=row.get("result"))
            for name in ("outcome_pass", "trajectory_pass", "gap", "tricked"):
                if row.get(name) is None:
                    continue
                client.score_current_trace(name=name, value=1.0 if row[name] else 0.0, data_type="NUMERIC")
