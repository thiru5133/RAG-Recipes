"""Output contract shared by the agent and the workflow, plus the pass check."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

CONTRACT_KEYS = [
    "recipe_id",
    "title",
    "servings",
    "ingredients",
    "method",
    "swaps_applied",
    "warnings",
]


def empty_result() -> Dict:
    return {k: ([] if k in {"ingredients", "method", "swaps_applied", "warnings"} else None)
            for k in CONTRACT_KEYS}


def extract_json(text: str) -> Optional[Dict]:
    if not text:
        return None
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def ingredient_blob(result: Dict) -> str:
    parts = []
    for row in result.get("ingredients") or []:
        if isinstance(row, dict):
            parts.append(str(row.get("name", "")))
        else:
            parts.append(str(row))
    return " ".join(parts).lower()


def passes(result: Optional[Dict], spec: Dict) -> bool:
    if not result:
        return False
    if result.get("recipe_id") != spec["gold_recipe"]:
        return False
    try:
        if int(result.get("servings") or 0) != int(spec["servings"]):
            return False
    except (TypeError, ValueError):
        return False
    method = result.get("method") or []
    if not method:
        return False
    blob = ingredient_blob(result)
    warnings = " ".join(str(w) for w in (result.get("warnings") or [])).lower()
    if spec.get("must_warn"):
        return bool(warnings.strip())
    for token in spec.get("forbidden") or []:
        if token.lower() in blob:
            return False
    for token in spec.get("required") or []:
        if token.lower() not in blob and token.lower() not in warnings:
            return False
    return True


def cost_usd(prompt_tokens: int, completion_tokens: int, input_per_m: float, output_per_m: float) -> float:
    return round(
        (prompt_tokens / 1_000_000.0) * input_per_m
        + (completion_tokens / 1_000_000.0) * output_per_m,
        6,
    )
