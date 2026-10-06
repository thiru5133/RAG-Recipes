"""Turn eval/week10/race_runs.json into race_table.md + multiplier.txt.

    python scripts/week10_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "week10"


def pct(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def main() -> None:
    rows = json.loads((OUT / "race_runs.json").read_text())
    arms = {a: [r for r in rows if r["arm"] == a] for a in ("single", "multi")}
    n = len(arms["single"])
    stats = {}
    for a, rs in arms.items():
        stats[a] = {
            "pass": sum(r["pass"] for r in rs), "n": len(rs),
            "p50": pct([r["latency_ms"] for r in rs], 50) / 1000, "p99": pct([r["latency_ms"] for r in rs], 99) / 1000,
            "tokens": sum(r["tokens"] for r in rs), "cost_q": sum(r["cost_usd"] for r in rs) / len(rs),
            "assert": sum(r["assertions"] for r in rs), "judge": sum(r["verdict"] == "PASS" for r in rs),
        }
    s, m = stats["single"], stats["multi"]
    mult = m["tokens"] / s["tokens"]
    share: dict = {}
    for r in arms["multi"]:
        for h, t in r["by_handoff"].items():
            share[h] = share.get(h, 0) + t
    top = max(share, key=share.get)
    top_pct = 100 * share[top] / m["tokens"]
    md = [f"# Week 10 race: single agent vs kitchen squad\n",
          f"Same {n} Week-6 cases ({', '.join(r['qid'] for r in arms['single'])}), same scorer "
          "(5 assertions AND judge v2; pass = both). One run per case per arm. Model `openai/gpt-oss-20b` for both arms; "
          "judge `openai/gpt-oss-120b` (not counted in cost). Latency excludes MCP server start-up for both arms.\n",
          "| metric | single agent | orchestrator + 2 workers |", "|---|---:|---:|",
          f"| pass rate | {s['pass']}/{s['n']} | {m['pass']}/{m['n']} |",
          f"| (assertions pass / judge PASS) | {s['assert']} / {s['judge']} | {m['assert']} / {m['judge']} |",
          f"| p50 latency | {s['p50']:.1f} s | {m['p50']:.1f} s |",
          f"| p99 latency (interpolated, n={n}) | {s['p99']:.1f} s | {m['p99']:.1f} s |",
          f"| total tokens | {s['tokens']:,} | {m['tokens']:,} |",
          f"| cost per question | ${s['cost_q']:.6f} | ${m['cost_q']:.6f} |\n",
          "## Per case\n", "| case | single pass | single tokens | single s | multi pass | multi tokens | multi s |", "|---|---|---:|---:|---|---:|---:|"]
    for a, b in zip(arms["single"], arms["multi"]):
        md.append(f"| {a['qid']} | {'PASS' if a['pass'] else 'FAIL'} | {a['tokens']:,} | {a['latency_ms']/1000:.1f} | "
                  f"{'PASS' if b['pass'] else 'FAIL'} | {b['tokens']:,} | {b['latency_ms']/1000:.1f} |")
    md += ["\n## Where the multi-agent tokens went (all cases)\n", "| hand-off | tokens | share of multi total |", "|---|---:|---:|"]
    for h, t in sorted(share.items(), key=lambda kv: -kv[1]):
        md.append(f"| {h} | {t:,} | {100*t/m['tokens']:.0f}% |")
    line = (f"context re-send multiplier = {m['tokens']:,} / {s['tokens']:,} = {mult:.1f}x; "
            f"largest share: {top} = {top_pct:.0f}% of all multi-agent tokens")
    md.append(f"\n**{line}**")
    (OUT / "race_table.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "multiplier.txt").write_text(line + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
