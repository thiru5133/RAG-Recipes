"""Capture the raw initialize -> tools/list -> tools/call exchange against the
ingredient server and attach hand-written annotations to every top-level field.

    python scripts/week9_capture_wire.py

The `raw` strings are exactly what crossed the pipe (McpClient.wire). The
annotations below are written by hand, not generated from the frames.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mcp_lite.client import McpClient  # noqa: E402

ANN = {
    "initialize.request": {
        "jsonrpc": "JSON-RPC version tag. Always the string \"2.0\"; lets the peer reject non-JSON-RPC garbage.",
        "id": "Request id (1). The response echoes it so replies can be matched to requests. Present => a reply is expected.",
        "method": "What the host is asking: open the session and negotiate versions/capabilities.",
        "params": "Arguments. protocolVersion = the spec revision the host speaks; capabilities = what the HOST offers the server (none here); clientInfo = who is connecting, for server-side logs.",
    },
    "initialize.response": {
        "jsonrpc": "Version tag, \"2.0\".",
        "id": "Echo of the request id (1) — this is the reply to initialize.",
        "result": "Success payload (an error would use an `error` key instead, never both). protocolVersion = revision the server agreed to; capabilities.tools = this server offers tools (listChanged:false = the list never changes mid-session); serverInfo = name/version, the identity that shows up in traces.",
    },
    "initialized.notification": {
        "jsonrpc": "Version tag, \"2.0\".",
        "method": "Notification that the host finished the handshake. Handshake step 3.",
        "(no id)": "There is deliberately NO id: a notification is fire-and-forget, the server must not answer it.",
    },
    "tools.list.request": {
        "jsonrpc": "Version tag, \"2.0\".",
        "id": "Request id (2).",
        "method": "Ask the server to describe every tool it exposes — this is DISCOVERY; the agent has no hard-coded list.",
        "params": "Empty object; a `cursor` here would page a long list.",
    },
    "tools.list.response": {
        "jsonrpc": "Version tag, \"2.0\".",
        "id": "Echo of request id (2).",
        "result": "{tools:[...]}. Each tool has name (what the model will call), description (the PROMPT the model reads to choose it) and inputSchema (JSON Schema the model's arguments must satisfy). The host forwards these three fields to the model verbatim. No nextCursor => this is the full list.",
    },
    "tools.call.request": {
        "jsonrpc": "Version tag, \"2.0\".",
        "id": "Request id (3).",
        "method": "Execute one tool. Sent by the HOST, only after the MODEL emitted a tool call.",
        "params": "name = which tool (from tools/list); arguments = the model's JSON args, validated against inputSchema by the host side.",
    },
    "tools.call.response": {
        "jsonrpc": "Version tag, \"2.0\".",
        "id": "Echo of request id (3).",
        "result": "content = list of typed blocks handed back to the model (here one text block holding JSON); isError = tool-level failure flag. false => data. true would still be a successful JSON-RPC reply, so the model can read the message and recover; a transport/protocol failure would be a top-level `error` instead.",
    },
}
MODEL_LINE = ("The model call happens in the host (agent/mcp_agent.py -> complete_messages -> Groq), between frame 5 "
              "(tools/list result in) and frame 6 (tools/call out); it does NOT happen in the MCP server or on the wire — "
              "the server only runs a dictionary lookup and returns data.")
KEYS = ["initialize.request", "initialize.response", "initialized.notification",
        "tools.list.request", "tools.list.response", "tools.call.request", "tools.call.response"]


def main() -> None:
    c = McpClient("ingredient_db", sys.executable, ["third_party/ingredient_db/server.py"], cwd=str(ROOT))
    c.start()
    c.list_tools()
    c.call_tool("get_ingredient_nutrition", {"name": "paneer"})
    c.close()
    assert len(c.wire) == 7, len(c.wire)
    frames = []
    for i, (w, key) in enumerate(zip(c.wire, KEYS), 1):
        frames.append({"n": i, "dir": w["dir"], "raw": w["raw"], "parsed": json.loads(w["raw"]),
                       "annotations": ANN[key]})
    out = {"server": "third_party/ingredient_db/server.py (stand-in for the content team's server)",
           "transport": "stdio, one JSON-RPC message per line",
           "where_the_model_call_happens": MODEL_LINE, "frames": frames}
    path = ROOT / "eval" / "week9" / "wire.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {path}")
    for f in frames:
        print(f["n"], f["dir"], f["raw"][:110])


if __name__ == "__main__":
    main()
