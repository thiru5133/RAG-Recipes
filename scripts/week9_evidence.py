"""Week 9 evidence: zero-diff proof, tool counts, and the server-two query.

    python scripts/week9_evidence.py

Reads two git tags (week9-server-one, week9-server-two). The agent code is the
same file in both; only config/mcp_servers.json differs. Tool counts come from
a live tools/list against each config, never from notes.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent.mcp_agent import discover, run_mcp_agent  # noqa: E402

OUT = ROOT / "eval" / "week9"
A, B = "week9-server-one", "week9-server-two"
AGENT_PATHS = ["src/agent/mcp_agent.py", "src/mcp_lite"]
QUERY = "How much protein is in 100 g of paneer, and does paneer contain any allergens?"


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def config_at(ref: str) -> Path:
    p = Path(tempfile.mkdtemp()) / f"mcp_servers.{ref}.json"
    p.write_text(git("show", f"{ref}:config/mcp_servers.json"), encoding="utf-8")
    return p


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. agent diff (requirement 2)
    agent_diff = git("diff", A, B, "--", *AGENT_PATHS)
    numstat = git("diff", "--numstat", A, B, "--", *AGENT_PATHS)
    whole = git("diff", "--stat", A, B)
    (OUT / "agent_diff.txt").write_text(
        f"$ git diff {A} {B} -- {' '.join(AGENT_PATHS)}\n"
        f"{agent_diff or '(no output)'}\n"
        f"$ git diff --numstat {A} {B} -- {' '.join(AGENT_PATHS)}\n"
        f"{numstat or '(no output)'}\n"
        f"changed lines in agent module: {sum(int(x.split()[0]) + int(x.split()[1]) for x in numstat.splitlines())}\n\n"
        f"$ git diff --stat {A} {B}      # everything that DID change\n{whole}",
        encoding="utf-8")
    (OUT / "config_diff.txt").write_text(
        f"$ git diff {A} {B} -- config/mcp_servers.json\n" + git("diff", A, B, "--", "config/mcp_servers.json"),
        encoding="utf-8")

    # 2. tool counts from tools/list (requirement 3)
    before = discover(config_at(A))
    after = discover(config_at(B))
    names = lambda ts: ", ".join(f"{t['server']}::{t['name']}" for t in ts)
    counts = (f"tools discovered via tools/list: {len(before)} before -> {len(after)} after\n\n"
              f"before ({len(before)}): {names(before)}\n"
              f"after  ({len(after)}): {names(after)}\n"
              f"added: {names([t for t in after if t not in before])}\n")
    (OUT / "tool_counts.txt").write_text(counts, encoding="utf-8")
    print(counts)

    # 3. one query that provably calls a server-two tool (requirement 1)
    run = run_mcp_agent(QUERY, config_path=config_at(B))
    run.pop("messages")
    (OUT / "server_two_query.json").write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    from_two = [t for t in run["trace"] if t.get("server") == "ingredient_db"]
    print("query:", QUERY)
    for t in run["trace"]:
        print(f"  lap {t['lap']}  {t.get('server')}::{t.get('tool')}  {json.dumps(t.get('args'))}")
    print("answer:", run["answer"])
    print("server-two tool calls:", [t["tool"] for t in from_two])
    assert from_two, "no tool from server two was called"


if __name__ == "__main__":
    main()
