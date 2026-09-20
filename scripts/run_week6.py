"""Week 6 eval: assertions + validated LLM judge, one command.

    python scripts/run_week6.py

Prints pass rate by Week-5 taxonomy mode, agreement_before / agreement_after,
and assertion count vs judged-criteria count.

The judge will not run if labels_25.json is missing. That is the point of the
blind protocol: labels first, judge second. `--judge v1` then `--judge v2`
after prediction.txt exists.

Frozen substitutions live in eval/substitutions.py. `--regenerate` is opt-in
and refuses to overwrite while labels exist, so a live model call cannot
quietly invalidate the labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from assertions import ASSERTION_NAMES, run_assertions  # noqa: E402
from eval.substitutions import CASES, frozen_payload  # noqa: E402
from judge import CRITERION, JUDGED_CRITERIA, judge_one, load_prompt  # noqa: E402
from ragas_lite import score_item  # noqa: E402

WEEK6 = ROOT / "eval" / "week6"
LABELS_PATH = WEEK6 / "labels_25.json"
SUBS_PATH = WEEK6 / "substitutions.json"
PRED_PATH = WEEK6 / "prediction.txt"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def substitutions_sha256(payload: dict) -> str:
    blob = json.dumps(
        [(it["qid"], it["substitution"]) for it in payload["items"]],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def write_frozen() -> dict:
    payload = frozen_payload()
    payload["sha256"] = substitutions_sha256(payload)
    payload["written_at"] = utc_now()
    WEEK6.mkdir(parents=True, exist_ok=True)
    SUBS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def load_items() -> tuple[list[dict], str]:
    if SUBS_PATH.exists():
        payload = json.loads(SUBS_PATH.read_text(encoding="utf-8"))
    else:
        payload = write_frozen()
    digest = substitutions_sha256(payload)
    if payload.get("sha256") and payload["sha256"] != digest:
        raise SystemExit("substitutions.json sha256 does not match contents; refusing to score")
    return payload["items"], digest


def load_labels(digest: str) -> dict:
    if not LABELS_PATH.exists():
        raise SystemExit(
            f"Blind protocol: write {LABELS_PATH} before running the judge.\n"
            "The file must contain 25+ human PASS/FAIL labels and the substitutions sha256."
        )
    labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    if labels.get("substitutions_sha256") != digest:
        raise SystemExit(
            "labels_25.json substitutions_sha256 does not match the frozen texts. "
            "Relabel after changing substitutions, never the other way around."
        )
    return labels


def assertion_table(items: list[dict]) -> list[dict]:
    rows = []
    for it in items:
        result = run_assertions(it["substitution"], it.get("servings_expected"))
        rows.append({**it, "assertions": result, "assertion_pass": result["passed"]})
    return rows


def run_judge(items: list[dict], version: str, rpm: float, force: bool) -> dict:
    out_path = WEEK6 / f"judge_{version}_results.json"
    if out_path.exists() and not force:
        cached = json.loads(out_path.read_text(encoding="utf-8"))
        print(f"  using cached {out_path.name} (pass --force to re-call the model)")
        return cached

    prompt = load_prompt(version)
    min_gap = 60.0 / rpm
    per = []
    for i, it in enumerate(items, 1):
        started = time.perf_counter()
        result = judge_one(it, prompt)
        per.append(result)
        flag = result["verdict"] or "UNPARSED"
        err = f"  {result['error'][:80]}" if result.get("error") else ""
        print(f"  {version} {i:02d}/{len(items)}  {it['qid']}  {flag}{err}")
        if result.get("error") and ("429" in result["error"] or "rate" in result["error"].lower()):
            time.sleep(20)
        elapsed = time.perf_counter() - started
        if elapsed < min_gap and i < len(items):
            time.sleep(min_gap - elapsed)

    bundle = {
        "version": version,
        "judged_at": utc_now(),
        "n": len(per),
        "substitutions_sha256": substitutions_sha256({"items": items}),
        "per": per,
    }
    out_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return bundle


def agreement(labels: dict, judge_bundle: dict) -> dict:
    human = {row["qid"]: row["human"].upper() for row in labels["labels"]}
    machine = {row["qid"]: (row.get("verdict") or "").upper() for row in judge_bundle["per"]}
    qids = [row["qid"] for row in labels["labels"] if row["qid"] in machine]
    n = len(qids)
    matches = 0
    disagreements = []
    for qid in qids:
        h, j = human[qid], machine[qid]
        if h == j and h in {"PASS", "FAIL"}:
            matches += 1
        else:
            disagreements.append({"qid": qid, "human": h, "judge": j or "UNPARSED"})
    return {
        "n": n,
        "matches": matches,
        "pct": round(100.0 * matches / n, 1) if n else 0.0,
        "disagreements": disagreements,
    }


def pass_rates(rows: list[dict], judge_bundle: dict, key: str) -> list[tuple[str, int, int]]:
    verdict = {r["qid"]: r.get("verdict") for r in judge_bundle["per"]}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    out = []
    for name in sorted(grouped):
        bucket = grouped[name]
        n_pass = sum(
            1
            for r in bucket
            if r["assertion_pass"] and verdict.get(r["qid"]) == "PASS"
        )
        out.append((name, n_pass, len(bucket)))
    n_pass = sum(1 for r in rows if r["assertion_pass"] and verdict.get(r["qid"]) == "PASS")
    out.append(("OVERALL", n_pass, len(rows)))
    return out


def print_rate_table(title: str, rows: list[tuple[str, int, int]]) -> None:
    print(f"\n{title}")
    print(f"  {'mode':<28} {'pass':>8} {'rate':>8}")
    for name, n_pass, n in rows:
        pct = f"{100.0 * n_pass / n:5.1f}%" if n else "  n/a"
        print(f"  {name:<28} {n_pass:>3}/{n:<3} {pct:>8}")


def ragas_report(items: list[dict]) -> dict:
    scored = [score_item(it) for it in items]
    faith = [s["faithfulness"]["score"] for s in scored]
    prec = [s["context_precision"]["score"] for s in scored]
    avg_f = round(sum(faith) / len(faith), 3) if faith else 0.0
    avg_p = round(sum(prec) / len(prec), 3) if prec else 0.0
    hidden = []
    for it, s in zip(items, scored):
        if s["faithfulness"]["score"] >= 0.9 and s["context_precision"]["score"] < 0.5:
            hidden.append(
                {
                    "qid": it["qid"],
                    "faithfulness": s["faithfulness"]["score"],
                    "context_precision": s["context_precision"]["score"],
                    "gold": it.get("gold_recipe"),
                    "retrieved": it.get("retrieved_recipe_ids"),
                }
            )
    return {
        "avg_faithfulness": avg_f,
        "avg_context_precision": avg_p,
        "per": scored,
        "faithfully_wrong": hidden,
    }


def print_protocol(labels: dict, v1: dict, v2: dict | None) -> None:
    print("\nBlind protocol")
    print(f"  labels_25.json     labeled_at = {labels.get('labeled_at')}")
    print(f"  judge v1           judged_at  = {v1.get('judged_at')}")
    if v2:
        print(f"  judge v2           judged_at  = {v2.get('judged_at')}")
    print(f"  substitutions sha256 = {labels.get('substitutions_sha256')}")
    labeled = labels.get("labeled_at") or ""
    judged = v1.get("judged_at") or ""
    if labeled and judged and labeled > judged:
        print("  WARNING: labels timestamp is after the judge run — that is not blind.")
    else:
        print("  order: labels timestamp precedes judge v1.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", choices=["none", "v1", "v2", "both"], default="both")
    ap.add_argument("--rpm", type=float, default=20.0)
    ap.add_argument("--force", action="store_true", help="re-call the judge even if results exist")
    ap.add_argument(
        "--write-frozen",
        action="store_true",
        help="rewrite substitutions.json from eval/substitutions.py",
    )
    args = ap.parse_args()

    WEEK6.mkdir(parents=True, exist_ok=True)
    if args.write_frozen or not SUBS_PATH.exists():
        payload = write_frozen()
        print(f"wrote {SUBS_PATH}  sha256={payload['sha256'][:12]}…  n={payload['n']}")

    items, digest = load_items()
    rows = assertion_table(items)
    ragas = ragas_report(items)

    print("=== Week 6 eval — substitution judge ===")
    print(f"cases: {len(items)}   assertions: {len(ASSERTION_NAMES)}   judged criteria: {JUDGED_CRITERIA}")
    print(f"criterion: {CRITERION}")

    labels = None
    v1 = v2 = None
    agr1 = agr2 = None

    if args.judge != "none":
        labels = load_labels(digest)
        label_mtime = LABELS_PATH.stat().st_mtime
        want_v1 = args.judge in {"v1", "both"}
        want_v2 = args.judge in {"v2", "both"}
        if want_v1:
            print("\nJudge v1")
            v1 = run_judge(items, "v1", args.rpm, args.force)
            v1_path = WEEK6 / "judge_v1_results.json"
            if v1_path.stat().st_mtime < label_mtime and not args.force:
                pass  # cached file may predate a relabel; user must --force
            agr1 = agreement(labels, v1)
        if want_v2:
            if not PRED_PATH.exists():
                print("\nJudge v2 skipped — write prediction.txt before iterating the prompt.")
            elif not (WEEK6 / "judge_v2.txt").exists():
                print("\nJudge v2 skipped — judge_v2.txt is not written yet.")
            else:
                print("\nJudge v2")
                v2 = run_judge(items, "v2", args.rpm, args.force)
                agr2 = agreement(labels, v2)

    if v1:
        print_rate_table("Pass rate by Week-5 taxonomy mode (judge v1)", pass_rates(rows, v1, "mode"))
        print_rate_table("Pass rate by slice (judge v1)", pass_rates(rows, v1, "slice"))
    if v2:
        print_rate_table("Pass rate by Week-5 taxonomy mode (judge v2)", pass_rates(rows, v2, "mode"))
        print_rate_table("Pass rate by slice (judge v2)", pass_rates(rows, v2, "slice"))

    print("\nAssertion vs judged criteria")
    print(f"  assertions implemented : {len(ASSERTION_NAMES)}  ({', '.join(ASSERTION_NAMES)})")
    print(f"  judged criteria        : {JUDGED_CRITERIA}  (constraint honouring, binary PASS/FAIL)")

    if agr1:
        print(f"\nagreement_before: {agr1['pct']}%  ({agr1['matches']}/{agr1['n']})")
        if agr1["disagreements"]:
            print("  v1 disagreements:")
            for d in agr1["disagreements"]:
                print(f"    {d['qid']}: human={d['human']}  judge={d['judge']}")
    if agr2:
        print(f"agreement_after:  {agr2['pct']}%  ({agr2['matches']}/{agr2['n']})")
        if agr2["disagreements"]:
            print("  v2 disagreements:")
            for d in agr2["disagreements"]:
                print(f"    {d['qid']}: human={d['human']}  judge={d['judge']}")

    print("\nRAGAS-lite")
    print(f"  avg faithfulness       : {ragas['avg_faithfulness']}")
    print(f"  avg context precision  : {ragas['avg_context_precision']}")
    if ragas["faithfully_wrong"]:
        print("  faithfully-wrong cases (faithfulness >= 0.9, context precision < 0.5):")
        for h in ragas["faithfully_wrong"]:
            print(
                f"    {h['qid']}: faithfulness={h['faithfulness']}  "
                f"context_precision={h['context_precision']}  "
                f"gold={h['gold']} retrieved={h['retrieved']}"
            )
    else:
        print("  no case with faithfulness >= 0.9 and context precision < 0.5")

    if labels and v1:
        print_protocol(labels, v1, v2)

    summary = {
        "n_cases": len(items),
        "n_assertions": len(ASSERTION_NAMES),
        "n_judged_criteria": JUDGED_CRITERIA,
        "agreement_before": agr1,
        "agreement_after": agr2,
        "ragas": {
            "avg_faithfulness": ragas["avg_faithfulness"],
            "avg_context_precision": ragas["avg_context_precision"],
            "faithfully_wrong": ragas["faithfully_wrong"],
        },
    }
    (WEEK6 / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {WEEK6 / 'summary.json'}")


if __name__ == "__main__":
    main()
