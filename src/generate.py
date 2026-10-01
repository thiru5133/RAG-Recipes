"""Grounded answer generation via Groq, with citations tied to chunk ids."""
import hashlib
import os
import re
import time
from typing import Dict, List, Optional

from dotenv import load_dotenv

from config import GROQ_MODEL

load_dotenv()

REFUSAL = "I cannot answer that from the provided recipe cards."

SYSTEM_PROMPT = f"""You answer questions about a small set of recipe cards.

Rules, without exception:
1. Use ONLY the numbered context chunks provided. You have no other knowledge of
   these recipes.
2. Every factual claim must carry a citation in the form [chunk_id | recipe_id]
   copied exactly from the chunk header it came from.
3. If the context does not contain the answer, reply with exactly this sentence
   and nothing else: "{REFUSAL}"
4. Never guess a quantity, temperature or time that is not written in the
   context. Do not fill gaps from general cooking knowledge.
5. Be brief: two or three sentences at most.
"""

PROMPT_VERSION = "v1.2.0"

# v1.3.0 (week 6): the "two or three sentences at most" cap made substitution
# answers stop after the first swap (e.g. tofu but not the coconut cream and oil
# the card also requires). Substitution questions now get every swap the context
# lists for the question; everything else keeps the brief limit.
SYSTEM_PROMPT_V13 = SYSTEM_PROMPT.replace(
    "5. Be brief: two or three sentences at most.\n",
    "5. Be brief: two or three sentences at most. Exception: when asked for a\n"
    "   substitution or how to adapt a recipe, state EVERY swap, quantity and\n"
    "   condition the context gives for that question (for example each\n"
    "   ingredient that must change, not only the first), up to six sentences,\n"
    "   and never add a swap the context does not list.\n",
)

PROMPT_REGISTRY = {PROMPT_VERSION: SYSTEM_PROMPT, "v1.3.0": SYSTEM_PROMPT_V13}

TEMPERATURE = 0
MAX_TOKENS = 400


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def system_prompt_for(version: str) -> str:
    if version not in PROMPT_REGISTRY:
        raise KeyError(
            f"prompt version {version!r} is not in the registry; "
            f"known versions: {sorted(PROMPT_REGISTRY)}"
        )
    return PROMPT_REGISTRY[version]


def format_context(hits: List[Dict]) -> str:
    blocks = []
    for h in hits:
        meta = h.get("metadata") or {}
        blocks.append(
            f"[chunk_id: {h['chunk_id']} | recipe_id: {meta.get('recipe_id', '?')} "
            f"| recipe: {meta.get('recipe_title', '?')} | section: {meta.get('section', '?')}]\n"
            f"{h['text']}"
        )
    return "\n\n---\n\n".join(blocks)


def build_user_prompt(question: str, hits: List[Dict]) -> str:
    """The exact user message sent to the model. Replay rebuilds it from a trace
    by calling this with hits reconstructed from the trace's chunk records."""
    return (
        f"Context chunks:\n\n{format_context(hits)}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above, with a [chunk_id | recipe_id] "
        "citation on every claim."
    )


def _client():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    from groq import Groq

    return Groq(api_key=key)


def complete(
    system_prompt: str,
    user_prompt: str,
    model: str = GROQ_MODEL,
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
) -> Dict:
    """One raw model call. Replay uses this directly with a rebuilt prompt."""
    client = _client()
    if client is None:
        return {
            "answer": None,
            "finish_reason": None,
            "usage": None,
            "latency_ms": None,
            "error": "GROQ_API_KEY is not set; no answer generated.",
        }
    started = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        usage = getattr(resp, "usage", None)
        return {
            "answer": resp.choices[0].message.content.strip(),
            "finish_reason": resp.choices[0].finish_reason,
            "usage": None
            if usage is None
            else {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
            },
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "error": None,
        }
    except Exception as exc:  # network, rate limit, bad key
        return {
            "answer": None,
            "finish_reason": None,
            "usage": None,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
        }


def generate(
    question: str,
    hits: List[Dict],
    model: str = GROQ_MODEL,
    prompt_version: str = PROMPT_VERSION,
) -> Dict:
    """Return the answer plus everything a replay needs to reproduce the call."""
    system_prompt = system_prompt_for(prompt_version)
    context_ids = [h["chunk_id"] for h in hits]
    user_prompt = build_user_prompt(question, hits)
    result = complete(system_prompt, user_prompt, model=model)
    return {
        "answer": result["answer"],
        "model": model,
        "context_ids": context_ids,
        "error": result["error"],
        "prompt_version": prompt_version,
        "system_prompt_sha256": sha256(system_prompt),
        "user_prompt": user_prompt,
        "user_prompt_sha256": sha256(user_prompt),
        "model_params": {"temperature": TEMPERATURE, "max_tokens": MAX_TOKENS},
        "finish_reason": result["finish_reason"],
        "usage": result["usage"],
        "latency_ms": result["latency_ms"],
    }


# Models drift from the prompted `[chunk_id | recipe_id]` shape. Normalise the
# known variants (full-width brackets, non-ASCII hyphens, padded spaces, the
# context-header form `chunk_id: X | recipe_id: Y`) before matching.
_BRACKETS = str.maketrans({"\u3010": "[", "\u3011": "]", "\uff3b": "[", "\uff3d": "]"})
_HYPHENS = re.compile("[\u2010\u2011\u2012\u2013\u2014\u2212]")
CITATION_RE = re.compile(
    r"\[\s*(?:chunk_id\s*:\s*)?([A-Za-z0-9_\-]+)\s*\|\s*(?:recipe_id\s*:\s*)?([A-Za-z0-9_\-]+)\s*\]"
)


def extract_citations(answer: Optional[str]):
    if not answer:
        return []
    text = _HYPHENS.sub("-", answer.translate(_BRACKETS))
    return [(m.group(1), m.group(2)) for m in CITATION_RE.finditer(text)]
