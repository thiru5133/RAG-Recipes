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

PROMPT_REGISTRY = {PROMPT_VERSION: SYSTEM_PROMPT}

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

    # 90s cap: an unenforced HTTP timeout is how W05 sat for eight hours.
    return Groq(api_key=key, timeout=90.0)


def complete_messages(
    messages: List[Dict],
    model: str = GROQ_MODEL,
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
    tools: Optional[List[Dict]] = None,
) -> Dict:
    """One chat-completions call. The agent loop uses this so every lap's
    tokens can be summed; `complete()` stays the two-string helper replay needs.
    """
    client = _client()
    if client is None:
        return {
            "content": None,
            "tool_calls": [],
            "finish_reason": None,
            "usage": None,
            "latency_ms": None,
            "error": "GROQ_API_KEY is not set; no answer generated.",
        }
    started = time.perf_counter()
    kwargs = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    last_err = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(**kwargs)
            usage = getattr(resp, "usage", None)
            msg = resp.choices[0].message
            content = (msg.content or "").strip()
            if not content:
                content = (getattr(msg, "reasoning", None) or "").strip()
            tool_calls = []
            for tc in getattr(msg, "tool_calls", None) or []:
                fn = tc.function
                tool_calls.append(
                    {
                        "id": getattr(tc, "id", "") or "",
                        "name": fn.name,
                        "arguments": fn.arguments or "{}",
                    }
                )
            return {
                "content": content,
                "tool_calls": tool_calls,
                "finish_reason": resp.choices[0].finish_reason,
                "usage": None
                if usage is None
                else {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                },
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error": None,
                "raw_message": msg,
            }
        except Exception as exc:
            last_err = exc
            msg = f"{type(exc).__name__}: {exc}"
            low = msg.lower()
            retryable = (
                "429" in msg
                or "rate" in low
                or "connect" in low
                or "timeout" in low
                or "timed out" in low
                or "temporarily" in low
            )
            if retryable and attempt < 2:
                wait = 25 if "429" in msg or "rate" in low else 5 * (attempt + 1)
                time.sleep(wait)
                continue
            break
    return {
        "content": None,
        "tool_calls": [],
        "finish_reason": None,
        "usage": None,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "error": f"{type(last_err).__name__}: {last_err}" if last_err else "unknown error",
        "raw_message": None,
    }


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
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        if not content:
            # gpt-oss on Groq often spends the token budget on `reasoning`
            # and leaves `content` empty. Fall back so a verdict still lands.
            content = (getattr(msg, "reasoning", None) or "").strip()
        return {
            "answer": content,
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


def generate(question: str, hits: List[Dict], model: str = GROQ_MODEL) -> Dict:
    """Return the answer plus everything a replay needs to reproduce the call."""
    context_ids = [h["chunk_id"] for h in hits]
    user_prompt = build_user_prompt(question, hits)
    result = complete(SYSTEM_PROMPT, user_prompt, model=model)
    return {
        "answer": result["answer"],
        "model": model,
        "context_ids": context_ids,
        "error": result["error"],
        "prompt_version": PROMPT_VERSION,
        "system_prompt_sha256": sha256(SYSTEM_PROMPT),
        "user_prompt": user_prompt,
        "user_prompt_sha256": sha256(user_prompt),
        "model_params": {"temperature": TEMPERATURE, "max_tokens": MAX_TOKENS},
        "finish_reason": result["finish_reason"],
        "usage": result["usage"],
        "latency_ms": result["latency_ms"],
    }


CITATION_RE = re.compile(r"\[([A-Za-z0-9_\-]+)\s*\|\s*([A-Za-z0-9_\-]+)\]")


def extract_citations(answer: Optional[str]):
    if not answer:
        return []
    return [(m.group(1), m.group(2)) for m in CITATION_RE.finditer(answer)]
