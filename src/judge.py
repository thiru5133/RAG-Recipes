"""LLM judge for one binary criterion: does the substitution honour the constraint.

Formatting, allergen-warning strings, oven units, servings echoes and numeric
quantities are not this model's job — `assertions.py` already ran those.

v1 is the prompt with no examples. v2 is the same prompt plus two of v1's own
disagreements as few-shots. Prompts live in eval/week6/judge_v1.txt and
judge_v2.txt so the diff is a file, not a comment.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

from config import ROOT
from generate import complete

WEEK6_DIR = ROOT / "eval" / "week6"
VERDICT_RE = re.compile(r"VERDICT:\s*(PASS|FAIL)", re.I)
BARE_RE = re.compile(r"\b(PASS|FAIL)\b", re.I)


def parse_verdict(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = VERDICT_RE.search(text)
    if m:
        return m.group(1).upper()
    hits = BARE_RE.findall(text)
    return hits[-1].upper() if hits else None


JUDGED_CRITERIA = 1
CRITERION = (
    "Does this substitution honour the stated CONSTRAINT without introducing a "
    "new allergen or dietary hazard, and without contradicting a swap the source "
    "recipe card already specifies?"
)


def load_prompt(version: str) -> str:
    path = WEEK6_DIR / f"judge_{version}.txt"
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def build_user_prompt(item: Dict) -> str:
    return (
        f"CONSTRAINT: {item['constraint']}\n"
        f"REQUEST: {item['request']}\n"
        f"SOURCE RECIPE: {item.get('recipe_title', item.get('recipe_id'))} "
        f"({item.get('gold_recipe') or item.get('recipe_id')})\n"
        f"SOURCE CARD (notes / relevant lines):\n{item.get('context', '').strip()}\n\n"
        f"SUBSTITUTION:\n{item['substitution']}\n"
    )


def judge_one(item: Dict, prompt: str, model: Optional[str] = None) -> Dict:
    user = build_user_prompt(item)
    kwargs = {"max_tokens": 800}
    if model:
        kwargs["model"] = model
    result = complete(prompt, user, **kwargs)
    raw = result.get("answer")
    return {
        "qid": item["qid"],
        "verdict": parse_verdict(raw),
        "raw": raw,
        "error": result.get("error"),
        "latency_ms": result.get("latency_ms"),
    }
