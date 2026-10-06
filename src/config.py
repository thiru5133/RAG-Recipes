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
RRF_K = 60  # Reciprocal Rank Fusion constant

# Second-stage rerank: retrieve this many candidates, then cut back to k.
RERANK_CANDIDATES = 20
# Tighter than first-stage RRF_K: the pool is small, so rank gaps must count.
RERANK_RRF_K = 10

# Refusal gate: if the best chunk scores below this cosine similarity, refuse
# before spending an LLM call. Calibrated in results.md from the observed score
# distribution over the 8 answerable questions.
REFUSAL_THRESHOLD = 0.30

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
# Week-7 loop can use a smaller Groq model if the 120b day-cap is gone.
# Same model for agent and workflow (workflow may make zero calls).
WEEK7_MODEL = os.environ.get("WEEK7_MODEL", "openai/gpt-oss-20b")
WEEK8_MODEL = os.environ.get("WEEK8_MODEL", WEEK7_MODEL)

# Groq list prices USD / 1M tokens (console.groq.com/docs/models, 2026-09-20)
GROQ_PRICES = {
    "openai/gpt-oss-120b": (0.15, 0.60),
    "openai/gpt-oss-20b": (0.075, 0.30),
}
GROQ_PRICE_INPUT_PER_M = float(os.environ.get("GROQ_PRICE_INPUT_PER_M", "0.15"))
GROQ_PRICE_OUTPUT_PER_M = float(os.environ.get("GROQ_PRICE_OUTPUT_PER_M", "0.60"))

# Agent-loop budgets. All four are checked every lap in src/agent/loop.py.
AGENT_MAX_ITERS = int(os.environ.get("AGENT_MAX_ITERS", "8"))
AGENT_MAX_TOKENS = int(os.environ.get("AGENT_MAX_TOKENS", "12000"))
AGENT_MAX_COST_USD = float(os.environ.get("AGENT_MAX_COST_USD", "0.05"))
AGENT_MAX_WALL_MS = int(os.environ.get("AGENT_MAX_WALL_MS", "60000"))


