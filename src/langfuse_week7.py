"""Send the saved week-7 race rows to Langfuse (no model calls).

One trace per request per system (agent vs workflow).
Sessions: week7-race-agent, week7-race-workflow.
Scores attached: pass, tokens, latency_ms, cost_usd.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from config import ROOT

load_dotenv(ROOT / ".env")

WEEK7 = ROOT / "eval" / "week7"


def langfuse_enabled() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))


def _load_race() -> list[dict]:
    path = WEEK7 / "race.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _load_requests() -> dict:
    try:
        import importlib.util

        req_path = WEEK7 / "requests.py"
        spec = importlib.util.spec_from_file_location("week7_requests", req_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return {r["id"]: r for r in getattr(mod, "REQUESTS", [])}
        return {}
    except Exception:
        return {}


def export_week7() -> str:
    if not langfuse_enabled():
        return "Langfuse: skipped (set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env)"
    try:
        from langfuse import get_client, propagate_attributes
    except ImportError:
        return "Langfuse: package missing. pip install -r requirements.txt"
    if not os.environ.get("LANGFUSE_BASE_URL") and os.environ.get("LANGFUSE_HOST"):
        os.environ["LANGFUSE_BASE_URL"] = os.environ["LANGFUSE_HOST"]

    rows = _load_race()
    if not rows:
        return "Langfuse: no race.csv found in eval/week7"

    req_map = _load_requests()
    sent = 0
    try:
        client = get_client()
        for r in rows:
            sys_name = r.get("system", "unknown")
            session = f"week7-race-{sys_name}"
            rid = r.get("id", "")
            req = req_map.get(rid, {})
            passed = r.get("pass", "").lower() == "true"
            tokens = int(r.get("tokens", 0) or 0)
            latency = int(r.get("latency_ms", 0) or 0)
            cost = float(r.get("cost_usd", 0.0) or 0.0)

            tags = [rid, r.get("class", ""), sys_name]
            tags = [t for t in tags if t]

            with propagate_attributes(session_id=session, tags=tags):
                with client.start_as_current_observation(
                    as_type="span",
                    name=f"week7:{sys_name}:{rid}",
                    input={"id": rid, "request": req.get("text", ""), "class": r.get("class")},
                    metadata={
                        "system": sys_name,
                        "stopped_by": r.get("stopped_by"),
                        "laps": r.get("laps"),
                        "tokens": tokens,
                        "cost_usd": cost,
                        "latency_ms": latency,
                    },
                ) as root:
                    root.update(
                        output={
                            "pass": passed,
                            "stopped_by": r.get("stopped_by"),
                            "laps": r.get("laps"),
                        }
                    )
                    client.score_current_trace(
                        name="pass",
                        value=1.0 if passed else 0.0,
                        data_type="NUMERIC",
                    )
                    client.score_current_trace(
                        name="tokens",
                        value=float(tokens),
                        data_type="NUMERIC",
                    )
            sent += 1
        client.flush()
    except Exception as exc:
        return f"Langfuse: export failed after {sent} traces ({type(exc).__name__}: {exc})"

    return (
        f"Langfuse: sent {sent} week-7 race traces. "
        "Filter Sessions: week7-race-agent / week7-race-workflow."
    )


if __name__ == "__main__":
    print(export_week7())
