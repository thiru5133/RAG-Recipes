"""Hand-built MCP over stdio (JSON-RPC 2.0, newline-delimited).

The official `mcp` SDK needs Python >= 3.10; this repo's venv is 3.9. The wire
protocol is small enough to write by hand, which is the point of Week 9: the
server exposes capabilities, the host runs the model.
"""
PROTOCOL_VERSION = "2025-06-18"
