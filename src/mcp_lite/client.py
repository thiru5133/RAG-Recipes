"""Minimal MCP client over a subprocess's stdio, with a raw wire recorder.

`wire` keeps every frame exactly as it crossed the pipe, so a handshake can be
captured verbatim (Week 9 wire.json) instead of reconstructed from memory.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

from mcp_lite import PROTOCOL_VERSION


class McpError(RuntimeError):
    pass


class McpClient:
    def __init__(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None,
                 cwd: Optional[str] = None, timeout_s: float = 30.0):
        self.name = name
        self._cmd = [command, *args]
        self._env = {**os.environ, **(env or {})}
        self._cwd = cwd
        self._timeout = timeout_s
        self._proc: Optional[subprocess.Popen] = None
        self._lines: "queue.Queue[Optional[str]]" = queue.Queue()
        self._next_id = 0
        self.wire: List[Dict[str, Any]] = []
        self.server_info: Dict[str, Any] = {}

    # ── lifecycle ───────────────────────────────────────────────────────
    def start(self) -> Dict:
        self._proc = subprocess.Popen(
            self._cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1, env=self._env, cwd=self._cwd,
        )
        threading.Thread(target=self._pump, daemon=True).start()
        init = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "recipe-agent-host", "version": "0.9.0"},
        })
        self.server_info = init.get("serverInfo", {})
        self.notify("notifications/initialized")
        return init

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=3)
            except Exception:
                self._proc.kill()

    def _pump(self) -> None:
        for line in self._proc.stdout:
            self._lines.put(line.rstrip("\n"))
        self._lines.put(None)

    # ── JSON-RPC ────────────────────────────────────────────────────────
    def _send(self, obj: Dict) -> None:
        raw = json.dumps(obj, ensure_ascii=False)
        self.wire.append({"dir": "client->server", "raw": raw})
        self._proc.stdin.write(raw + "\n")
        self._proc.stdin.flush()

    def notify(self, method: str, params: Optional[Dict] = None) -> None:
        msg: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)

    def request(self, method: str, params: Optional[Dict] = None) -> Dict:
        self._next_id += 1
        rid = self._next_id
        msg: Dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        deadline = time.time() + self._timeout
        while True:
            try:
                line = self._lines.get(timeout=max(0.05, deadline - time.time()))
            except queue.Empty:
                raise McpError(f"{self.name}: timeout waiting for {method}")
            if line is None:
                raise McpError(f"{self.name}: server closed the pipe during {method}")
            self.wire.append({"dir": "server->client", "raw": line})
            resp = json.loads(line)
            if resp.get("id") != rid:
                continue
            if "error" in resp:
                raise McpError(f"{self.name}: {method}: {resp['error'].get('message')}")
            return resp["result"]

    # ── MCP methods ─────────────────────────────────────────────────────
    def list_tools(self) -> List[Dict]:
        tools: List[Dict] = []
        cursor = None
        while True:
            res = self.request("tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(res.get("tools", []))
            cursor = res.get("nextCursor")
            if not cursor:
                return tools

    def call_tool(self, name: str, arguments: Dict) -> Dict:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def list_resources(self) -> List[Dict]:
        return self.request("resources/list", {}).get("resources", [])

    def read_resource(self, uri: str) -> str:
        res = self.request("resources/read", {"uri": uri})
        return "\n".join(c.get("text", "") for c in res.get("contents", []))
