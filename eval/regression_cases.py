"""Regression cases built from the week-5 failures (taxonomy.md / notes.md).

Each CITATION_SHAPES entry is a model reply copied from a real trace, with the
citation(s) a correct extractor must recover. They exist so a shape the verifier
once dropped can never be dropped again without a test going red.
"""
import re

# The extractor as shipped through week 5 (commit b74ab31). Kept only so the
# report can show before/after on the same inputs.
LEGACY_CITATION_RE = re.compile(r"\[([A-Za-z0-9_\-]+)\s*\|\s*([A-Za-z0-9_\-]+)\]")


def legacy_extract_citations(answer):
    if not answer:
        return []
    return [(m.group(1), m.group(2)) for m in LEGACY_CITATION_RE.finditer(answer)]


CITATION_SHAPES = [
    {"id": "T07-plain", "trace": "ac25b5bd",
     "text": "Cook the eggs 6 to 8 minutes once covered. [R006-A03 | R006]",
     "expected": [("R006-A03", "R006")]},
    {"id": "T02-fullwidth", "trace": "a110140c",
     "text": "The Shakshuka provides 298 kcal per serving【R006-B06 | R006】",
     "expected": [("R006-B06", "R006")]},
    {"id": "T17-fullwidth-bold", "trace": "a0425747",
     "text": "The recipe calls for **50 g of green curry paste**【R005-B01 | R005】",
     "expected": [("R005-B01", "R005")]},
    {"id": "T10-padded", "trace": "9c9db0d4",
     "text": "The dough uses 325 ml of water [ R003-A00 | R003 ]",
     "expected": [("R003-A00", "R003")]},
    {"id": "T14-padded", "trace": "fdcb0d08",
     "text": "The curry uses 2 tablespoons of fish sauce [ R004-B01 | R004 ].",
     "expected": [("R004-B01", "R004")]},
    {"id": "T18-padded-unicode-hyphen", "trace": "59947af2",
     "text": "Use 200 g of dried chickpeas [ R002‑A00 | R002 ].",
     "expected": [("R002-A00", "R002")]},
    {"id": "T11-header-form", "trace": "6a8e7a17",
     "text": "Press the tofu for 30 minutes [chunk_id: R005-B01 | recipe_id: R005].",
     "expected": [("R005-B01", "R005")]},
    {"id": "multi", "trace": None,
     "text": "Simmer 15 minutes [R006-A02 | R006] then add eggs [ R006-A03 | R006 ].",
     "expected": [("R006-A02", "R006"), ("R006-A03", "R006")]},
    {"id": "none", "trace": None,
     "text": "I cannot answer that from the provided recipe cards.",
     "expected": []},
]
