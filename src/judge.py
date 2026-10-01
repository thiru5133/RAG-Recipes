"""LLM-as-judge for substitution answers (G-Eval style, binary verdict).

Binary PASS/FAIL, not 1-10: a yes/no against explicit criteria is easier to
validate against a human and harder for the judge to hedge on. The judge reasons
through the criteria first, then commits to a verdict in JSON.

The judge is only trusted after `scripts/validate_judge.py` shows it agrees with
human grading. See eval/judge_labels.py.
"""
import json
import re
from typing import Dict

from config import JUDGE_MODEL
from generate import complete

JUDGE_PROMPT_VERSION = "j1.0.0"

JUDGE_SYSTEM = """You grade answers from a recipe assistant that was asked about a
substitution or how to adapt a recipe. You are given the recipe card text, the
facts a correct answer must contain, and the assistant's answer.

Work through these steps, then give a verdict.
1. COMPLETE: for each REQUIRED FACT, is it present in the answer with the same
   meaning? Numbers, units and ingredient names must match. A missing fact fails.
2. FAITHFUL: does the answer contradict the card, or add a swap, quantity or
   condition that the card does not state? Any invented or wrong detail fails.
3. BEHAVIOUR: if EXPECTED BEHAVIOUR is "refuse", the card has no answer; the
   answer must decline to answer from the cards and must not offer a substitute.
   If it is "answer", a refusal fails.
Ignore tone, length and citation formatting. Judge content only.

Reply with JSON only, no other text:
{"reasoning": "<one or two sentences covering steps 1-3>", "verdict": "PASS" or "FAIL"}
PASS only if all three steps pass."""


def build_judge_prompt(case: Dict, answer: str) -> str:
    facts = "\n".join(f"- {f}" for f in case["required_facts"]) or "- (none: the card has no answer)"
    return (
        f"QUESTION: {case['question']}\n\n"
        f"RECIPE CARD TEXT:\n{case['reference']}\n\n"
        f"REQUIRED FACTS:\n{facts}\n\n"
        f"EXPECTED BEHAVIOUR: {case['expected_behaviour']}\n\n"
        f"ASSISTANT ANSWER:\n{answer}"
    )


_JSON_RE = re.compile(r"\{.*\}", re.S)


def parse_verdict(raw: str) -> Dict:
    """Pull the JSON object out of the reply. Anything unparseable is an error,
    never silently a PASS or a FAIL."""
    if not raw:
        return {"verdict": None, "reasoning": "", "parse_error": "empty reply"}
    m = _JSON_RE.search(raw)
    if not m:
        return {"verdict": None, "reasoning": raw[:200], "parse_error": "no JSON"}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        return {"verdict": None, "reasoning": raw[:200], "parse_error": str(exc)}
    verdict = str(obj.get("verdict", "")).strip().upper()
    if verdict not in ("PASS", "FAIL"):
        return {"verdict": None, "reasoning": str(obj.get("reasoning", "")), "parse_error": f"bad verdict {verdict!r}"}
    return {"verdict": verdict, "reasoning": str(obj.get("reasoning", "")), "parse_error": None}


def judge_substitution(case: Dict, answer: str, model: str = JUDGE_MODEL) -> Dict:
    """Grade one answer. Returns verdict ('PASS'/'FAIL'/None), reasoning, error."""
    res = complete(JUDGE_SYSTEM, build_judge_prompt(case, answer), model=model, temperature=0, max_tokens=900)
    if res["error"]:
        return {"verdict": None, "reasoning": "", "error": res["error"]}
    parsed = parse_verdict(res["answer"])
    return {"verdict": parsed["verdict"], "reasoning": parsed["reasoning"], "error": parsed["parse_error"]}
