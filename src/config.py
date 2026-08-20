"""Shared paths and tunable defaults."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECIPE_DIR = ROOT / "data" / "recipes"
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", ROOT / ".chroma"))
RESULTS_DIR = ROOT / "results"

# Strategy A (basic) defaults
BASIC_CHUNK_SIZE = 500
BASIC_OVERLAP = 80

# Strategy B (structure-aware) defaults
STRUCT_MAX_CHARS = 700
STRUCT_ROWS_PER_CHUNK = 8
STRUCT_OVERLAP_ROWS = 1

COLLECTION_BASIC = "recipes_basic"
COLLECTION_STRUCTURED = "recipes_structured"

STRATEGIES = {
    "basic": COLLECTION_BASIC,
    "structured": COLLECTION_STRUCTURED,
}

TOP_K = 5

# Refusal gate: if the best chunk scores below this cosine similarity, refuse
# before spending an LLM call. Calibrated in results.md from the observed score
# distribution over the 8 answerable questions.
REFUSAL_THRESHOLD = 0.30

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


