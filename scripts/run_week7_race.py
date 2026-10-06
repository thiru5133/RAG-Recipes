"""Race agent vs fixed workflow on the same 10 requests.

    python scripts/run_week7_race.py
    python scripts/run_week7_race.py --budget-demo

Writes eval/week7/race.csv and prints the 8-number table.
--budget-demo runs W07 with max_iters=2 and writes budget_termination.log.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from agent.contract import passes  # noqa: E402
from agent.loop import run_agent  # noqa: E402
from agent.tools import ALLERGEN_SCHEMA, TWO_TOOL_SCHEMAS, THREE_TOOL_SCHEMAS  # noqa: E402
from agent.workflow import run_workflow  # noqa: E402
from eval.week7.requests import REQUESTS  # noqa: E402

WEEK7 = ROOT / "eval" / "week7"


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    n_pass = sum(1 for r in rows if r["pass"])
    lat = sorted(r["latency_ms"] for r in rows)
    p50 = lat[n // 2] if n % 2 else (lat[n // 2 - 1] + lat[n // 2]) / 2
    tokens = sum(r["tokens"] for r in rows)
    cost = sum(r["cost_usd"] for r in rows)
    return {
        "n": n,
        "pass_rate": round(n_pass / n, 3) if n else 0.0,
        "n_pass": n_pass,
        "p50_latency_ms": int(p50) if lat else 0,
        "total_tokens": tokens,
        "cost_per_request_usd": round(cost / n, 6) if n else 0.0,
        "total_cost_usd": round(cost, 6),
    }


def write_tool_diff() -> None:
    WEEK7.mkdir(parents=True, exist_ok=True)
    (WEEK7 / "tools_two.json").write_text(
        json.dumps(TWO_TOOL_SCHEMAS, indent=2) + "\n", encoding="utf-8"
    )
    (WEEK7 / "tools_three.json").write_text(
        json.dumps(THREE_TOOL_SCHEMAS, indent=2) + "\n", encoding="utf-8"
    )
    desc = ALLERGEN_SCHEMA["function"]
    lines = [
        "--- two tools (search_recipes, scale_recipe)",
        "+++ three tools (+ get_allergen_profile)",
        "",
        f"+ name: {desc['name']}",
        f"+ description: {desc['description']}",
        "+ parameters:",
        f"+   recipe_id enum: {desc['parameters']['properties']['recipe_id']['enum']}",
        f"+   allergen enum:  {desc['parameters']['properties']['allergen']['enum']}",
        "",
        "Does not overlap search_recipes (no corpus lookup) or scale_recipe (no quantity math).",
        "One job: inspect a single allergen class on one card.",
        "",
    ]
    (WEEK7 / "tool_description.diff").write_text("\n".join(lines), encoding="utf-8")


def budget_demo() -> None:
    spec = next(r for r in REQUESTS if r["id"] == "W07")
    out = run_agent(spec["text"], max_iters=2)
    path = WEEK7 / "budget_termination.log"
    body = [
        f"request: {spec['id']}  {spec['text'][:80]}",
        f"max_iters: 2  (race default is 8)",
        f"stopped_by: {out['stopped_by']}",
        f"laps: {out['laps']}",
        f"tokens: {out['tokens']}",
        "",
        "log:",
        *out["log"],
        "",
        "Clean termination: the loop checked max_iters at the top of the next lap",
        "and returned instead of calling the model again.",
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")
    print(f"wrote {path}  stopped_by={out['stopped_by']}")


def race(rpm: float) -> None:
    WEEK7.mkdir(parents=True, exist_ok=True)
    write_tool_diff()
    gap = 60.0 / rpm if rpm else 0
    print("racing 10 requests x 2 systems...", flush=True)
    per = []
    csv_path = WEEK7 / "race.csv"
    fieldnames = [
        "id", "class", "system", "pass", "stopped_by", "laps",
        "tokens", "prompt_tokens", "completion_tokens", "cost_usd", "latency_ms",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

    for spec in REQUESTS:
        for system, fn in (("agent", run_agent), ("workflow", run_workflow)):
            print(f"  start {spec['id']} {system}...", flush=True)
            t0 = time.perf_counter()
            out = fn(spec["text"])
            ok = passes(out["result"], spec)
            row = {
                "id": spec["id"],
                "class": spec["class"],
                "system": system,
                "pass": ok,
                "stopped_by": out["stopped_by"],
                "laps": out["laps"],
                "tokens": out["tokens"],
                "prompt_tokens": out["prompt_tokens"],
                "completion_tokens": out["completion_tokens"],
                "cost_usd": out["cost_usd"],
                "latency_ms": out["latency_ms"],
            }
            per.append(row)
            with csv_path.open("a", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writerow(row)
            flag = "PASS" if ok else "FAIL"
            print(
                f"  {spec['id']} {system:<9} {flag}  "
                f"laps={out['laps']} tok={out['tokens']:<5} "
                f"{out['latency_ms']}ms  {out['stopped_by']}",
                flush=True,
            )
            slept = time.perf_counter() - t0
            if gap and slept < gap:
                time.sleep(gap - slept)

    agent_rows = [r for r in per if r["system"] == "agent"]
    wf_rows = [r for r in per if r["system"] == "workflow"]
    a, b = summarise(agent_rows), summarise(wf_rows)

    print("\n=== race: agent vs workflow (same 10 requests) ===")
    print(f"{'':<22} {'agent':>14} {'workflow':>14}")
    print(f"{'pass rate':<22} {a['n_pass']}/{a['n']:<10} {b['n_pass']}/{b['n']}")
    print(f"{'p50 latency (ms)':<22} {a['p50_latency_ms']:>14} {b['p50_latency_ms']:>14}")
    print(f"{'total tokens':<22} {a['total_tokens']:>14} {b['total_tokens']:>14}")
    print(f"{'cost / request (USD)':<22} {a['cost_per_request_usd']:>14} {b['cost_per_request_usd']:>14}")
    print(f"\nwrote {csv_path}")

    (WEEK7 / "race_summary.json").write_text(
        json.dumps({"agent": a, "workflow": b, "per": per}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpm", type=float, default=20.0)
    ap.add_argument("--budget-demo", action="store_true")
    args = ap.parse_args()
    write_tool_diff()
    if args.budget_demo:
        budget_demo()
        return
    race(args.rpm)


if __name__ == "__main__":
    main()
