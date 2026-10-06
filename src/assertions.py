"""Deterministic checks that used to live in the LLM judge prompt.

An `if` never has an off day. These five run on every substitution before the
judge is asked the one question it is actually for: does the swap honour the
constraint.

Skipped (applicable=False) rather than failed when the substitution has no
oven, or is a gate-refusal with no ingredient list — a refusal is scored by
the judge, not by pretending it had a 250 C line.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Longest first so "fish sauce" matches before "fish", "coconut cream" before "cream".
INGREDIENT_LEXICON = sorted(
    {
        "extra-firm tofu",
        "tofu",
        "tempeh",
        "paneer",
        "raw cashews",
        "cashews",
        "melon seeds",
        "heavy cream",
        "coconut cream",
        "coconut milk",
        "unsalted butter",
        "butter",
        "neutral oil",
        "olive oil",
        "fish sauce",
        "light soy sauce",
        "soy sauce",
        "white miso paste",
        "miso",
        "green curry paste",
        "vegan green curry paste",
        "chicken breast",
        "chicken thigh",
        "chicken stock",
        "vegetable stock",
        "palm sugar",
        "thai aubergines",
        "aubergine",
        "bamboo shoots",
        "makrut lime leaves",
        "lime leaves",
        "thai basil",
        "basil leaves",
        "fresh basil",
        "fresh mozzarella",
        "mozzarella",
        "feta cheese",
        "feta",
        "large eggs",
        "eggs",
        "chickpeas",
        "tinned chickpeas",
        "dried chickpeas",
        "amchur",
        "lemon juice",
        "garam masala",
        "fenugreek leaves",
        "cumin seeds",
        "coriander powder",
        "fresh coriander",
        "fresh parsley",
        "type 00 flour",
        "rice flour",
        "semolina flour",
        "sourdough starter",
        "fresh yeast",
        "san marzano tomatoes",
        "ripe tomatoes",
        "tomatoes",
        "red bell peppers",
        "onion",
        "garlic cloves",
        "garlic",
        "fresh ginger",
        "ginger",
        "green chillies",
        "red chilli",
        "kashmiri chilli powder",
        "sweet paprika",
        "ground cumin",
        "caraway seeds",
        "cayenne pepper",
        "turmeric",
        "granulated sugar",
        "fine sea salt",
        "salt",
        "water",
    },
    key=len,
    reverse=True,
)

ALLERGEN_IN_LIST = [
    (re.compile(r"\bcashews?\b", re.I), "nuts"),
    (re.compile(r"\bpaneer\b", re.I), "dairy"),
    (re.compile(r"\b(heavy cream|unsalted butter|butter|mozzarella|feta)\b", re.I), "dairy"),
    (re.compile(r"\bfish sauce\b", re.I), "fish"),
    (re.compile(r"\bshrimp\b", re.I), "shellfish"),
    (re.compile(r"\b(eggs?|feta cheese)\b", re.I), "egg"),
    (re.compile(r"\b(type 00 flour|semolina flour|gluten)\b", re.I), "gluten"),
]

ALLERGEN_IN_WARNING = {
    "nuts": re.compile(r"\b(nuts?|cashews?)\b", re.I),
    "dairy": re.compile(r"\b(dairy|milk|butter|cream|cheese)\b", re.I),
    "fish": re.compile(r"\b(fish)\b", re.I),
    "shellfish": re.compile(r"\b(shellfish|shrimp|prawn)\b", re.I),
    "egg": re.compile(r"\b(eggs?)\b", re.I),
    "gluten": re.compile(r"\b(gluten|wheat|flour)\b", re.I),
}
NAME_LINE_RE = re.compile(r"^\s*[-*]\s*([^|\n]+)\|", re.M)

SERVINGS_RE = re.compile(r"SERVINGS:\s*(\d+)", re.I)
WARNING_RE = re.compile(r"ALLERGEN_WARNING:\s*(.+)", re.I)
INGREDIENTS_RE = re.compile(
    r"INGREDIENTS:\s*(.*?)\n(?:METHOD:|OVEN:)", re.I | re.S
)
METHOD_RE = re.compile(r"METHOD:\s*(.*?)\n(?:OVEN:|$)", re.I | re.S)
OVEN_FIELD_RE = re.compile(r"OVEN:\s*(.+)", re.I)
TEMP_UNITS_RE = re.compile(
    r"\d+\s*(?:°\s*)?(?:C|F)\b|\d+\s*degrees",
    re.I,
)
OVEN_TALK_RE = re.compile(r"\b(oven|preheat|bake|pizza stone)\b", re.I)
ING_LINE_RE = re.compile(
    r"^\s*[-*]\s*[^|\n]+\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|",
    re.M,
)
REFUSAL_RE = re.compile(r"i cannot answer that", re.I)

ASSERTION_NAMES = [
    "method_ingredients_listed",
    "allergen_warning_present",
    "oven_temp_units",
    "servings_echoed",
    "quantities_numeric",
]


def _section(text: str, regex: re.Pattern) -> str:
    m = regex.search(text)
    return m.group(1).strip() if m else ""


def _ingredient_names(text: str) -> str:
    """Name column only. Notes like 'replaces fish sauce' must not trip allergens."""
    return "\n".join(m.group(1).strip() for m in NAME_LINE_RE.finditer(text))


def _lexicon_hits(text: str) -> List[str]:
    found = []
    lower = text.lower()
    used_spans: List[Tuple[int, int]] = []
    for name in INGREDIENT_LEXICON:
        start = 0
        while True:
            idx = lower.find(name, start)
            if idx < 0:
                break
            end = idx + len(name)
            if any(idx < s_end and end > s_start for s_start, s_end in used_spans):
                start = end
                continue
            left_ok = idx == 0 or not lower[idx - 1].isalnum()
            right_ok = end == len(lower) or not lower[end].isalnum()
            if left_ok and right_ok:
                found.append(name)
                used_spans.append((idx, end))
                break
            start = end
    return found


def method_ingredients_listed(text: str) -> Dict:
    if REFUSAL_RE.search(text):
        return {
            "name": "method_ingredients_listed",
            "applicable": False,
            "passed": True,
            "detail": "refusal — no method to check",
        }
    ingredients = _section(text, INGREDIENTS_RE)
    method = _section(text, METHOD_RE)
    if not ingredients or not method:
        return {
            "name": "method_ingredients_listed",
            "applicable": True,
            "passed": False,
            "detail": "unstructured substitution — no INGREDIENTS/METHOD blocks",
        }
    missing = []
    for name in _lexicon_hits(method):
        if name not in ingredients.lower():
            missing.append(name)
    return {
        "name": "method_ingredients_listed",
        "applicable": True,
        "passed": not missing,
        "detail": "ok" if not missing else f"in method but not listed: {missing}",
    }


def allergen_warning_present(text: str) -> Dict:
    if REFUSAL_RE.search(text):
        return {
            "name": "allergen_warning_present",
            "applicable": False,
            "passed": True,
            "detail": "refusal — no ingredient list",
        }
    ingredients = _section(text, INGREDIENTS_RE)
    if not ingredients:
        return {
            "name": "allergen_warning_present",
            "applicable": True,
            "passed": False,
            "detail": "no INGREDIENTS block to scan",
        }
    names = _ingredient_names(ingredients)
    warning = _section(text, WARNING_RE)
    present = []
    for pat, label in ALLERGEN_IN_LIST:
        if pat.search(names) and label not in present:
            present.append(label)
    if not present:
        return {
            "name": "allergen_warning_present",
            "applicable": True,
            "passed": True,
            "detail": "no tracked allergen in the list",
        }
    missing = [a for a in present if not ALLERGEN_IN_WARNING[a].search(warning)]
    return {
        "name": "allergen_warning_present",
        "applicable": True,
        "passed": not missing,
        "detail": "ok" if not missing else f"allergens {missing} not named in warning {warning!r}",
    }


def oven_temp_units(text: str) -> Dict:
    oven_field = _section(text, OVEN_FIELD_RE)
    method = _section(text, METHOD_RE) or text
    talks_oven = bool(OVEN_TALK_RE.search(method) or OVEN_TALK_RE.search(oven_field))
    if oven_field.lower() in {"none", "n/a", ""} and not talks_oven:
        return {
            "name": "oven_temp_units",
            "applicable": False,
            "passed": True,
            "detail": "no oven step",
        }
    blob = f"{oven_field}\n{method}"
    ok = bool(TEMP_UNITS_RE.search(blob))
    return {
        "name": "oven_temp_units",
        "applicable": True,
        "passed": ok,
        "detail": "ok" if ok else f"oven mentioned but no unit on the temperature: {oven_field!r}",
    }


def servings_echoed(text: str, expected: Optional[int]) -> Dict:
    if REFUSAL_RE.search(text):
        return {
            "name": "servings_echoed",
            "applicable": False,
            "passed": True,
            "detail": "refusal — no servings line expected",
        }
    m = SERVINGS_RE.search(text)
    if not m:
        return {
            "name": "servings_echoed",
            "applicable": True,
            "passed": False,
            "detail": "no SERVINGS: N line",
        }
    got = int(m.group(1))
    ok = expected is None or got == int(expected)
    return {
        "name": "servings_echoed",
        "applicable": True,
        "passed": ok,
        "detail": "ok" if ok else f"SERVINGS {got} != expected {expected}",
    }


def quantities_numeric(text: str) -> Dict:
    if REFUSAL_RE.search(text):
        return {
            "name": "quantities_numeric",
            "applicable": False,
            "passed": True,
            "detail": "refusal — no quantities",
        }
    lines = ING_LINE_RE.findall(text)
    if not lines:
        return {
            "name": "quantities_numeric",
            "applicable": True,
            "passed": False,
            "detail": "no parseable `name | number | unit` ingredient rows",
        }
    return {
        "name": "quantities_numeric",
        "applicable": True,
        "passed": True,
        "detail": f"{len(lines)} numeric quantities",
    }


def run_assertions(text: str, servings_expected: Optional[int] = None) -> Dict:
    checks = [
        method_ingredients_listed(text),
        allergen_warning_present(text),
        oven_temp_units(text),
        servings_echoed(text, servings_expected),
        quantities_numeric(text),
    ]
    applicable = [c for c in checks if c["applicable"]]
    passed = all(c["passed"] for c in applicable)
    return {
        "passed": passed,
        "n_assertions": len(ASSERTION_NAMES),
        "n_applicable": len(applicable),
        "n_applicable_passed": sum(1 for c in applicable if c["passed"]),
        "checks": checks,
    }
