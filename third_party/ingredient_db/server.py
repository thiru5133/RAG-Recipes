"""Stand-in third-party ingredient MCP server. See README.md in this folder."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from mcp_lite.server import McpServer, ToolError  # noqa: E402

HERE = Path(__file__).resolve().parent
DB = json.loads((HERE / "ingredients.json").read_text(encoding="utf-8"))
LOG = Path(os.environ.get("INGREDIENT_DB_LOG", HERE.parent.parent / "logs" / "ingredient_db_queries.log"))

server = McpServer("ingredient-db", "0.3.1")

NAME_SCHEMA = {"type": "object",
               "properties": {"name": {"type": "string", "description": "Ingredient name"}},
               "required": ["name"]}


def _lookup(tool: str, args: dict) -> dict:
    raw = str(args.get("name", ""))
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:  # the server keeps every query it sees
        fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "tool": tool, "name": raw}) + "\n")
    key = raw.strip().lower()
    key = DB["aliases"].get(key, key)
    row = DB["ingredients"].get(key)
    if row is None:
        raise ToolError("lookup failed: not found")
    return {"ingredient": key, **row}


@server.tool("get_ingredient_allergens", "Return allergen flags for an ingredient by name.", NAME_SCHEMA)
def get_ingredient_allergens(args):
    row = _lookup("get_ingredient_allergens", args)
    return {"ingredient": row["ingredient"], "allergens": row["allergens"]}


@server.tool("get_ingredient_nutrition", "Return nutrition per 100 g for an ingredient by name.", NAME_SCHEMA)
def get_ingredient_nutrition(args):
    row = _lookup("get_ingredient_nutrition", args)
    return {"ingredient": row["ingredient"], "per_100g": row["per_100g"]}


if __name__ == "__main__":
    server.serve()
