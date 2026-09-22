"""Hand-built agent loop: model chooses tools until it emits the output contract.

Four budgets are checked at the top of every lap — an unenforced budget is a
comment. Tokens are summed across laps; the loop re-sends the whole message
list each time, so counting only the last call would understate cost.
"""
from __future__ import annotations

import json
import re
import time
from typing import Dict, List, Optional

from config import (
    AGENT_MAX_COST_USD,
    AGENT_MAX_ITERS,
    AGENT_MAX_TOKENS,
    AGENT_MAX_WALL_MS,
    GROQ_PRICES,
    WEEK7_MODEL,
)
from generate import complete_messages

from agent.contract import cost_usd, empty_result, extract_json
from agent.tools import THREE_TOOL_SCHEMAS, run_tool

SYSTEM = """You adapt one recipe from a six-card corpus.

You have three tools. Each does one job. Do not ask a tool to do another's job.
- search_recipes: find the recipe_id. Call this first.
- scale_recipe: change serving count. Call this second.
- get_allergen_profile: ONE allergen enum per call (nuts, dairy, gluten, fish, shellfish, egg, meat).

If the user is vegan, you must clear dairy, egg, fish, shellfish and meat — that is several profile calls, not one.
If a profile result has "introduces" or "leaves" and the user also needs those classes gone, call get_allergen_profile again with that enum. Do not stop after the first allergen.

When you are done, output ONLY this JSON (no markdown):
{
  "recipe_id": "R00X",
  "title": "...",
  "servings": <int>,
  "ingredients": [{"name": "...", "quantity": <number>, "unit": "..."}],
  "method": ["step", "..."],
  "swaps_applied": ["..."],
  "warnings": ["..."]
}
Apply every card_swap you received to the scaled ingredient list before you emit.
If cannot_adapt is true, keep the original ingredients and put the reason in warnings.

If the API has no native tools, emit a tool call as a single JSON object:
{"tool": "search_recipes", "args": {"query": "..."}}
{"tool": "scale_recipe", "args": {"recipe_id": "R001", "servings": 8}}
{"tool": "get_allergen_profile", "args": {"recipe_id": "R001", "allergen": "dairy"}}
"""

JSON_TOOL_RE = re.compile(
    r"\{[^{}]*\"(?:tool|name)\"\s*:\s*\"(search_recipes|scale_recipe|get_allergen_profile)\"[^{}]*\}",
    re.S,
)


def _parse_args(raw) -> Dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def _json_tool_call(text: str) -> Optional[Dict]:
    if not text:
        return None
    try:
        obj = json.loads(text.strip())
        if isinstance(obj, dict) and obj.get("tool") in {
            "search_recipes", "scale_recipe", "get_allergen_profile",
        }:
            return {"name": obj["tool"], "arguments": obj.get("args") or obj.get("arguments") or {}}
    except json.JSONDecodeError:
        pass
    m = JSON_TOOL_RE.search(text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    name = obj.get("tool") or obj.get("name")
    args = obj.get("args") or obj.get("arguments") or {}
    if name in {"search_recipes", "scale_recipe", "get_allergen_profile"}:
        return {"name": name, "arguments": args}
    return None


def _looks_done(obj: Optional[Dict]) -> bool:
    if not obj:
        return False
    if obj.get("done") or obj.get("recipe_id"):
        return "ingredients" in obj or "method" in obj or obj.get("done") is True
    return False


def run_agent(
    request_text: str,
    *,
    max_iters: int = AGENT_MAX_ITERS,
    max_tokens: int = AGENT_MAX_TOKENS,
    max_cost_usd: float = AGENT_MAX_COST_USD,
    max_wall_ms: int = AGENT_MAX_WALL_MS,
    model: str = WEEK7_MODEL,
) -> Dict:
    messages: List[Dict] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": request_text},
    ]
    log: List[str] = []
    prompt_tokens = completion_tokens = 0
    started = time.perf_counter()
    result = empty_result()
    stopped_by = None
    laps = 0
    tools_ok = True

    for lap in range(1, max_iters + 1):
        laps = lap
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        inp, outp = GROQ_PRICES.get(model, (0.15, 0.60))
        spent = cost_usd(prompt_tokens, completion_tokens, inp, outp)
        used = prompt_tokens + completion_tokens

        if used >= max_tokens:
            stopped_by = "max_tokens"
            log.append(f"LAP {lap} BUDGET max_tokens used={used} cap={max_tokens}")
            break
        if spent >= max_cost_usd:
            stopped_by = "max_cost"
            log.append(f"LAP {lap} BUDGET max_cost usd={spent} cap={max_cost_usd}")
            break
        if elapsed_ms >= max_wall_ms:
            stopped_by = "wall_clock"
            log.append(f"LAP {lap} BUDGET wall_clock ms={elapsed_ms} cap={max_wall_ms}")
            break

        resp = complete_messages(
            messages,
            model=model,
            max_tokens=1200,
            tools=THREE_TOOL_SCHEMAS if tools_ok else None,
        )
        err = resp.get("error") or ""
        if "429" in err or "rate" in err.lower():
            log.append(f"LAP {lap} rate-limit, sleeping 25s")
            time.sleep(25)
            resp = complete_messages(
                messages,
                model=model,
                max_tokens=1200,
                tools=THREE_TOOL_SCHEMAS if tools_ok else None,
            )
            err = resp.get("error") or ""
        if err and tools_ok and "tool" in err.lower():
            tools_ok = False
            log.append(f"LAP {lap} tools rejected by API, falling back to JSON protocol")
            resp = complete_messages(messages, model=model, max_tokens=1200, tools=None)
        if resp.get("error"):
            log.append(f"LAP {lap} ERROR {resp['error']}")
            stopped_by = "error"
            break

        usage = resp.get("usage") or {}
        prompt_tokens += int(usage.get("prompt_tokens") or 0)
        completion_tokens += int(usage.get("completion_tokens") or 0)
        log.append(
            f"LAP {lap} tokens_in={usage.get('prompt_tokens')} "
            f"tokens_out={usage.get('completion_tokens')} "
            f"cumulative={prompt_tokens + completion_tokens}"
        )

        tool_calls = list(resp.get("tool_calls") or [])
        content = resp.get("content") or ""

        if not tool_calls:
            parsed = _json_tool_call(content)
            if parsed:
                tool_calls = [{"id": f"json-{lap}", **parsed, "arguments": json.dumps(parsed["arguments"])
                               if isinstance(parsed["arguments"], dict) else parsed["arguments"]}]

        if tool_calls:
            raw_msg = resp.get("raw_message")
            if raw_msg is not None and getattr(raw_msg, "tool_calls", None):
                messages.append(
                    {
                        "role": "assistant",
                        "content": content or None,
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {"name": tc["name"], "arguments": tc["arguments"]},
                            }
                            for tc in tool_calls
                        ],
                    }
                )
                native = True
            else:
                messages.append({"role": "assistant", "content": content or json.dumps(tool_calls)})
                native = False

            for tc in tool_calls:
                args = _parse_args(tc.get("arguments"))
                payload = run_tool(tc["name"], args)
                log.append(f"LAP {lap} TOOL {tc['name']} {json.dumps(args, ensure_ascii=False)[:120]}")
                if native:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(payload, ensure_ascii=False),
                        }
                    )
                else:
                    messages.append(
                        {
                            "role": "user",
                            "content": f"TOOL_RESULT {tc['name']}: {json.dumps(payload, ensure_ascii=False)}",
                        }
                    )
            continue

        done = extract_json(content)
        if _looks_done(done):
            result = {**empty_result(), **{k: done[k] for k in done if k in empty_result() or k in done}}
            for k, v in done.items():
                result[k] = v
            stopped_by = "completed"
            log.append(f"LAP {lap} DONE recipe_id={result.get('recipe_id')}")
            break

        messages.append({"role": "assistant", "content": content})
        messages.append({
            "role": "user",
            "content": "Output the final JSON contract now, or call a tool.",
        })
    else:
        stopped_by = "max_iters"
        log.append(f"BUDGET max_iters cap={max_iters}")

    if stopped_by is None:
        stopped_by = "max_iters"
        log.append(f"BUDGET max_iters cap={max_iters}")

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    inp, outp = GROQ_PRICES.get(model, (0.15, 0.60))
    spent = cost_usd(prompt_tokens, completion_tokens, inp, outp)
    return {
        "system": "agent",
        "result": result,
        "stopped_by": stopped_by,
        "laps": laps,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tokens": prompt_tokens + completion_tokens,
        "cost_usd": spent,
        "latency_ms": elapsed_ms,
        "log": log,
    }
