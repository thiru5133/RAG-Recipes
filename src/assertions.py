"""Rule-based checks. Free, deterministic, run before any LLM judge.

Each check takes the dict returned by `guardrails.answer_question` and returns
(passed: bool, detail: str).
"""
from typing import Dict, Iterable, Tuple

Check = Tuple[bool, str]


def refused(result: Dict) -> Check:
    return bool(result.get("refused")), f"refused_by={result.get('refused_by')}"


def answered(result: Dict) -> Check:
    ok = not result.get("refused") and bool(result.get("answer")) and not result.get("error")
    return ok, "answered" if ok else f"refused={result.get('refused')} error={result.get('error')}"


def citation_valid(result: Dict) -> Check:
    """A parseable citation whose chunk_id was in the context and whose
    recipe_id matches that chunk."""
    c = result.get("citations") or {}
    return bool(c.get("valid")), f"cited={c.get('cited')}"


def cites_recipe(result: Dict, gold_recipes: Iterable[str]) -> Check:
    c = result.get("citations") or {}
    cited = {rid for _, rid in c.get("cited", [])}
    ok = bool(cited & set(gold_recipes))
    return ok, f"cited recipes={sorted(cited)} gold={sorted(gold_recipes)}"


def contains_any(result: Dict, tokens: Iterable[str]) -> Check:
    answer = (result.get("answer") or "").lower()
    ok = any(t.lower() in answer for t in tokens)
    return ok, f"looked for any of {list(tokens)}"


def expect_answer(result: Dict, gold_recipes, tokens) -> Dict[str, Check]:
    """The full bundle for an answerable question."""
    return {
        "answered": answered(result),
        "has_expected_fact": contains_any(result, tokens),
        "citation_valid": citation_valid(result),
        "cites_gold_recipe": cites_recipe(result, gold_recipes),
    }


def expect_refusal(result: Dict) -> Dict[str, Check]:
    return {"refused": refused(result)}
