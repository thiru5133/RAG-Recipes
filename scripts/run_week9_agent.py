"""Week 9 — ask the MCP agent one question.

    python scripts/run_week9_agent.py "How many kcal in 100 g of paneer?"
    python scripts/run_week9_agent.py --config config/mcp_servers.json "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent.mcp_agent import DEFAULT_CONFIG, run_mcp_agent  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--out", help="write the full run (trace included) as JSON")
    a = ap.parse_args()
    out = run_mcp_agent(a.question, config_path=Path(a.config))
    print("tools discovered:", out["tools_discovered"])
    for t in out["trace"]:
        print(f"  lap {t['lap']}  {t.get('server')}::{t.get('tool')}  {json.dumps(t.get('args'))}  error={t.get('is_error')}")
    print(f"stopped_by={out['stopped_by']} laps={out['laps']} tokens={out['tokens']} cost=${out['cost_usd']}")
    print("\n" + out["answer"])
    if a.out:
        keep = {k: v for k, v in out.items() if k != "messages"}
        Path(a.out).write_text(json.dumps(keep, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
