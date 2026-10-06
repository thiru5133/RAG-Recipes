# Bonus — one gateway front door, audit line per call, scoped token

Agent config: `config/mcp_servers.gateway.json` (one server: the gateway). Question: `For 100 g of paneer, give me the calories and protein, and tell me which allergens it has.`


## full scope (`tok-recipe-agent-full`)

tools the agent discovered through the single front door: 5 — search_recipes, scale_recipe, get_allergen_profile, get_ingredient_allergens, get_ingredient_nutrition

Trace:

- `get_ingredient_nutrition({"name": "paneer"})` -> ok: {"ingredient": "paneer", "per_100g": {"kcal": 321, "protein_g": 21, "fat_g": 25, "carbs_g": 3.6}}

Audit lines written by the gateway:

```
{"ts": "2026-10-01T21:05:29", "caller": "recipe-agent", "tool": "get_ingredient_nutrition", "downstream": "ingredient_db", "queried": "paneer", "decision": "ALLOW", "is_error": false}
```

Final answer: Paneer (100 g): 321 kcal, 21 g protein.  
Allergen: dairy.

## allergen-only scope (`tok-recipe-agent-allergen-only`)

tools the agent discovered through the single front door: 5 — search_recipes, scale_recipe, get_allergen_profile, get_ingredient_allergens, get_ingredient_nutrition

Trace:

- `get_ingredient_nutrition({"name": "paneer"})` -> ERROR: Access denied: 'get_ingredient_nutrition' is outside this session's scope. Nutrition lookups are switched off for this session. Do not guess nutrition numbers: tell the user nutrition is unavailable here, and answer with the aller
- `get_ingredient_allergens({"name": "paneer"})` -> ok: {"ingredient": "paneer", "allergens": ["dairy"]}

Audit lines written by the gateway:

```
{"ts": "2026-10-01T21:05:41", "caller": "recipe-agent", "tool": "get_ingredient_nutrition", "downstream": "ingredient_db", "queried": "paneer", "decision": "DENY", "is_error": true}
{"ts": "2026-10-01T21:05:48", "caller": "recipe-agent", "tool": "get_ingredient_allergens", "downstream": "ingredient_db", "queried": "paneer", "decision": "ALLOW", "is_error": false}
```

Final answer: I’m sorry, but nutrition data (calories and protein) is not available in this session.  
Allergen information for paneer: **dairy**.

Changed lines in agent/mcp_agent.py vs `week9-server-two`: 0
