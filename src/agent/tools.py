"""Three recipe-adaptation tools. One job each. Descriptions do not overlap.

1. search_recipes  — match a dish query to a recipe_id. No ingredients, no scale.
2. scale_recipe    — multiply quantities to a serving count. No search, no swap.
3. get_allergen_profile — ONE allergen/diet enum on ONE recipe. No search, no scale.

The third tool is the one Week 7 adds. Its schema is the diff in
eval/week7/tool_description.diff.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Dict, List, Optional

from loader import load_corpus

RECIPE_IDS = ["R001", "R002", "R003", "R004", "R005", "R006"]
ALLERGENS = ["nuts", "dairy", "gluten", "fish", "shellfish", "egg", "meat"]

# Name-column substrings on the ingredient table. Notes text is ignored.
ALLERGEN_TERMS = {
    "nuts": ["cashew"],
    "dairy": ["paneer", "butter", "heavy cream", "mozzarella", "feta"],
    "gluten": ["type 00 flour", "semolina", "soy sauce"],
    "fish": ["fish sauce"],
    "shellfish": ["shrimp"],
    "egg": ["egg"],
    "meat": ["chicken thigh", "chicken breast", "chicken stock"],
}

# Card-specified swaps. `introduces` is the cascade hook: the substitute itself
# carries another allergen, so a second get_allergen_profile call is required.
SWAPS = {
    ("R001", "dairy"): {
        "changes": [
            {"from": "Paneer", "to": "extra-firm tofu", "note": "same weight, pressed 30 minutes"},
            {"from": "Unsalted butter", "to": "neutral oil", "note": "same weight"},
            {"from": "Heavy cream", "to": "coconut cream", "note": "same volume, off the heat"},
        ],
        "cannot": False,
        "introduces": [],
        "leaves": ["nuts"],
    },
    ("R001", "nuts"): {
        "changes": [
            {"from": "Raw cashews", "to": "melon seeds", "note": "2 tbsp soaked, as the card specifies"},
        ],
        "cannot": False,
        "introduces": [],
        "leaves": [],
    },
    ("R002", "dairy"): {"changes": [], "cannot": False, "introduces": [], "leaves": [],
                        "note": "already vegan, no dairy on the card"},
    ("R003", "gluten"): {
        "changes": [],
        "cannot": True,
        "reason": "Card: cannot be made gluten-free without changing the dough entirely.",
        "introduces": [],
        "leaves": [],
    },
    ("R003", "dairy"): {
        "changes": [
            {"from": "Fresh mozzarella", "to": "omit mozzarella", "note": "card has no dairy-free cheese swap"},
        ],
        "cannot": False,
        "introduces": [],
        "leaves": ["gluten"],
    },
    ("R004", "fish"): {
        "changes": [
            {"from": "Fish sauce", "to": "light soy sauce", "note": "2 tbsp, as on the vegan card"},
        ],
        "cannot": False,
        "introduces": ["gluten"],
        "leaves": ["meat", "shellfish"],
    },
    ("R004", "meat"): {
        "changes": [
            {"from": "Chicken thigh", "to": "extra-firm tofu", "note": "400 g, see the tofu version"},
            {"from": "Chicken stock", "to": "vegetable stock", "note": "same volume"},
        ],
        "cannot": False,
        "introduces": [],
        "leaves": ["fish", "shellfish"],
    },
    ("R004", "shellfish"): {
        "changes": [
            {"from": "Green curry paste", "to": "vegan-certified green curry paste",
             "note": "supermarket paste usually contains shrimp"},
        ],
        "cannot": False,
        "introduces": [],
        "leaves": [],
    },
    ("R004", "gluten"): {
        "changes": [
            {"from": "light soy sauce", "to": "gluten-free tamari", "note": "same volume, wheat-free"},
        ],
        "cannot": False,
        "introduces": [],
        "leaves": [],
    },
    ("R005", "fish"): {"changes": [], "cannot": False, "introduces": [], "leaves": [],
                       "note": "already uses soy + miso, no fish sauce"},
    ("R006", "egg"): {
        "changes": [
            {"from": "Large eggs", "to": "chickpeas", "note": "two 400 g tins, simmer 10 minutes"},
        ],
        "cannot": False,
        "introduces": [],
        "leaves": ["dairy"],
    },
    ("R006", "dairy"): {
        "changes": [
            {"from": "Feta cheese", "to": "omit feta", "note": "card's vegan version omits it"},
        ],
        "cannot": False,
        "introduces": [],
        "leaves": ["egg"],
    },
}


def _section(recipe, name: str) -> str:
    for s in recipe.sections:
        if s.name == name:
            return s.text
    return ""


def _parse_ingredients(recipe) -> List[Dict]:
    rows = []
    for line in _section(recipe, "Ingredients").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() in {"ingredient", "---"} or set(cells[0]) <= {"-"}:
            continue
        try:
            qty = float(cells[1])
        except ValueError:
            qty = None
        rows.append(
            {
                "name": cells[0],
                "quantity": qty,
                "quantity_raw": cells[1],
                "unit": cells[2],
                "notes": cells[3] if len(cells) > 3 else "",
            }
        )
    return rows


def _parse_method(recipe) -> List[str]:
    steps = []
    for line in _section(recipe, "Method").splitlines():
        m = re.match(r"\s*\d+\.\s+(.*)", line)
        if m:
            steps.append(m.group(1).strip())
        elif steps and line.strip():
            steps[-1] = steps[-1] + " " + line.strip()
    return steps


@lru_cache(maxsize=1)
def catalog() -> Dict[str, Dict]:
    out = {}
    for r in load_corpus():
        try:
            servings = int(str(r.servings).split()[0])
        except (TypeError, ValueError):
            servings = 4
        out[r.recipe_id] = {
            "recipe_id": r.recipe_id,
            "title": r.title,
            "cuisine": r.cuisine,
            "dietary_tags": list(r.dietary_tags),
            "base_servings": servings,
            "ingredients": _parse_ingredients(r),
            "method": _parse_method(r),
            "notes": _section(r, "Notes"),
        }
    return out


def _hits_allergen(name: str, allergen: str) -> bool:
    low = name.lower()
    return any(term in low for term in ALLERGEN_TERMS.get(allergen, []))


# ── schemas (Groq/OpenAI tools format) ──────────────────────────────────────

SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_recipes",
        "description": (
            "Match a dish name or cuisine word to a recipe_id in the six-card "
            "corpus. Returns id, title, base servings and dietary tags. "
            "Does not return ingredient rows, method steps, nutrition, or swaps."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Dish name or cuisine keyword, e.g. 'paneer butter masala'.",
                }
            },
            "required": ["query"],
        },
    },
}

SCALE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "scale_recipe",
        "description": (
            "Multiply every ingredient quantity on one recipe from its base "
            "servings to a target serving count. Returns the scaled ingredient "
            "table and the original method steps. "
            "Does not search the corpus, does not inspect allergens, does not swap."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "recipe_id": {
                    "type": "string",
                    "enum": RECIPE_IDS,
                    "description": "Card id from search_recipes.",
                },
                "servings": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Target serving count.",
                },
            },
            "required": ["recipe_id", "servings"],
        },
    },
}

ALLERGEN_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_allergen_profile",
        "description": (
            "List the ingredients on one recipe that carry a SINGLE named "
            "allergen or diet restriction, and the swap the card itself writes "
            "if it writes one. Call again with a different enum value if the "
            "swap introduces another allergen (see 'introduces' / 'leaves'). "
            "Does not search, does not scale quantities, does not rewrite the method."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "recipe_id": {
                    "type": "string",
                    "enum": RECIPE_IDS,
                },
                "allergen": {
                    "type": "string",
                    "enum": ALLERGENS,
                    "description": "Exactly one class per call.",
                },
            },
            "required": ["recipe_id", "allergen"],
        },
    },
}

TWO_TOOL_SCHEMAS = [SEARCH_SCHEMA, SCALE_SCHEMA]
THREE_TOOL_SCHEMAS = [SEARCH_SCHEMA, SCALE_SCHEMA, ALLERGEN_SCHEMA]


# ── implementations ─────────────────────────────────────────────────────────

def search_recipes(query: str) -> Dict:
    q = (query or "").lower()
    scored = []
    for card in catalog().values():
        blob = " ".join(
            [card["recipe_id"], card["title"], card["cuisine"], " ".join(card["dietary_tags"])]
        ).lower()
        tokens = [t for t in re.findall(r"[a-z0-9]+", q) if len(t) > 2]
        score = sum(1 for t in tokens if t in blob)
        if card["recipe_id"].lower() in q:
            score += 5
        scored.append((score, card))
    scored.sort(key=lambda x: x[0], reverse=True)
    hits = [
        {
            "recipe_id": c["recipe_id"],
            "title": c["title"],
            "base_servings": c["base_servings"],
            "dietary_tags": c["dietary_tags"],
            "score": s,
        }
        for s, c in scored
        if s > 0
    ][:3]
    if not hits:
        # still return the best title overlap so the agent has somewhere to go
        top = scored[0][1]
        hits = [{
            "recipe_id": top["recipe_id"],
            "title": top["title"],
            "base_servings": top["base_servings"],
            "dietary_tags": top["dietary_tags"],
            "score": 0,
        }]
    return {"matches": hits}


def scale_recipe(recipe_id: str, servings: int) -> Dict:
    card = catalog().get(recipe_id)
    if not card:
        return {"error": f"unknown recipe_id {recipe_id}"}
    base = card["base_servings"] or 1
    factor = float(servings) / float(base)
    scaled = []
    for row in card["ingredients"]:
        qty = row["quantity"]
        scaled.append(
            {
                "name": row["name"],
                "quantity": round(qty * factor, 2) if qty is not None else row["quantity_raw"],
                "unit": row["unit"],
                "notes": row["notes"],
            }
        )
    return {
        "recipe_id": recipe_id,
        "title": card["title"],
        "base_servings": base,
        "servings": int(servings),
        "factor": round(factor, 4),
        "ingredients": scaled,
        "method": list(card["method"]),
    }


def get_allergen_profile(recipe_id: str, allergen: str) -> Dict:
    if allergen not in ALLERGENS:
        return {"error": f"allergen must be one of {ALLERGENS}"}
    card = catalog().get(recipe_id)
    if not card:
        return {"error": f"unknown recipe_id {recipe_id}"}
    present = [row["name"] for row in card["ingredients"] if _hits_allergen(row["name"], allergen)]
    # soy sauce only counts as gluten when it is actually on the card (R005) or
    # after a fish→soy swap (signalled via SWAPS introduces, not the raw table).
    if allergen == "gluten" and recipe_id == "R004":
        present = [n for n in present if "soy" not in n.lower()]
    spec = SWAPS.get((recipe_id, allergen), {
        "changes": [],
        "cannot": False,
        "introduces": [],
        "leaves": [],
        "note": "no swap written on this card for that class",
    })
    return {
        "recipe_id": recipe_id,
        "allergen": allergen,
        "present": present,
        "cannot_adapt": bool(spec.get("cannot")),
        "reason": spec.get("reason") or spec.get("note") or "",
        "card_swap": spec.get("changes") or [],
        "introduces": list(spec.get("introduces") or []),
        "leaves": list(spec.get("leaves") or []),
    }


DISPATCH = {
    "search_recipes": lambda args: search_recipes(args.get("query", "")),
    "scale_recipe": lambda args: scale_recipe(args.get("recipe_id", ""), int(args.get("servings") or 1)),
    "get_allergen_profile": lambda args: get_allergen_profile(
        args.get("recipe_id", ""), args.get("allergen", "")
    ),
}


def run_tool(name: str, args: Dict) -> Dict:
    fn = DISPATCH.get(name)
    if not fn:
        return {"error": f"unknown tool {name}"}
    try:
        return fn(args)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def schemas_to_json(schemas: List[Dict]) -> str:
    return json.dumps(schemas, indent=2)
