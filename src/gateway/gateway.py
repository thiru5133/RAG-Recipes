"""MCP gateway: one front door in front of N downstream MCP servers.

Upstream (the agent) sees a single server. Downstream servers come from
config/gateway_downstream.json. Every tools/call writes ONE audit line
(caller, tool, ingredient/query, decision) and is checked against the scope of
the token in $GATEWAY_TOKEN. A denial is returned as an isError tool result
whose text tells the model what to do next — it is not a protocol error.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent.mcp_agent import McpHost  # noqa: E402  (the gateway is a host to its downstreams)
from mcp_lite.server import McpServer, ToolError  # noqa: E402

AUDIT = Path(os.environ.get("GATEWAY_AUDIT_LOG", ROOT / "logs" / "gateway_audit.log"))
TOKENS = json.loads((ROOT / "config" / "gateway_tokens.json").read_text(encoding="utf-8"))["tokens"]
SCOPE = TOKENS.get(os.environ.get("GATEWAY_TOKEN", ""))


def _subject(args: dict) -> str:
    for k in ("name", "query", "recipe_id"):
        if args.get(k):
            return str(args[k])
    return ""


def _audit(caller: str, tool: str, downstream: str, args: dict, decision: str, is_error: bool) -> None:
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    line = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "caller": caller, "tool": tool,
            "downstream": downstream, "queried": _subject(args), "decision": decision, "is_error": is_error}
    with AUDIT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")


def build() -> McpServer:
    host = McpHost(ROOT / "config" / "gateway_downstream.json").connect()
    server = McpServer("gateway", "1.0.0")
    caller = SCOPE["caller"] if SCOPE else "unknown"

    def make(tool_name: str, downstream: str):
        def fn(args):
            allowed = SCOPE and (SCOPE["allow"] == ["*"] or tool_name in SCOPE["allow"])
            if not allowed:
                _audit(caller, tool_name, downstream, args, "DENY", True)
                msg = (SCOPE or {}).get("deny_message") or "This token is not valid for this gateway."
                raise ToolError(f"Access denied: '{tool_name}' is outside this session's scope. {msg}")
            out = host.call(tool_name, args)
            _audit(caller, tool_name, downstream, args, "ALLOW", out["isError"])
            if out["isError"]:
                raise ToolError(out["text"])
            return out["text"]
        return fn

    for t in host.tools:
        server.tool(t["name"], t.get("description", ""), t["inputSchema"])(make(t["name"], t["server"]))
    for name, client in host.clients.items():
        for r in client.list_resources():
            server.resource(r["uri"], r["name"], r.get("description", ""),
                            (lambda c=client, u=r["uri"]: c.read_resource(u)), r.get("mimeType", "text/markdown"))
    return server


if __name__ == "__main__":
    build().serve()
