"""Week 7 — one-command agent.

    python scripts/run_week7_agent.py
    python scripts/run_week7_agent.py --id W07
    python scripts/run_week7_agent.py --id W07 --max-iters 2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from agent.contract import passes  # noqa: E402
from agent.loop import run_agent  # noqa: E402
from eval.week7.requests import REQUESTS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="W01")
    ap.add_argument("--max-iters", type=int, default=None)
    ap.add_argument("--max-tokens", type=int, default=None)
    ap.add_argument("--max-cost", type=float, default=None)
    ap.add_argument("--max-wall-ms", type=int, default=None)
    args = ap.parse_args()

    spec = next(r for r in REQUESTS if r["id"] == args.id)
    kwargs = {}
    if args.max_iters is not None:
        kwargs["max_iters"] = args.max_iters
    if args.max_tokens is not None:
        kwargs["max_tokens"] = args.max_tokens
    if args.max_cost is not None:
        kwargs["max_cost_usd"] = args.max_cost
    if args.max_wall_ms is not None:
        kwargs["max_wall_ms"] = args.max_wall_ms

    out = run_agent(spec["text"], **kwargs)
    ok = passes(out["result"], spec)
    print(f"agent {spec['id']}  pass={ok}  stopped_by={out['stopped_by']}  "
          f"laps={out['laps']}  tokens={out['tokens']}  "
          f"cost_usd={out['cost_usd']}  latency_ms={out['latency_ms']}")
    for line in out["log"]:
        print(" ", line)
    print(json.dumps(out["result"], indent=2, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
