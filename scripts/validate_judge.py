"""Check that the substitution judge agrees with human grading before trusting it.

    python scripts/validate_judge.py            # run the judge on the labelled set
    python scripts/validate_judge.py --label    # grade the set yourself first

Writes eval_runs/judge_validation.json. run_evals.py reads that file and marks
the judge score UNVALIDATED unless the verdict here is trusted.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from config import JUDGE_MODEL  # noqa: E402
from eval.judge_labels import JUDGE_LABELS  # noqa: E402
from eval.substitution_cases import SUBSTITUTION_CASES  # noqa: E402
from judge import JUDGE_PROMPT_VERSION, judge_substitution  # noqa: E402

CASES = {c["qid"]: c for c in SUBSTITUTION_CASES}
USER_LABELS = ROOT / "eval" / "judge_labels_user.json"
OUT = ROOT / "eval_runs" / "judge_validation.json"

# A judge is trusted only if it clears all three bars.
MIN_AGREEMENT = 0.85
MIN_KAPPA = 0.70
MAX_FALSE_PASS_RATE = 0.10  # judge says PASS where the human said FAIL: the costly error


def load_labels():
    """Human labels if the user graded the set, otherwise the draft labels."""
    if USER_LABELS.exists():
        user = json.loads(USER_LABELS.read_text())
        items = [dict(x, label=user[x["id"]]) for x in JUDGE_LABELS if x["id"] in user]
        return items, "user"
    return [dict(x) for x in JUDGE_LABELS], "draft"


def cohens_kappa(pairs):
    n = len(pairs)
    if not n:
        return 0.0
    po = sum(1 for h, j in pairs if h == j) / n
    pe = sum(
        (sum(1 for h, _ in pairs if h == lab) / n) * (sum(1 for _, j in pairs if j == lab) / n)
        for lab in ("PASS", "FAIL")
    )
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def interactive_label():
    existing = json.loads(USER_LABELS.read_text()) if USER_LABELS.exists() else {}
    print("Grade each answer. PASS = every required fact present, nothing wrong or invented.")
    print("For refusal cases PASS = it declines and offers no substitute. p / f / s(kip) / q(uit)\n")
    for item in JUDGE_LABELS:
        if item["id"] in existing:
            continue
        case = CASES[item["qid"]]
        print(f"[{item['id']}] {case['question']}")
        print(f"  expected behaviour: {case['expected_behaviour']}")
        for f in case["required_facts"]:
            print(f"  required: {f}")
        print(f"  ANSWER: {item['answer']}")
        while True:
            a = input("  grade (p/f/s/q): ").strip().lower()
            if a in ("p", "f", "s", "q"):
                break
        if a == "q":
            break
        if a != "s":
            existing[item["id"]] = "PASS" if a == "p" else "FAIL"
            USER_LABELS.write_text(json.dumps(existing, indent=1))
        print()
    print(f"saved {len(existing)}/{len(JUDGE_LABELS)} labels to {USER_LABELS}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", action="store_true", help="grade the labelled set yourself")
    ap.add_argument("--rpm", type=float, default=30.0)
    args = ap.parse_args()
    if args.label:
        return interactive_label()

    labels, source = load_labels()
    print(f"judge {JUDGE_MODEL} ({JUDGE_PROMPT_VERSION}) on {len(labels)} labelled answers; labels: {source}")
    rows, pairs, gap = [], [], 60.0 / args.rpm
    for item in labels:
        out = judge_substitution(CASES[item["qid"]], item["answer"])
        time.sleep(gap)
        row = {"id": item["id"], "qid": item["qid"], "human": item["label"],
               "judge": out["verdict"], "reasoning": out["reasoning"], "error": out["error"],
               "why_human": item.get("why")}
        rows.append(row)
        if out["verdict"]:
            pairs.append((item["label"], out["verdict"]))
        print(f"  {item['id']} human={item['label']} judge={out['verdict']}"
              + ("" if item["label"] == out["verdict"] else "   <-- disagree")
              + (f"  ERROR {out['error']}" if out["error"] else ""))

    n = len(pairs)
    agree = sum(1 for h, j in pairs if h == j)
    fp = sum(1 for h, j in pairs if h == "FAIL" and j == "PASS")
    fn = sum(1 for h, j in pairs if h == "PASS" and j == "FAIL")
    human_fail = sum(1 for h, _ in pairs if h == "FAIL")
    human_pass = n - human_fail
    summary = {
        "judge_model": JUDGE_MODEL,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "label_source": source,
        "labelled": len(labels),
        "judged": n,
        "judge_errors": len(labels) - n,
        "agreement": round(agree / n, 4) if n else 0.0,
        "cohens_kappa": round(cohens_kappa(pairs), 4),
        "false_pass": fp,
        "false_pass_rate": round(fp / human_fail, 4) if human_fail else 0.0,
        "false_fail": fn,
        "false_fail_rate": round(fn / human_pass, 4) if human_pass else 0.0,
        "thresholds": {"agreement": MIN_AGREEMENT, "kappa": MIN_KAPPA, "false_pass_rate": MAX_FALSE_PASS_RATE},
    }
    summary["trusted"] = bool(
        n and summary["judge_errors"] == 0
        and summary["agreement"] >= MIN_AGREEMENT
        and summary["cohens_kappa"] >= MIN_KAPPA
        and summary["false_pass_rate"] <= MAX_FALSE_PASS_RATE
        and source == "user"
    )
    summary["rows"] = rows
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=1, ensure_ascii=False))

    print(f"\nagreement {summary['agreement']:.0%} (need {MIN_AGREEMENT:.0%}) | "
          f"kappa {summary['cohens_kappa']:.2f} (need {MIN_KAPPA}) | "
          f"false-pass {fp}/{human_fail} (need <= {MAX_FALSE_PASS_RATE:.0%}) | false-fail {fn}/{human_pass}")
    if source != "user":
        print("labels are the DRAFT set: run with --label to grade them yourself; "
              "the judge cannot be marked trusted on draft labels.")
    print("TRUSTED" if summary["trusted"] else "NOT TRUSTED")
    for r in rows:
        if r["judge"] != r["human"]:
            print(f"\n{r['id']} ({r['why_human']}): human={r['human']} judge={r['judge']}\n  {r['reasoning']}")


if __name__ == "__main__":
    main()
