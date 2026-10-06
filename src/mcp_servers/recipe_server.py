"""Server one: our own recipe MCP server (search, scale, per-recipe allergen swaps).

Wraps the same pure functions the Week 7/8 agent called in-process; the agent
now reaches them over MCP instead. No model call lives here.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import tools as impl  # noqa: E402
from mcp_lite.server import McpServer, ToolError  # noqa: E402

server = McpServer("recipe-server", "1.0.0")


@server.tool(
    "search_recipes",
    "Search recipes by name or cuisine.",
    {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
)
def search_recipes(args):
    return impl.search_recipes(args.get("query", ""))


@server.tool(
    "scale_recipe",
    "Scale ONE recipe's ingredient quantities to a target serving count and return the scaled "
    "ingredient table plus the method steps. Call this AFTER search_recipes has given you a "
    "recipe_id: ids look like 'R001' and a dish name such as 'shakshuka' is not an id, so never "
    "guess one. Does not search, does not check allergens, does not swap ingredients. If it "
    "returns an error, the message tells you the next call to make.",
    {"type": "object",
     "properties": {
         "recipe_id": {"type": "string",
                       "description": "Card id returned by search_recipes, e.g. 'R006'. Not a dish name."},
         "servings": {"type": "integer", "description": "Target serving count, 1 or more."}},
     "required": ["recipe_id", "servings"]},
)
def scale_recipe(args):
    rid = args.get("recipe_id", "")
    out = impl.scale_recipe(rid, int(args.get("servings") or 1))
    if out.get("error"):
        raise ToolError(
            f"No recipe has id '{rid}'. Valid ids are {', '.join(impl.RECIPE_IDS)}; a dish name is not an id. "
            f"Call search_recipes with the dish name (e.g. query='shakshuka') to get its id, "
            f"then call scale_recipe again with that id."
        )
    return out


@server.tool(
    "get_allergen_profile",
    "Get the allergen profile for a recipe.",
    {"type": "object",
     "properties": {"recipe_id": {"type": "string"}, "allergen": {"type": "string"}},
     "required": ["recipe_id", "allergen"]},
)
def get_allergen_profile(args):
    out = impl.get_allergen_profile(args.get("recipe_id", ""), args.get("allergen", ""))
    if out.get("error"):
        raise ToolError("Error 4")
    return out


def _allergen_matrix() -> str:
    """Standing context, not a tool: the app attaches it, the model never fetches it."""
    rows = ["| recipe_id | title | " + " | ".join(impl.ALLERGENS) + " |",
            "|---|---|" + "---|" * len(impl.ALLERGENS)]
    for rid, card in impl.catalog().items():
        flags = []
        for a in impl.ALLERGENS:
            hit = any(impl._hits_allergen(r["name"], a) for r in card["ingredients"])
            flags.append("yes" if hit else "-")
        rows.append(f"| {rid} | {card['title']} | " + " | ".join(flags) + " |")
    return "# Allergen matrix (as written on the cards)\n\n" + "\n".join(rows) + "\n"


server.resource(
    "recipes://allergen-matrix", "allergen-matrix",
    "Recipe x allergen-class matrix for all six cards.", _allergen_matrix,
)

if __name__ == "__main__":
    server.serve()
