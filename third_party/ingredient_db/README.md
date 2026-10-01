# ingredient_db (stand-in for the content team's MCP server)

The content team's real server is not in this repo, so this directory holds a
stand-in with the same surface the brief describes: lookup by ingredient name,
allergen flags, per-100g nutrition. Treat it as the *third-party* server — the
agent never imports it; it is reached only through `config/mcp_servers.json`.

Deliberately third-party-shaped: its own allergen vocabulary (it adds `soy`),
exact-name lookup only, and an opaque `lookup failed` error. It appends every
query it receives to `logs/ingredient_db_queries.log` — that file is the
"what does it log" evidence for `eval/week9/risk_note.md`.
