"""Grounded answer generation via Groq, with citations tied to chunk ids."""
import os
import re
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


def _client():
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    from groq import Groq

    return Groq(api_key=key)


def generate(question: str, hits: List[Dict], model: str = GROQ_MODEL) -> Dict:
    """Return {'answer', 'model', 'context_ids', 'error'}."""
    context_ids = [h["chunk_id"] for h in hits]
    client = _client()
    if client is None:
        return {
            "answer": None,
            "model": model,
            "context_ids": context_ids,
            "error": "GROQ_API_KEY is not set; no answer generated.",
        }

    prompt = (
        f"Context chunks:\n\n{format_context(hits)}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above, with a [chunk_id | recipe_id] "
        "citation on every claim."
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=400,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return {
            "answer": resp.choices[0].message.content.strip(),
            "model": model,
            "context_ids": context_ids,
            "error": None,
        }
    except Exception as exc:  # network, rate limit, bad key
        return {
            "answer": None,
            "model": model,
            "context_ids": context_ids,
            "error": f"{type(exc).__name__}: {exc}",
        }


CITATION_RE = re.compile(r"\[([A-Za-z0-9_\-]+)\s*\|\s*([A-Za-z0-9_\-]+)\]")


def extract_citations(answer: Optional[str]):
    if not answer:
        return []
    return [(m.group(1), m.group(2)) for m in CITATION_RE.finditer(answer)]
