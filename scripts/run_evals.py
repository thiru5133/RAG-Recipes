"""One command: score the app on every problem type.

    python scripts/run_evals.py                          # full run (uses the Groq API)
    python scripts/run_evals.py --no-llm                 # free checks only
    python scripts/run_evals.py --tag after --prompt-version v1.3.0

Free, deterministic suites run first (they replay last week's failures). The
LLM suites then generate answers and score them: rule assertions first, the
validated substitution judge for the part a rule cannot check. Results go to
eval_runs/<tag>.json; compare two runs with scripts/compare_evals.py.
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import assertions  # noqa: E402
from config import GROQ_MODEL, JUDGE_MODEL, REFUSAL_THRESHOLD  # noqa: E402
from eval.generation_cases import ANSWER_CASES, REFUSE_CASES  # noqa: E402
from eval.questions import QUESTIONS  # noqa: E402
from eval.regression_cases import CITATION_SHAPES, legacy_extract_citations  # noqa: E402
from eval.substitution_cases import SUBSTITUTION_CASES  # noqa: E402
from evaluate import evaluate_hits  # noqa: E402
from generate import PROMPT_VERSION, extract_citations  # noqa: E402
from guardrails import answer_question, below_threshold  # noqa: E402
from judge import JUDGE_PROMPT_VERSION, judge_substitution  # noqa: E402
from retrieve import search  # noqa: E402

RUNS = ROOT / "eval_runs"
VALIDATION = RUNS / "judge_validation.json"

# The fixed configuration every LLM suite runs under, so only the thing being
# changed (the prompt) differs between two runs.
CONFIG = {"strategy": "structured", "mode": "semantic", "k": 3, "rerank": False}

PROBLEM_TYPES = {
    "citation_format": "Citation in a shape the verifier cannot read",
    "hybrid_gate": "Hybrid search refused by the score gate",
    "table_miss": "Ingredient/nutrition table missing from the top 3",
    "answer_assertions": "Answerable question answered, cited and correct",
    "refusal": "Unanswerable question correctly refused",
    "substitution": "Substitution answer complete and faithful (LLM judge)",
}


def suite(name, cases, baseline=None, errors=0, **extra):
    passed = sum(1 for c in cases if c["passed"])
    out = {"problem_type": PROBLEM_TYPES[name], "passed": passed, "total": len(cases),
           "errors": errors, "cases": cases}
    if baseline is not None:
        out["baseline_passed"] = baseline["passed"]
        out["baseline_label"] = baseline["label"]
    out.update(extra)
    return out


# --------------------------------------------------------------------------
# Free suites: regression tests from the week-5 failures
# --------------------------------------------------------------------------

def run_citation_format():
    cases, legacy_ok = [], 0
    for s in CITATION_SHAPES:
        got, old = extract_citations(s["text"]), legacy_extract_citations(s["text"])
        ok, old_ok = got == s["expected"], old == s["expected"]
        legacy_ok += old_ok
        cases.append({"id": s["id"], "trace": s["trace"], "passed": ok, "legacy_passed": old_ok,
                      "expected": s["expected"], "got": got})
    return suite("citation_format", cases,
                 baseline={"passed": legacy_ok, "label": "extractor as shipped in week 5"})


def run_hybrid_gate():
    """Every answerable golden question must clear the refusal gate in hybrid
    mode. The legacy figure replays the pre-fix gate, which compared the RRF
    score (never above ~0.033) with the 0.30 cosine threshold."""
    cases, legacy_ok = [], 0
    for q in QUESTIONS:
        hits = search(q["question"], strategy="structured", k=5, mode="hybrid")
        gate_ok = not below_threshold(hits, REFUSAL_THRESHOLD)
        legacy = bool(hits) and hits[0].get("rrf_score", 0.0) >= REFUSAL_THRESHOLD
        legacy_ok += legacy
        cases.append({"id": q["qid"], "passed": gate_ok, "legacy_passed": legacy,
                      "top_rrf": hits[0].get("rrf_score") if hits else None,
                      "gate_cosine": hits[0].get("gate_score") if hits else None})
    return suite("hybrid_gate", cases,
                 baseline={"passed": legacy_ok, "label": "gate on the RRF score (pre-fix)"})


def run_table_miss():
    """The card's answer row must be in the top 3 for table questions.
    Baseline is plain semantic retrieval; current is the same with rerank on."""
    cases, base_ok = [], 0
    for q in [q for q in QUESTIONS if q["type"] == "table"]:
        plain = evaluate_hits(search(q["question"], strategy="structured", k=3), q)
        rer = evaluate_hits(search(q["question"], strategy="structured", k=3, rerank=True), q)
        b = plain["first_answer_rank"] is not None and plain["first_answer_rank"] <= 3
        c = rer["first_answer_rank"] is not None and rer["first_answer_rank"] <= 3
        base_ok += b
        cases.append({"id": q["qid"], "passed": c, "legacy_passed": b,
                      "rank_plain": plain["first_answer_rank"], "rank_rerank": rer["first_answer_rank"]})
    return suite("table_miss", cases,
                 baseline={"passed": base_ok, "label": "semantic, rerank off"})


# --------------------------------------------------------------------------
# LLM suites
# --------------------------------------------------------------------------

class Pacer:
    def __init__(self, rpm):
        self.gap, self.last = 60.0 / rpm, 0.0

    def wait(self):
        delay = self.gap - (time.time() - self.last)
        if delay > 0:
            time.sleep(delay)
        self.last = time.time()


def ask(question, prompt_version, pacer, retries=3):
    """Retrieve and answer through the real guarded path, retrying rate limits."""
    hits = search(question, **CONFIG)
    result = None
    for attempt in range(retries):
        pacer.wait()
        result = answer_question(question, hits, prompt_version=prompt_version)
        err = result.get("error") or ""
        if not err or "RateLimit" not in err:
            break
        time.sleep(20 * (attempt + 1))
    return hits, result


def run_answer_assertions(prompt_version, pacer):
    cases, errors = [], 0
    for c in ANSWER_CASES:
        hits, result = ask(c["question"], prompt_version, pacer)
        if result.get("error"):
            errors += 1
            cases.append({"id": c["qid"], "passed": False, "error": result["error"]})
            continue
        checks = assertions.expect_answer(result, c["gold_recipes"], c["must_contain"])
        cases.append({"id": c["qid"], "passed": all(ok for ok, _ in checks.values()),
                      "checks": {k: ok for k, (ok, _) in checks.items()},
                      "answer": result["answer"]})
    return suite("answer_assertions", [c for c in cases if "error" not in c], errors=errors)


def run_refusal(prompt_version, pacer):
    cases, errors = [], 0
    for c in REFUSE_CASES:
        _, result = ask(c["question"], prompt_version, pacer)
        if result.get("error"):
            errors += 1
            continue
        ok, detail = assertions.refused(result)
        cases.append({"id": c["qid"], "passed": ok, "detail": detail, "answer": result["answer"]})
    return suite("refusal", cases, errors=errors)


def run_substitution(prompt_version, pacer):
    cases, errors = [], 0
    for c in SUBSTITUTION_CASES:
        hits, result = ask(c["question"], prompt_version, pacer)
        if result.get("error"):
            errors += 1
            continue
        pacer.wait()
        verdict = judge_substitution(c, result["answer"])
        if verdict["verdict"] is None:
            errors += 1
            continue
        cites = assertions.citation_valid(result)[0] if not result["refused"] else None
        cases.append({"id": c["qid"], "passed": verdict["verdict"] == "PASS",
                      "verdict": verdict["verdict"], "reasoning": verdict["reasoning"],
                      "answer": result["answer"], "citation_valid": cites,
                      "retrieved": [h["chunk_id"] for h in hits]})
    return suite("substitution", cases, errors=errors)


def judge_status():
    if not VALIDATION.exists():
        return {"validated": False, "note": "no judge_validation.json: run scripts/validate_judge.py"}
    v = json.loads(VALIDATION.read_text())
    return {"validated": bool(v.get("trusted")), "agreement": v.get("agreement"),
            "kappa": v.get("cohens_kappa"), "label_source": v.get("label_source")}


def print_summary(run):
    print(f"\n=== {run['tag']}  prompt {run['prompt_version']}  judge {run['judge']} ===")
    for name, s in run["suites"].items():
        base = f"   (baseline {s['baseline_passed']}/{s['total']}: {s['baseline_label']})" if "baseline_passed" in s else ""
        err = f"  [{s['errors']} errored, excluded]" if s.get("errors") else ""
        flag = "  UNVALIDATED JUDGE" if name == "substitution" and not run["judge"]["validated"] else ""
        print(f"  {s['passed']:>2}/{s['total']:<2}  {s['problem_type']}{base}{err}{flag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="run")
    ap.add_argument("--prompt-version", default=PROMPT_VERSION)
    ap.add_argument("--no-llm", action="store_true", help="free checks only")
    ap.add_argument("--rpm", type=float, default=25.0)
    args = ap.parse_args()

    run = {"tag": args.tag, "timestamp": datetime.now().isoformat(timespec="seconds"),
           "prompt_version": args.prompt_version, "generator": GROQ_MODEL,
           "judge": dict(model=JUDGE_MODEL, prompt_version=JUDGE_PROMPT_VERSION, **judge_status()),
           "config": CONFIG, "suites": {}}
    run["suites"]["citation_format"] = run_citation_format()
    run["suites"]["hybrid_gate"] = run_hybrid_gate()
    run["suites"]["table_miss"] = run_table_miss()
    if not args.no_llm:
        pacer = Pacer(args.rpm)
        run["suites"]["answer_assertions"] = run_answer_assertions(args.prompt_version, pacer)
        run["suites"]["refusal"] = run_refusal(args.prompt_version, pacer)
        run["suites"]["substitution"] = run_substitution(args.prompt_version, pacer)

    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{args.tag}.json").write_text(json.dumps(run, indent=1, ensure_ascii=False))
    print_summary(run)
    print(f"\nsaved eval_runs/{args.tag}.json")


if __name__ == "__main__":
    main()
