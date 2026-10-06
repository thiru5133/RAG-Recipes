"""RAGAS-shaped faithfulness and context precision, no extra dependency.

Faithfulness: fraction of substitution claims (ingredient rows + method steps)
whose names and numbers also appear in the retrieved context. A substitution
can score 0.9 here while describing the wrong recipe, because the metric never
asks whether the context was the right recipe.

Context precision: fraction of retrieved recipe_ids that match the gold recipe.
That is the number that catches 'faithfully wrong'.
"""
from __future__ import annotations

import re
from typing import Dict, List

from assertions import INGREDIENT_LEXICON

ING_ROW_RE = re.compile(r"^\s*[-*]\s*(.+)$", re.M)
STEP_RE = re.compile(r"^\s*\d+\.\s+(.+)$", re.M)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def _claims(text: str) -> List[str]:
    claims = [m.group(1).strip() for m in ING_ROW_RE.finditer(text or "")]
    claims.extend(m.group(1).strip() for m in STEP_RE.finditer(text or ""))
    if claims:
        return [c for c in claims if len(c) > 3]
    # Unstructured (regression traces): split on sentence boundaries.
    return [s.strip() for s in re.split(r"[.!?]\s+", text or "") if len(s.strip()) > 12]


def _names_in(text: str) -> List[str]:
    lower = text.lower()
    return [name for name in INGREDIENT_LEXICON if re.search(rf"\b{re.escape(name)}\b", lower)]


def _supported(claim: str, context_lower: str) -> bool:
    names = _names_in(claim)
    numbers = NUMBER_RE.findall(claim)
    if not names and not numbers:
        words = [w for w in re.findall(r"[a-z]{4,}", claim.lower()) if w not in {"then", "with", "from", "into", "over"}]
        if not words:
            return True
        return sum(1 for w in words if w in context_lower) >= max(1, (len(words) + 1) // 2)
    hits = 0
    total = 0
    for n in names:
        total += 1
        if n.lower() in context_lower:
            hits += 1
    for n in numbers:
        total += 1
        if n in context_lower:
            hits += 1
    return hits >= max(1, (total + 1) // 2)


def faithfulness(substitution: str, context: str) -> Dict:
    claims = _claims(substitution)
    if not claims:
        return {"score": 0.0, "n_claims": 0, "n_supported": 0}
    ctx = (context or "").lower()
    n_supported = sum(1 for c in claims if _supported(c, ctx))
    return {
        "score": round(n_supported / len(claims), 3),
        "n_claims": len(claims),
        "n_supported": n_supported,
    }


def context_precision(retrieved_recipe_ids: List[str], gold_recipe: str) -> Dict:
    if not retrieved_recipe_ids:
        return {"score": 0.0, "n_relevant": 0, "n": 0}
    n_rel = sum(1 for r in retrieved_recipe_ids if r == gold_recipe)
    return {
        "score": round(n_rel / len(retrieved_recipe_ids), 3),
        "n_relevant": n_rel,
        "n": len(retrieved_recipe_ids),
    }


def score_item(item: Dict) -> Dict:
    faith = faithfulness(item["substitution"], item.get("context") or "")
    prec = context_precision(item.get("retrieved_recipe_ids") or [], item.get("gold_recipe") or "")
    return {"qid": item["qid"], "faithfulness": faith, "context_precision": prec}
