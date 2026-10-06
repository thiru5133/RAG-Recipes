"""Bonus: both servers behind one gateway, audit line per call, scoped token.

    python scripts/week9_gateway_demo.py

The agent is unchanged: it is pointed at config/mcp_servers.gateway.json, which
lists ONE server (the gateway). Same question, two tokens.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent.mcp_agent import run_mcp_agent  # noqa: E402

CFG = ROOT / "config" / "mcp_servers.gateway.json"
AUDIT = ROOT / "logs" / "gateway_audit.log"
QUESTION = "For 100 g of paneer, give me the calories and protein, and tell me which allergens it has."
TOKENS = [("tok-recipe-agent-full", "full scope"), ("tok-recipe-agent-allergen-only", "allergen-only scope")]


def main() -> None:
    AUDIT.unlink(missing_ok=True)
    md = ["# Bonus — one gateway front door, audit line per call, scoped token\n",
          f"Agent config: `config/mcp_servers.gateway.json` (one server: the gateway). Question: `{QUESTION}`\n"]
    for tok, label in TOKENS:
        os.environ["GATEWAY_TOKEN"] = tok
        start = AUDIT.read_text().count("\n") if AUDIT.exists() else 0
        run = run_mcp_agent(QUESTION, config_path=CFG)
        lines = AUDIT.read_text().splitlines()[start:]
        md += [f"\n## {label} (`{tok}`)\n", f"tools the agent discovered through the single front door: "
               f"{len(run['tools_discovered'])} — {', '.join(run['tools_discovered'])}\n", "Trace:\n"]
        for t in run["trace"]:
            if "tool" in t:
                md.append(f"- `{t['tool']}({json.dumps(t['args'])})` -> {'ERROR' if t['is_error'] else 'ok'}: {t['result'][:230]}")
        md += ["\nAudit lines written by the gateway:\n", "```"] + lines + ["```", f"\nFinal answer: {run['answer'].strip()}"]
    diff = subprocess.run(["git", "diff", "--numstat", "week9-server-two", "--", "src/agent/mcp_agent.py"],
                          cwd=ROOT, capture_output=True, text=True).stdout
    md.append(f"\nChanged lines in agent/mcp_agent.py vs `week9-server-two`: {'0' if not diff.strip() else diff.strip()}")
    (ROOT / "eval" / "week9" / "bonus_gateway.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
