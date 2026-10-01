"""Shared plumbing for the Week 10 squad: one metered model call, one restricted tool loop.

Every model call is appended to a `Meter` under a named hand-off, so the token
bill can be attributed to a specific edge of the graph afterwards.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from config import GROQ_PRICES, WEEK7_MODEL
from generate import complete_messages
from agent.mcp_agent import MAX_OUT_TOKENS as MAX_OUT, McpHost



@dataclass
class Meter:
    rows: List[Dict] = field(default_factory=list)

    def add(self, handoff: str, usage: Optional[Dict], ms: int) -> None:
        u = usage or {}
        self.rows.append({"handoff": handoff, "prompt_tokens": int(u.get("prompt_tokens") or 0),
                          "completion_tokens": int(u.get("completion_tokens") or 0), "ms": ms})

    @property
    def tokens(self) -> int:
        return sum(r["prompt_tokens"] + r["completion_tokens"] for r in self.rows)

    def by_handoff(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for r in self.rows:
            out[r["handoff"]] = out.get(r["handoff"], 0) + r["prompt_tokens"] + r["completion_tokens"]
        return out

    def cost(self, model: str = WEEK7_MODEL) -> float:
        inp, outp = GROQ_PRICES.get(model, (0.15, 0.60))
        return sum(r["prompt_tokens"] * inp + r["completion_tokens"] * outp for r in self.rows) / 1e6


def llm(messages: List[Dict], meter: Meter, handoff: str, tools: Optional[List[Dict]] = None,
        model: str = WEEK7_MODEL) -> Dict:
    t0 = time.perf_counter()
    resp = complete_messages(messages, model=model, max_tokens=MAX_OUT, tools=tools or None)
    meter.add(handoff, resp.get("usage"), int((time.perf_counter() - t0) * 1000))
    return resp


def tool_loop(system: str, user: str, host: McpHost, allowed: Sequence[str], meter: Meter, handoff: str,
              max_laps: int = 6, model: str = WEEK7_MODEL) -> Dict:
    """ReAct loop restricted to `allowed` tool names (narrow tools are the point of a worker)."""
    schemas = [s for s in host.schemas() if s["function"]["name"] in allowed]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    calls: List[Dict] = []
    for _ in range(max_laps):
        resp = llm(messages, meter, handoff, tools=schemas, model=model)
        if resp.get("error"):
            if "tool_use_failed" in resp["error"] or "Failed to call a function" in resp["error"]:
                messages.append({"role": "user", "content": "Malformed tool call. Call the tool again with valid JSON arguments."})
                continue
            return {"text": "", "error": resp["error"], "calls": calls}
        tcs = resp.get("tool_calls") or []
        if not tcs:
            return {"text": resp.get("content") or "", "error": None, "calls": calls}
        messages.append({"role": "assistant", "content": resp.get("content") or None, "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}} for c in tcs]})
        for c in tcs:
            try:
                args = json.loads(c["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            if c["name"] not in allowed:
                out = {"isError": True, "text": f"Tool '{c['name']}' is not available to this worker. Available: {', '.join(allowed)}."}
            else:
                out = host.call(c["name"], args)
            calls.append({"tool": c["name"], "args": args, "is_error": out["isError"]})
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": ("ERROR: " if out["isError"] else "") + out["text"]})
    return {"text": "", "error": "max_laps", "calls": calls}
