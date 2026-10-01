"""Week 9 agent: the host side of MCP.

This module names NO tools. It reads config/mcp_servers.json, starts every
server listed there, asks each one `tools/list`, hands whatever came back to the
model, and routes each model tool call to the server that owns that name.
Adding a server is therefore a config edit; `git diff` on this file stays empty.

The model call lives here (the host). Servers only expose capabilities.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from config import (AGENT_MAX_COST_USD, AGENT_MAX_ITERS, AGENT_MAX_TOKENS, AGENT_MAX_WALL_MS,
                    GROQ_PRICES, ROOT, WEEK7_MODEL)
from generate import complete_messages
from agent.contract import cost_usd
from mcp_lite.client import McpClient, McpError

DEFAULT_CONFIG = ROOT / "config" / "mcp_servers.json"

SYSTEM = """You are a recipe assistant. Use the tools you are given; read each tool's description to decide which one fits.
Reference data attached by the app (if any) appears below. Do not fetch what is already attached.
Never state an allergen flag or a nutrition number that a tool did not return. If a tool returns an error, use its text to decide your next step.
Answer briefly in plain text when you are done."""


def _expand(value: str) -> str:
    value = value.replace("${PYTHON}", sys.executable)
    return re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), value)


class McpHost:
    def __init__(self, config_path: Path = DEFAULT_CONFIG):
        cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.clients: Dict[str, McpClient] = {}
        self.attach: Dict[str, List[str]] = {}
        for name, spec in cfg["servers"].items():
            self.clients[name] = McpClient(
                name, _expand(spec["command"]), [_expand(a) for a in spec.get("args", [])],
                env={k: _expand(v) for k, v in (spec.get("env") or {}).items()}, cwd=str(ROOT),
            )
            self.attach[name] = spec.get("attach_resources", [])
        self.tools: List[Dict] = []          # {"server", "name", "description", "inputSchema"}
        self.route: Dict[str, str] = {}      # tool name -> server name
        self.attached = ""

    def connect(self) -> "McpHost":
        for name, client in self.clients.items():
            client.start()
            for t in client.list_tools():
                if t["name"] in self.route:
                    raise McpError(f"tool name collision: {t['name']} on {self.route[t['name']]} and {name}")
                self.route[t["name"]] = name
                self.tools.append({"server": name, **t})
            for uri in self.attach[name]:
                self.attached += client.read_resource(uri) + "\n"
        return self

    def schemas(self) -> List[Dict]:
        return [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                                  "parameters": t["inputSchema"]}} for t in self.tools]

    def call(self, name: str, args: Dict) -> Dict:
        server = self.route.get(name)
        if server is None:
            return {"server": None, "isError": True, "text": f"No tool named '{name}'. Available tools: {', '.join(sorted(self.route))}."}
        res = self.clients[server].call_tool(name, args)
        text = "\n".join(c.get("text", "") for c in res.get("content", []))
        return {"server": server, "isError": bool(res.get("isError")), "text": text}

    def close(self) -> None:
        for c in self.clients.values():
            c.close()


def discover(config_path: Path = DEFAULT_CONFIG) -> List[Dict]:
    """tools/list across every configured server — the source for tool counts."""
    host = McpHost(config_path).connect()
    try:
        return [{"server": t["server"], "name": t["name"]} for t in host.tools]
    finally:
        host.close()


def run_mcp_agent(request_text: str, *, config_path: Path = DEFAULT_CONFIG, model: str = WEEK7_MODEL,
                  max_iters: int = AGENT_MAX_ITERS, max_tokens: int = AGENT_MAX_TOKENS,
                  max_cost_usd: float = AGENT_MAX_COST_USD, max_wall_ms: int = AGENT_MAX_WALL_MS,
                  prefix_messages: Optional[List[Dict]] = None, host: Optional[McpHost] = None) -> Dict:
    own_host = host is None
    host = host or McpHost(config_path).connect()
    system = SYSTEM + (f"\n\n{host.attached}" if host.attached else "")
    messages: List[Dict] = [{"role": "system", "content": system}, {"role": "user", "content": request_text}]
    messages += prefix_messages or []
    trace: List[Dict] = []
    prompt_tokens = completion_tokens = 0
    answer, stopped_by, laps = "", None, 0
    started = time.perf_counter()
    inp, outp = GROQ_PRICES.get(model, (0.15, 0.60))
    try:
        for lap in range(1, max_iters + 1):
            laps = lap
            spent = cost_usd(prompt_tokens, completion_tokens, inp, outp)
            if prompt_tokens + completion_tokens >= max_tokens:
                stopped_by = "max_tokens"; break
            if spent >= max_cost_usd:
                stopped_by = "max_cost"; break
            if (time.perf_counter() - started) * 1000 >= max_wall_ms:
                stopped_by = "wall_clock"; break
            resp = complete_messages(messages, model=model, max_tokens=1200, tools=host.schemas())
            err = resp.get("error") or ""
            if "tool_use_failed" in err or "Failed to call a function" in err:
                messages.append({"role": "user", "content": "Your last tool call was malformed. Call the tool again with valid JSON arguments."})
                trace.append({"lap": lap, "event": "malformed_tool_call"})
                continue
            if err:
                trace.append({"lap": lap, "event": "model_error", "error": err}); stopped_by = "error"; break
            usage = resp.get("usage") or {}
            prompt_tokens += int(usage.get("prompt_tokens") or 0)
            completion_tokens += int(usage.get("completion_tokens") or 0)
            calls = resp.get("tool_calls") or []
            content = resp.get("content") or ""
            if not calls:
                answer, stopped_by = content, "completed"; break
            messages.append({"role": "assistant", "content": content or None, "tool_calls": [
                {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in calls]})
            for c in calls:
                try:
                    args = json.loads(c["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                out = host.call(c["name"], args)
                trace.append({"lap": lap, "tool": c["name"], "server": out["server"], "args": args,
                              "is_error": out["isError"], "result": out["text"][:300]})
                body = ("ERROR: " if out["isError"] else "") + out["text"]
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": body})
        else:
            stopped_by = "max_iters"
    finally:
        if own_host:
            host.close()
    return {
        "answer": answer, "stopped_by": stopped_by or "max_iters", "laps": laps,
        "tokens": prompt_tokens + completion_tokens, "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost_usd(prompt_tokens, completion_tokens, inp, outp),
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "tools_discovered": [t["name"] for t in host.tools], "trace": trace, "messages": messages,
    }
