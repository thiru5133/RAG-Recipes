"""Minimal MCP server: initialize, tools/list, tools/call, resources/list|read, ping.

stdout is the protocol channel. Anything human-readable goes to stderr.
There is no model call in here — a server exposes a capability and returns
data; the host decides when to call it and runs the model.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, List, Optional

from mcp_lite import PROTOCOL_VERSION


class ToolError(Exception):
    """Raised by a tool body. Becomes a tools/call result with isError=true,
    so the model sees the message and can recover (it is not a protocol error)."""


class McpServer:
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}

    # ── registration ────────────────────────────────────────────────────
    def tool(self, name: str, description: str, input_schema: Dict) -> Callable:
        def deco(fn: Callable[[Dict], Any]) -> Callable:
            self._tools[name] = {
                "spec": {"name": name, "description": description, "inputSchema": input_schema},
                "fn": fn,
            }
            return fn
        return deco

    def resource(self, uri: str, name: str, description: str, reader: Callable[[], str],
                 mime_type: str = "text/markdown") -> None:
        self._resources[uri] = {
            "spec": {"uri": uri, "name": name, "description": description, "mimeType": mime_type},
            "reader": reader,
        }

    # ── dispatch ────────────────────────────────────────────────────────
    def handle(self, msg: Dict) -> Optional[Dict]:
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}
        if mid is None:  # notification: never answered
            return None
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        **({"resources": {}} if self._resources else {}),
                    },
                    "serverInfo": {"name": self.name, "version": self.version},
                }
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": [t["spec"] for t in self._tools.values()]}
            elif method == "tools/call":
                result = self._call(params)
            elif method == "resources/list":
                result = {"resources": [r["spec"] for r in self._resources.values()]}
            elif method == "resources/read":
                uri = params.get("uri")
                res = self._resources.get(uri)
                if not res:
                    return _error(mid, -32002, f"resource not found: {uri}")
                result = {"contents": [{"uri": uri, "mimeType": res["spec"]["mimeType"],
                                        "text": res["reader"]()}]}
            else:
                return _error(mid, -32601, f"method not found: {method}")
        except Exception as exc:  # genuine server fault -> protocol error
            return _error(mid, -32603, f"{type(exc).__name__}: {exc}")
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def _call(self, params: Dict) -> Dict:
        name = params.get("name")
        tool = self._tools.get(name)
        if tool is None:
            # Unknown tool is a caller mistake the model can fix: report it as a tool error.
            known = ", ".join(sorted(self._tools))
            return _text(f"No tool named '{name}'. Available tools: {known}.", True)
        try:
            out = tool["fn"](params.get("arguments") or {})
        except ToolError as exc:
            return _text(str(exc), True)
        return _text(out if isinstance(out, str) else json.dumps(out, ensure_ascii=False), False)

    def serve(self) -> None:
        print(f"[{self.name}] ready", file=sys.stderr, flush=True)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                out = _error(None, -32700, "parse error")
            else:
                out = self.handle(msg)
            if out is not None:
                sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
                sys.stdout.flush()


def _text(text: str, is_error: bool) -> Dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _error(mid: Any, code: int, message: str) -> Dict:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}
