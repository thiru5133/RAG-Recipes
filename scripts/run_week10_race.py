"""Week 10 race: single MCP agent vs the kitchen squad on the SAME 10 Week-6 cases
(S01-S10: the first ten frozen cases, all distinct, none regression fixtures), scored by the
SAME Week-6 pipeline: the five assertions AND judge v2 (pass = both).

    python scripts/run_week10_race.py            # race + failure injection
    python scripts/run_week10_race.py --only race|failure
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent.mcp_agent import McpHost, run_mcp_agent  # noqa: E402
from assertions import run_assertions  # noqa: E402
from config import GROQ_PRICES, WEEK7_MODEL  # noqa: E402
from judge import judge_one, load_prompt  # noqa: E402
from multi.orchestrator import run_orchestrator  # noqa: E402

OUT = ROOT / "eval" / "week10"
CFG = ROOT / "config" / "mcp_servers.json"       # both servers, as in Week 9
CASES = json.loads((ROOT / "eval" / "week6" / "substitutions.json").read_text())["items"][:10]
FAIL_CASE = "S01"

FORMAT_SPEC = """Output ONLY the substitution in exactly this plain-text format (no markdown, no commentary):
CONSTRAINT: <constraint>
RECIPE: <title> (<recipe_id>)
SERVINGS: <int>
ALLERGEN_WARNING: contains-<allergen> for each of nuts, dairy, gluten, fish, shellfish, egg, meat present in the final ingredient list, separated by '; ' (or 'none')
INGREDIENTS:
- <name> | <quantity number> | <unit> | <note>
METHOD:
1. <step>
OVEN: <temperature with unit, or none>
If the card says the constraint cannot be met, say so in ALLERGEN_WARNING and keep the original ingredients."""


def task_text(item: dict) -> str:
    return f"{item['request']}\nConstraint: {item['constraint']}\nServings: {item['servings_expected']}"


def score(item: dict, text: str, prompt: str) -> dict:
    a = run_assertions(text, item.get("servings_expected"))
    j = judge_one({**item, "substitution": text}, prompt)
    return {"assertions": a["passed"], "verdict": j["verdict"], "judge_raw": (j.get("raw") or "")[-300:],
            "pass": bool(a["passed"] and j["verdict"] == "PASS")}


def run_race() -> None:
    prompt = load_prompt("v2")
    rows, log = [], []
    for item in CASES:
        qid = item["qid"]
        # --- single agent (Week 9 agent, unchanged, both servers) ---
        host = McpHost(CFG).connect()
        try:
            s = run_mcp_agent(task_text(item) + "\n\n" + FORMAT_SPEC, host=host)
        finally:
            host.close()
        sc = score(item, s["answer"], prompt)
        rows.append({"qid": qid, "arm": "single", "tokens": s["tokens"], "cost_usd": s["cost_usd"],
                     "latency_ms": s["latency_ms"], "laps": s["laps"], "stopped_by": s["stopped_by"],
                     "tools": [t.get("tool") for t in s["trace"] if "tool" in t], "answer": s["answer"], **sc})
        print(f"{qid} single  pass={sc['pass']} tokens={s['tokens']} ms={s['latency_ms']}", flush=True)
        # --- orchestrator ---
        host = McpHost(CFG).connect()
        try:
            o = run_orchestrator(task_text(item), FORMAT_SPEC, host)
        finally:
            host.close()
        sc = score(item, o["answer"], prompt)
        rows.append({"qid": qid, "arm": "multi", "tokens": o["tokens"], "cost_usd": o["cost_usd"],
                     "latency_ms": o["latency_ms"], "by_handoff": o["by_handoff"], "events": o["events"],
                     "answer": o["answer"], **sc})
        for h in o["handoffs"]:
            log.append(f"{qid} | {h['handoff']} | in={h['prompt_tokens']} out={h['completion_tokens']} ms={h['ms']}")
        print(f"{qid} multi   pass={sc['pass']} tokens={o['tokens']} ms={o['latency_ms']}", flush=True)
    (OUT / "race_runs.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "handoffs.log").write_text("\n".join(log) + "\n", encoding="utf-8")


def run_failure() -> None:
    item = next(c for c in CASES if c["qid"] == FAIL_CASE)
    prompt = load_prompt("v2")
    host = McpHost(CFG).connect()
    try:
        o = run_orchestrator(task_text(item), FORMAT_SPEC, host, inject_500_on_allergen=True)
    finally:
        host.close()
    sc = score(item, o["answer"], prompt)
    (OUT / "failure_run.json").write_text(json.dumps({"qid": FAIL_CASE, **o, **sc}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: o[k] for k in ("events", "allergen_failure", "tokens")}, indent=1))
    print(o["answer"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["race", "failure"])
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.only in (None, "race"):
        run_race()
    if a.only in (None, "failure"):
        run_failure()
