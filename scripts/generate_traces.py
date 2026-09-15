"""generate_traces.py — Synthetic trace log generator for Week 5 error analysis.

Generates 1000+ realistic traces that replicate the actual failure modes the
recipe RAG system exhibits in production: quantity confusion between near-duplicate
recipes, cross-recipe attribution, low-confidence refusals fired on answerable
questions, hallucinated quantities, and missing citations.

Each trace record contains every field required for a replay:
  trace_id, timestamp, question, prompt_version, model, model_params,
  strategy, mode, k, rerank, retrieved_chunks (chunk_id + score), raw_output,
  answer, refused, refusal_reason, citations, latency_ms.

Run: python scripts/generate_traces.py
Output: traces/traces.jsonl  (~1200 traces)
"""
from __future__ import annotations

import json
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

TRACES_DIR = ROOT / "traces"
TRACES_DIR.mkdir(exist_ok=True)
OUT = TRACES_DIR / "traces.jsonl"

# ── deterministic seed for reproducibility ───────────────────────────────────
GENERATION_SEED = 20260915
rng = random.Random(GENERATION_SEED)

PROMPT_VERSION = "v1.2.0"
MODEL = "openai/gpt-oss-120b"
MODEL_PARAMS = {"temperature": 0, "max_tokens": 400}

# ── corpus facts ─────────────────────────────────────────────────────────────
RECIPES = {
    "R001": ("Paneer Butter Masala", "Indian"),
    "R002": ("Chana Masala", "Indian"),
    "R003": ("Classic Margherita Pizza", "Italian"),
    "R004": ("Thai Green Curry with Chicken", "Thai"),
    "R005": ("Vegan Thai Green Curry with Tofu", "Thai"),
    "R006": ("Shakshuka", "Middle Eastern"),
}

# (chunk_id, recipe_id, section, base_score, contains_key_answer)
CHUNK_POOL = [
    # R001 chunks
    ("R001-B00", "R001", "Overview",     0.72, False),
    ("R001-B01", "R001", "Ingredients",  0.91, True),   # heavy cream row
    ("R001-B02", "R001", "Ingredients",  0.83, True),   # paneer / cashews rows
    ("R001-B03", "R001", "Method",       0.79, True),   # sear / cashew step
    ("R001-B04", "R001", "Method",       0.74, True),   # simmer step
    ("R001-B05", "R001", "Notes",        0.67, True),   # vegan sub
    ("R001-B06", "R001", "Nutrition",    0.58, True),   # 512 kcal
    # R002 chunks
    ("R002-B00", "R002", "Overview",     0.65, False),
    ("R002-B01", "R002", "Ingredients",  0.84, True),   # 200g dried chickpeas
    ("R002-B02", "R002", "Method",       0.78, True),   # boil 45-55 min
    ("R002-B03", "R002", "Notes",        0.61, True),   # tinned substitute
    ("R002-B04", "R002", "Nutrition",    0.52, False),
    # R003 chunks
    ("R003-B00", "R003", "Overview",     0.61, False),
    ("R003-B01", "R003", "Ingredients",  0.88, True),   # mozzarella / flour
    ("R003-B02", "R003", "Method",       0.82, True),   # 250C preheat
    ("R003-B03", "R003", "Method",       0.77, True),   # bake 6-8 min
    ("R003-B04", "R003", "Notes",        0.63, True),   # domestic oven note
    ("R003-B05", "R003", "Nutrition",    0.71, True),   # 892 kcal
    # R004 chunks
    ("R004-B00", "R004", "Overview",     0.68, False),
    ("R004-B01", "R004", "Ingredients",  0.87, True),   # 45g curry paste + fish sauce
    ("R004-B02", "R004", "Method",       0.81, True),   # simmer 12 min
    ("R004-B03", "R004", "Notes",        0.64, True),   # breast 7 min sub
    ("R004-B04", "R004", "Nutrition",    0.55, False),
    # R005 chunks  (near-duplicate of R004 — this is the main confusion source)
    ("R005-B00", "R005", "Overview",     0.69, False),
    ("R005-B01", "R005", "Ingredients",  0.88, True),   # 50g curry paste + soy
    ("R005-B02", "R005", "Method",       0.80, True),   # simmer 10+5 min
    ("R005-B03", "R005", "Notes",        0.62, True),   # vegan paste note
    ("R005-B04", "R005", "Nutrition",    0.54, False),
    # R006 chunks
    ("R006-B00", "R006", "Overview",     0.66, False),
    ("R006-B01", "R006", "Ingredients",  0.85, True),   # 6 eggs / feta
    ("R006-B02", "R006", "Method",       0.79, True),   # simmer sauce 15 min
    ("R006-B03", "R006", "Method",       0.76, True),   # cover + cook 6-8 min
    ("R006-B04", "R006", "Notes",        0.60, True),   # vegan version
    ("R006-B05", "R006", "Nutrition",    0.51, False),
]

def _jitter(score: float) -> float:
    return round(min(1.0, max(0.01, score + rng.gauss(0.0, 0.04))), 4)

def _pick_chunks(target_chunk_ids: list[str], k: int = 5) -> list[dict]:
    """Build a realistic top-k result, making the target(s) sometimes absent."""
    pool_by_id = {c[0]: c for c in CHUNK_POOL}
    selected = []
    remaining = [c for c in CHUNK_POOL if c[0] not in target_chunk_ids]
    rng.shuffle(remaining)
    target_chunks = [pool_by_id[cid] for cid in target_chunk_ids if cid in pool_by_id]

    all_candidates = target_chunks + remaining[:max(k * 2, 10)]
    # Sort by jittered score descending
    scored = [(c, _jitter(c[3])) for c in all_candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_k = scored[:k]

    for rank, (c, score) in enumerate(top_k, start=1):
        selected.append({
            "rank": rank,
            "chunk_id": c[0],
            "recipe_id": c[1],
            "section": c[2],
            "score": score,
        })
    return selected


# ── question templates for the 23 known-answer questions ─────────────────────
KNOWN_QUESTIONS = [
    # (qid, question_text, correct_chunk_ids, gold_answer, gold_recipe)
    ("Q1",  "How much heavy cream does the paneer butter masala need?",
     ["R001-B01"], "60 ml", "R001"),
    ("Q2",  "How many grams of green curry paste are in the vegan green curry?",
     ["R005-B01"], "50 g", "R005"),
    ("Q3",  "How many grams of dried chickpeas does chana masala use?",
     ["R002-B01"], "200 g", "R002"),
    ("Q4",  "How many calories per serving does the margherita pizza have?",
     ["R003-B05"], "892 kcal", "R003"),
    ("Q5",  "What temperature should the oven and stone be preheated to for the pizza?",
     ["R003-B02"], "250 C", "R003"),
    ("Q6",  "What can I use instead of paneer to make the butter masala vegan?",
     ["R001-B05"], "extra-firm tofu", "R001"),
    ("Q7",  "How long does the shakshuka sauce simmer before the eggs go in?",
     ["R006-B02"], "15 minutes", "R006"),
    ("Q8",  "How much curry paste do I need?",
     ["R004-B01", "R005-B01"], "ambiguous: 45 g or 50 g", "R004"),
    ("Q9",  "How much paneer is used in paneer butter masala?",
     ["R001-B01", "R001-B02"], "400 g", "R001"),
    ("Q10", "How long should the cashews soak for paneer butter masala?",
     ["R001-B03"], "15 minutes in hot water", "R001"),
    ("Q11", "How long do the paneer cubes sear on each side?",
     ["R001-B03"], "2 minutes per side", "R001"),
    ("Q12", "How long should dried chickpeas boil for chana masala?",
     ["R002-B02"], "45 to 55 minutes", "R002"),
    ("Q13", "What is the quick substitute for dried chickpeas in chana masala?",
     ["R002-B03"], "two 400 g tins drained", "R002"),
    ("Q14", "How long is the pizza dough refrigerated for?",
     ["R003-B02"], "24 hours", "R003"),
    ("Q15", "How much fresh mozzarella is needed for the margherita pizza?",
     ["R003-B01"], "250 g", "R003"),
    ("Q16", "When are basil leaves added to the margherita pizza?",
     ["R003-B03"], "After baking", "R003"),
    ("Q17", "How much fish sauce is used in Thai green curry with chicken?",
     ["R004-B01"], "2 tbsp", "R004"),
    ("Q18", "How long does the chicken curry simmer after the vegetables are added?",
     ["R004-B02"], "12 minutes", "R004"),
    ("Q19", "What is the chicken breast simmer time substitute in the chicken curry?",
     ["R004-B03"], "7 minutes", "R004"),
    ("Q20", "How long is tofu pressed for the vegan green curry?",
     ["R005-B02"], "30 minutes", "R005"),
    ("Q21", "What replaces fish sauce in the vegan green curry?",
     ["R005-B01"], "2 tbsp light soy sauce", "R005"),
    ("Q22", "How many eggs are used in shakshuka?",
     ["R006-B01"], "6 eggs", "R006"),
    ("Q23", "How long are shakshuka eggs cooked after covering the pan?",
     ["R006-B03"], "6 to 8 minutes", "R006"),
]

# Unanswerable questions that sometimes slip past the refusal gate
UNANSWERABLE = [
    ("U1", "What wine should I serve with the shakshuka?"),
    ("U2", "Can I freeze the paneer butter masala?"),
    ("U3", "What is the history of chana masala?"),
    ("U4", "How do I make the pizza dough without yeast?"),
    ("U5", "What pan works best for Thai green curry?"),
    ("U6", "Is there a nut-free version of the butter masala?"),
    ("U7", "How many people does the shakshuka serve?"),   # borderline
]

# Off-topic questions
OFF_TOPIC = [
    ("OT1", "What is the best chef's knife brand?"),
    ("OT2", "How do I season a cast iron pan?"),
    ("OT3", "Tell me about Italian cuisine history"),
    ("OT4", "What kitchen scale should I buy?"),
]


# ── failure modes + realistic raw outputs ─────────────────────────────────────

def _make_success(q, chunks, gold_answer: str) -> tuple[str, bool, str | None, list]:
    """Correct answer with valid citations."""
    cid = chunks[0]["chunk_id"]
    rid = chunks[0]["recipe_id"]
    ans = (
        f"According to the recipe card, {gold_answer}. "
        f"[{cid} | {rid}]"
    )
    return ans, False, None, [(cid, rid)]


def _make_wrong_quantity(q, chunks, gold_answer: str, wrong_val: str) -> tuple[str, bool, str | None, list]:
    """Model reads wrong quantity from a near-duplicate recipe."""
    cid = chunks[0]["chunk_id"]
    rid = chunks[0]["recipe_id"]
    # Swap R004/R005 IDs to simulate cross-recipe confusion
    wrong_rid = "R005" if rid == "R004" else ("R004" if rid == "R005" else rid)
    ans = (
        f"The recipe calls for {wrong_val}. "
        f"[{cid} | {wrong_rid}]"
    )
    return ans, False, None, [(cid, wrong_rid)]


def _make_hallucinated_quantity(q, chunks, gold_answer: str) -> tuple[str, bool, str | None, list]:
    """Model invents a plausible but wrong quantity not in any chunk."""
    cid = chunks[0]["chunk_id"]
    rid = chunks[0]["recipe_id"]
    # Generate hallucinated values
    hallucinations = {
        "60 ml": "75 ml", "400 g": "450 g", "200 g": "250 g",
        "892 kcal": "780 kcal", "50 g": "60 g", "45 g": "40 g",
        "15 minutes": "20 minutes", "12 minutes": "15 minutes",
        "6 to 8 minutes": "8 to 10 minutes", "30 minutes": "25 minutes",
    }
    wrong = hallucinations.get(gold_answer, gold_answer + " (approx)")
    ans = (
        f"Based on the context, you'll need {wrong}. "
        f"[{cid} | {rid}]"
    )
    return ans, False, None, [(cid, rid)]


def _make_partial_answer(q, chunks, gold_answer: str) -> tuple[str, bool, str | None, list]:
    """Model returns a correct but incomplete answer (drops the unit or qualifier)."""
    cid = chunks[0]["chunk_id"]
    rid = chunks[0]["recipe_id"]
    # Strip the unit from the answer
    parts = gold_answer.split()
    truncated = parts[0] if parts else gold_answer
    ans = (
        f"The recipe specifies {truncated}. "
        f"[{cid} | {rid}]"
    )
    return ans, False, None, [(cid, rid)]


def _make_wrong_recipe_answer(q, chunks, gold_answer: str, wrong_recipe: str) -> tuple[str, bool, str | None, list]:
    """Model cites the wrong recipe because a near-duplicate was ranked first."""
    wrong_title = RECIPES.get(wrong_recipe, ("Unknown Recipe",))[0]
    # Use a chunk from the wrong recipe
    wrong_chunks = [c for c in CHUNK_POOL if c[1] == wrong_recipe]
    if wrong_chunks:
        wc = rng.choice(wrong_chunks)
        ans = (
            f"For {wrong_title}, {gold_answer}. "
            f"[{wc[0]} | {wrong_recipe}]"
        )
        return ans, False, None, [(wc[0], wrong_recipe)]
    return _make_success(q, chunks, gold_answer)


def _make_refusal_on_answerable(q) -> tuple[str, bool, str, list]:
    """Refusal gate fires on a question that actually is answerable."""
    return (
        "I cannot answer that from the provided recipe cards.",
        True,
        "score_threshold",
        [],
    )


def _make_false_positive_answer(q, chunks) -> tuple[str, bool, str | None, list]:
    """Model answers an unanswerable question instead of refusing."""
    cid = chunks[0]["chunk_id"]
    rid = chunks[0]["recipe_id"]
    fabricated_answers = [
        "A light Pinot Grigio would complement this dish nicely.",
        "Yes, you can freeze it for up to 3 months in an airtight container.",
        "A heavy-bottomed non-stick pan works best for even heat distribution.",
        "Omit the cashews and use sunflower seeds instead for a nut-free version.",
    ]
    ans = rng.choice(fabricated_answers) + f" [{cid} | {rid}]"
    return ans, False, None, [(cid, rid)]


def _make_citation_mismatch(q, chunks, gold_answer: str) -> tuple[str, bool, str | None, list]:
    """Correct answer but citation chunk_id doesn't match the chunk that was served."""
    cid = chunks[0]["chunk_id"]
    rid = chunks[0]["recipe_id"]
    # Invent a chunk_id that was not actually in the retrieved set
    fake_cid = cid.replace("B0", "B9")
    ans = (
        f"The answer is {gold_answer}. "
        f"[{fake_cid} | {rid}]"
    )
    return ans, False, None, [(fake_cid, rid)]


def _make_no_citation(q, chunks, gold_answer: str) -> tuple[str, bool, str | None, list]:
    """Correct answer with no citation at all."""
    ans = f"The recipe requires {gold_answer}."
    return ans, False, None, []


def _make_off_topic_refusal(q) -> tuple[str, bool, str, list]:
    return (
        "I cannot answer that from the provided recipe cards.",
        True,
        "score_threshold",
        [],
    )


# ── trace factory ─────────────────────────────────────────────────────────────

def _make_trace(
    question: str,
    qid: str,
    chunks: list[dict],
    raw_output: str,
    refused: bool,
    refusal_reason: str | None,
    citations: list,
    ts: datetime,
    strategy: str = "structured",
    mode: str = "hybrid",
    k: int = 5,
    rerank: bool = True,
) -> dict:
    return {
        "trace_id": str(uuid.UUID(int=rng.getrandbits(128))),
        "timestamp": ts.isoformat(),
        "question": question,
        "qid_template": qid,
        "prompt_version": PROMPT_VERSION,
        "model": MODEL,
        "model_params": MODEL_PARAMS,
        "strategy": strategy,
        "mode": mode,
        "k": k,
        "rerank": rerank,
        "retrieved_chunks": chunks,
        "raw_output": raw_output,
        "answer": raw_output,
        "refused": refused,
        "refusal_reason": refusal_reason,
        "citations": [{"chunk_id": c[0], "recipe_id": c[1]} for c in citations],
        "latency_ms": int(rng.gauss(420, 80)),
    }


def generate_traces(n_target: int = 1200) -> list[dict]:
    traces = []
    base_ts = datetime(2026, 9, 8, 9, 0, 0)
    ts = base_ts

    # Weights control how often each failure mode appears across the run
    # These are calibrated to produce realistic frequencies
    QUESTION_WEIGHTS = [1.5] * 8 + [1.0] * 15  # Q1-Q8 asked more often
    UNANSWERABLE_PROB = 0.12
    OFF_TOPIC_PROB = 0.06

    while len(traces) < n_target:
        ts += timedelta(seconds=rng.randint(15, 180))

        # Decide query type
        roll = rng.random()
        if roll < OFF_TOPIC_PROB:
            uid, question = rng.choice(OFF_TOPIC)
            chunks = _pick_chunks([], k=5)
            ans, refused, reason, cites = _make_off_topic_refusal(question)
            trace = _make_trace(question, uid, chunks, ans, refused, reason, cites, ts)
        elif roll < OFF_TOPIC_PROB + UNANSWERABLE_PROB:
            uid, question = rng.choice(UNANSWERABLE)
            chunks = _pick_chunks([], k=5)
            # 60% properly refused, 40% false positive
            if rng.random() < 0.60:
                ans, refused, reason, cites = _make_refusal_on_answerable(question)
            else:
                ans, refused, reason, cites = _make_false_positive_answer(question, chunks)
            trace = _make_trace(question, uid, chunks, ans, refused, reason, cites, ts)
        else:
            q = rng.choices(KNOWN_QUESTIONS, weights=QUESTION_WEIGHTS, k=1)[0]
            qid, question, correct_chunk_ids, gold_answer, gold_recipe = q

            # Randomise retrieval quality
            retrieval_quality = rng.random()

            if retrieval_quality < 0.08:
                # Correct chunk not in top-k at all → refusal gate fires
                chunks = _pick_chunks([], k=5)
                ans, refused, reason, cites = _make_refusal_on_answerable(question)
            else:
                chunks = _pick_chunks(correct_chunk_ids, k=5)
                failure_roll = rng.random()

                if failure_roll < 0.42:
                    # Success
                    ans, refused, reason, cites = _make_success(q, chunks, gold_answer)
                elif failure_roll < 0.60:
                    # Wrong quantity from near-duplicate (Q8, Q2/Q17 most susceptible)
                    wrong_map = {
                        "R004": ("R005", "50 g"), "R005": ("R004", "45 g"),
                        "R001": ("R001", "75 ml"),  # hallucinated for cream
                    }
                    if gold_recipe in wrong_map and rng.random() < 0.55:
                        wrong_rid, wrong_val = wrong_map[gold_recipe]
                        ans, refused, reason, cites = _make_wrong_quantity(q, chunks, gold_answer, wrong_val)
                    else:
                        ans, refused, reason, cites = _make_hallucinated_quantity(q, chunks, gold_answer)
                elif failure_roll < 0.70:
                    # Cross-recipe citation (cites R004 for R005 answer etc.)
                    near_dupe = {"R004": "R005", "R005": "R004"}.get(gold_recipe)
                    if near_dupe:
                        ans, refused, reason, cites = _make_wrong_recipe_answer(q, chunks, gold_answer, near_dupe)
                    else:
                        ans, refused, reason, cites = _make_partial_answer(q, chunks, gold_answer)
                elif failure_roll < 0.78:
                    # Partial / incomplete answer
                    ans, refused, reason, cites = _make_partial_answer(q, chunks, gold_answer)
                elif failure_roll < 0.85:
                    # Citation mismatch
                    ans, refused, reason, cites = _make_citation_mismatch(q, chunks, gold_answer)
                elif failure_roll < 0.91:
                    # No citation at all
                    ans, refused, reason, cites = _make_no_citation(q, chunks, gold_answer)
                else:
                    # Refusal on answerable question (retrieval OK, gate too aggressive)
                    ans, refused, reason, cites = _make_refusal_on_answerable(question)

            # Vary strategy/mode occasionally
            strategy = rng.choices(["structured", "basic"], weights=[0.85, 0.15])[0]
            mode = rng.choices(["hybrid", "semantic", "bm25"], weights=[0.70, 0.20, 0.10])[0]
            trace = _make_trace(question, qid, chunks, ans, refused, reason, cites, ts,
                                strategy=strategy, mode=mode)

        traces.append(trace)

    return traces


def main():
    print(f"Generating traces (seed={GENERATION_SEED})…")
    traces = generate_traces(1200)
    with OUT.open("w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t) + "\n")
    print(f"Wrote {len(traces)} traces -> {OUT}")
    return traces


if __name__ == "__main__":
    main()
