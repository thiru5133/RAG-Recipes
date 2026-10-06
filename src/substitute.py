"""Generate a structured recipe substitution from retrieved cards.

Used only when someone regenerates the frozen eval set. The Week-6 numbers are
scored on `eval/substitutions.py` frozen_text, not on a live call, so a new
generation cannot silently invalidate the blind labels.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from generate import complete
from retrieve import search

SYSTEM = """You rewrite a recipe to honour one substitution constraint.

Output exactly this shape and nothing else:

CONSTRAINT: <the constraint>
RECIPE: <title> (<id>)
SERVINGS: <integer>
ALLERGEN_WARNING: <allergen classes present after the swap, or none>
INGREDIENTS:
- <name> | <number> | <unit> | <notes>
METHOD:
1. ...
OVEN: <temperature with C or F, or none>

Rules:
- Use ONLY the context chunks. If they do not contain the swap, output the
  single sentence: I cannot answer that from the provided recipe cards.
- Every ingredient named in METHOD must appear in INGREDIENTS.
- If an allergen (nuts, dairy, fish, shellfish, egg, gluten) remains in
  INGREDIENTS, name it in ALLERGEN_WARNING.
- Quantities are numbers. SERVINGS is the source card's serving count.
- Do not invent a swap the notes do not support.
"""


def generate_substitution(
    request: str,
    constraint: str,
    hits: Optional[List[Dict]] = None,
    strategy: str = "structured",
    mode: str = "semantic",
    k: int = 5,
) -> Dict:
    if hits is None:
        hits = search(request, strategy=strategy, mode=mode, k=k)
    blocks = []
    for h in hits:
        meta = h.get("metadata") or {}
        blocks.append(
            f"[{h['chunk_id']} | {meta.get('recipe_id', '?')} | {meta.get('section', '?')}]\n"
            f"{h['text']}"
        )
    user = (
        f"Context:\n\n" + "\n\n---\n\n".join(blocks) + "\n\n"
        f"Request: {request}\n"
        f"Constraint: {constraint}\n"
        "Rewrite the recipe to honour the constraint."
    )
    result = complete(SYSTEM, user, max_tokens=900)
    return {
        "substitution": result.get("answer"),
        "error": result.get("error"),
        "hits": hits,
        "latency_ms": result.get("latency_ms"),
    }
