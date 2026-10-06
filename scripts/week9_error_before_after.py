"""Requirement 5: replay the SAME failing scale_recipe call against the old and the
new recipe server and record how the model handles each.

    python scripts/week9_error_before_after.py [--trials 5]

Old server = src/mcp_servers/recipe_server.py at tag week9-server-one
("Scale a recipe to a number of servings." / "Error 3"). New = working tree.
The failing call is injected (not sampled) so the only variable is the
docstring + error text the model sees.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent.mcp_agent import McpHost, run_mcp_agent  # noqa: E402

REQUEST = "Scale the shakshuka to 6 servings."
BAD_ARGS = {"recipe_id": "shakshuka", "servings": 6}
OLD_REF = "week9-server-one"


def variant_config(server_file: Path, attach: bool) -> Path:
    cfg = {"servers": {"recipes": {"command": "${PYTHON}", "args": [str(server_file)],
                                   "attach_resources": ["recipes://allergen-matrix"] if attach else []}}}
    p = Path(tempfile.mkdtemp()) / "cfg.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


def one_trial(cfg: Path) -> dict:
    host = McpHost(cfg).connect()
    try:
        err = host.call("scale_recipe", BAD_ARGS)  # the identical failing call, against this server
        prefix = [
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "call_bad", "type": "function",
                 "function": {"name": "scale_recipe", "arguments": json.dumps(BAD_ARGS)}}]},
            {"role": "tool", "tool_call_id": "call_bad", "content": "ERROR: " + err["text"]},
        ]
        run = run_mcp_agent(REQUEST, host=host, prefix_messages=prefix)
    finally:
        host.close()
    follow = run["trace"]
    scaled_ok = any(t.get("tool") == "scale_recipe" and not t["is_error"] and t["args"].get("recipe_id") == "R006"
                    for t in follow)
    searched = any(t.get("tool") == "search_recipes" for t in follow)
    return {"error_text_seen": err["text"], "followup_calls": [
        {"tool": t.get("tool"), "args": t.get("args"), "is_error": t.get("is_error")} for t in follow if "tool" in t],
        "searched_first": searched, "recovered": scaled_ok, "answer": run["answer"],
        "tokens": run["tokens"], "stopped_by": run["stopped_by"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=5)
    n = ap.parse_args().trials
    old_src = subprocess.run(["git", "show", f"{OLD_REF}:src/mcp_servers/recipe_server.py"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
    old_file = ROOT / "src" / "mcp_servers" / "_old_recipe_server.py"
    old_file.write_text(old_src, encoding="utf-8")
    results = {}
    try:
        for label, server in (("before", old_file), ("after", ROOT / "src/mcp_servers/recipe_server.py")):
            for attach in (False, True):
                cfg = variant_config(server, attach)
                results[(label, attach)] = [one_trial(cfg) for _ in range(n)]
    finally:
        old_file.unlink(missing_ok=True) if sys.version_info >= (3, 8) else None

    def rate(k):
        return sum(t["recovered"] for t in results[k]), len(results[k])

    old_doc = "Scale a recipe to a number of servings."
    md = [f"# Requirement 5 — same failing call, old vs new docstring/error\n",
          f"Request: `{REQUEST}`  \nInjected failing call (identical in every trial): "
          f"`scale_recipe({json.dumps(BAD_ARGS)})` — a guessed dish name instead of an id.\n",
          "| | tool description the model saw | error text the model saw |", "|---|---|---|",
          f"| **before** (`{OLD_REF}`) | `{old_doc}` | `{results[('before', False)][0]['error_text_seen']}` |",
          f"| **after** (working tree) | docstring rewritten as a prompt (see `recipe_server.py`) | "
          f"`{results[('after', False)][0]['error_text_seen']}` |\n",
          f"## Recovery rate over {n} trials (recovered = a later `scale_recipe` succeeded on R006)\n",
          "| condition | before | after |", "|---|---:|---:|"]
    for attach, name in ((False, "no allergen matrix attached (isolates the error text)"),
                         (True, "allergen matrix attached as a resource")):
        b, a = rate(("before", attach)), rate(("after", attach))
        md.append(f"| {name} | {b[0]}/{b[1]} | {a[0]}/{a[1]} |")
    for attach in (False, True):
        for label in ("before", "after"):
            t = results[(label, attach)][0]
            md += [f"\n## Transcript — {label}, matrix {'attached' if attach else 'not attached'} (trial 1)\n",
                   f"1. user: {REQUEST}", f"2. model -> `scale_recipe({json.dumps(BAD_ARGS)})`",
                   f"3. tool: `ERROR: {t['error_text_seen']}`"]
            for i, c in enumerate(t["followup_calls"], 4):
                md.append(f"{i}. model -> `{c['tool']}({json.dumps(c['args'])})` "
                          f"{'-> error' if c['is_error'] else '-> ok'}")
            md.append(f"{len(t['followup_calls']) + 4}. model answer: {t['answer'].strip() or '(none)'}  "
                      f"\n   _stopped_by={t['stopped_by']}, tokens={t['tokens']}_")
    (ROOT / "eval" / "week9" / "error_before_after.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (ROOT / "eval" / "week9" / "error_before_after.json").write_text(
        json.dumps({f"{k[0]}|matrix={k[1]}": v for k, v in results.items()}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print("\n".join(md[:14]))


if __name__ == "__main__":
    main()
