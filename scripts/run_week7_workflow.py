"""Week 7 — one-command fixed workflow.

    python scripts/run_week7_workflow.py
    python scripts/run_week7_workflow.py --id W07
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
from agent.workflow import run_workflow  # noqa: E402
from eval.week7.requests import REQUESTS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default="W01")
    args = ap.parse_args()
    spec = next(r for r in REQUESTS if r["id"] == args.id)
    out = run_workflow(spec["text"])
    ok = passes(out["result"], spec)
    print(f"workflow {spec['id']}  pass={ok}  stopped_by={out['stopped_by']}  "
          f"tokens={out['tokens']}  cost_usd={out['cost_usd']}  "
          f"latency_ms={out['latency_ms']}")
    for line in out["log"]:
        print(" ", line)
    print(json.dumps(out["result"], indent=2, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
