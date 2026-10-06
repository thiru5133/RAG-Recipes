"""Fixed workflow: the same three tools, the same model, the same JSON contract.

Hard-coded steps. No agent loop. One get_allergen_profile call if a restriction
is present — it does not inspect `introduces` / `leaves`, so allergen-cascade
requests miss the second swap.
"""
from __future__ import annotations

import re
import time
from typing import Dict, List, Tuple

from config import GROQ_MODEL, GROQ_PRICE_INPUT_PER_M, GROQ_PRICE_OUTPUT_PER_M
from agent.contract import cost_usd, empty_result
from agent.tools import get_allergen_profile, scale_recipe, search_recipes

# First keyword wins. Vegan is not an enum on the tool; it maps to dairy so the
# workflow still makes exactly one profile call (the cascade cases then fail).
KEYWORD_ALLERGEN = [
    ("gluten-free", "gluten"),
    ("gluten free", "gluten"),
    ("nut-free", "nuts"),
    ("nut free", "nuts"),
    ("dairy-free", "dairy"),
    ("dairy free", "dairy"),
    ("vegan", "dairy"),
    ("vegetarian", "meat"),
    ("egg-free", "egg"),
    ("no egg", "egg"),
    ("fish", "fish"),
    ("shellfish", "shellfish"),
]


def parse_slots(text: str) -> Dict:
    low = text.lower()
    allergen = None
    for kw, al in KEYWORD_ALLERGEN:
        if kw in low:
            allergen = al
            break
    servings = None
    m = re.search(r"\bfor\s+(\d+)\b", low)
    if m:
        servings = int(m.group(1))
    if servings is None:
        m = re.search(r"\bto\s+(\d+)\s+servings?\b", low)
        if m:
            servings = int(m.group(1))
    if servings is None:
        m = re.search(r"\b(\d+)\s+servings?\b", low)
        if m:
            servings = int(m.group(1))
    return {"query": text, "servings": servings, "allergen": allergen}


def apply_swap(ingredients: List[Dict], profile: Dict) -> Tuple[List[Dict], List[str], List[str]]:
    warnings: List[str] = []
    swaps: List[str] = []
    if profile.get("cannot_adapt"):
        warnings.append(profile.get("reason") or "cannot adapt")
        return ingredients, swaps, warnings
    changes = profile.get("card_swap") or []
    if not changes:
        if profile.get("reason"):
            warnings.append(profile["reason"])
        return ingredients, swaps, warnings

    out = []
    for row in ingredients:
        name = (row.get("name") or "").lower()
        hit = next(
            (c for c in changes if c["from"].lower() in name),
            None,
        )
        if not hit:
            out.append(row)
            continue
        swaps.append(f"{hit['from']} → {hit['to']}")
        if hit["to"].lower().startswith("omit"):
            continue
        new = dict(row)
        new["name"] = hit["to"]
        new["notes"] = hit.get("note", row.get("notes", ""))
        out.append(new)
    return out, swaps, warnings


def run_workflow(request_text: str, model: str = GROQ_MODEL) -> Dict:
    started = time.perf_counter()
    log: List[str] = []
    prompt_tokens = completion_tokens = 0
    slots = parse_slots(request_text)
    log.append(f"PARSE servings={slots['servings']} allergen={slots['allergen']}")

    # Step 1 — search (tool, not a model decision)
    found = search_recipes(slots["query"])
    match = (found.get("matches") or [{}])[0]
    recipe_id = match.get("recipe_id")
    log.append(f"TOOL search_recipes -> {recipe_id}")

    servings = slots["servings"] or match.get("base_servings") or 4

    # Step 2 — scale
    scaled = scale_recipe(recipe_id, int(servings))
    log.append(f"TOOL scale_recipe {recipe_id} servings={servings}")

    ingredients = list(scaled.get("ingredients") or [])
    method = list(scaled.get("method") or [])
    swaps: List[str] = []
    warnings: List[str] = []

    # Step 3 — at most ONE allergen profile. No loop. Cascades stop here.
    if slots["allergen"]:
        profile = get_allergen_profile(recipe_id, slots["allergen"])
        log.append(
            f"TOOL get_allergen_profile {recipe_id} {slots['allergen']} "
            f"introduces={profile.get('introduces')} leaves={profile.get('leaves')}"
        )
        ingredients, swaps, warnings = apply_swap(ingredients, profile)

    assembled = {
        "recipe_id": recipe_id,
        "title": scaled.get("title") or match.get("title"),
        "servings": int(servings),
        "ingredients": ingredients,
        "method": method,
        "swaps_applied": swaps,
        "warnings": warnings,
    }
    result = assembled
    log.append("ASSEMBLE python (no extra model call)")

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    spent = cost_usd(
        prompt_tokens, completion_tokens,
        GROQ_PRICE_INPUT_PER_M, GROQ_PRICE_OUTPUT_PER_M,
    )
    return {
        "system": "workflow",
        "result": {**empty_result(), **result},
        "stopped_by": "completed",
        "laps": 1,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tokens": prompt_tokens + completion_tokens,
        "cost_usd": spent,
        "latency_ms": elapsed_ms,
        "log": log,
    }
