# Week 9 — MCP: add a tool server without touching the agent

**One sentence:** the recipe agent now gets its tools from MCP servers listed in a config file, so a second server (the content team's ingredient database) went live by editing four lines of JSON, and `git diff` proves zero agent lines changed.

Branch: `week9-mcp-ingredient-server` (from `origin/week8-agent-failure-modes`, the latest branch that contains the agent). Evidence lives in `eval/week9/`.

## The idea in 60 seconds (for someone new to MCP)

- **MCP** is a standard way for an AI app to discover and call tools. Messages are JSON-RPC 2.0, one per line over stdin/stdout.
- **Three roles.** The *server* exposes capabilities and runs no model. The *host* (our agent) runs the model and decides when to call a tool. The *model* only emits "call tool X with args Y".
- **Discovery.** The host asks each server `tools/list` and gets name, description and input schema for every tool. It hands those to the model unchanged. Nothing about tools is hard-coded in the agent.
- **Tools vs resources.** A tool is something the model chooses to invoke. A resource is standing context the app attaches itself. The recipe×allergen matrix is a resource (`recipes://allergen-matrix`), because it is needed every turn and should be in the prompt, not fetched on demand.

```
user ─▶ HOST (agent/mcp_agent.py) ──model call (Groq)──▶ "call get_ingredient_nutrition"
          │  tools/list, tools/call (JSON-RPC over stdio)
          ├──▶ recipes server        (src/mcp_servers/recipe_server.py)   our own
          └──▶ ingredient_db server  (third_party/ingredient_db/server.py) the content team's
```

## What was built

| Piece | Path | Notes |
| --- | --- | --- |
| MCP protocol, hand-built | `src/mcp_lite/` | The official `mcp` SDK needs Python ≥ 3.10; this venv is 3.9. The protocol is small, and writing it makes the wire visible. |
| Server one (own) | `src/mcp_servers/recipe_server.py` | `search_recipes`, `scale_recipe`, `get_allergen_profile`, plus the allergen-matrix resource. |
| Server two (third party) | `third_party/ingredient_db/` | `get_ingredient_allergens`, `get_ingredient_nutrition`. **A stand-in:** the content team's real server is not in this repo. |
| The agent | `src/agent/mcp_agent.py` | Names no tools. Reads `config/mcp_servers.json`, starts servers, discovers, routes. |
| Config | `config/mcp_servers.json` | The only file that changed to add server two. |

## Results, requirement by requirement

**1. Server two called, tool name in the trace** — `eval/week9/server_two_query.json`

```
Q: How much protein is in 100 g of paneer, and does paneer contain any allergens?
lap 1  ingredient_db::get_ingredient_nutrition {"name": "paneer"}
```

**2. Zero agent lines changed** — `eval/week9/agent_diff.txt`, `config_diff.txt`

`git diff week9-server-one week9-server-two -- src/agent/mcp_agent.py src/mcp_lite` prints nothing. The whole-repo diff is `config/mcp_servers.json | 4 ++++`. The two tags are commits `c495710` and `20b7636`. Server two's code already sat in the repo, unreferenced, at the first commit, so the second commit is purely a config change.

**3. Tool counts from `tools/list`** — `eval/week9/tool_counts.txt`

**3 before → 5 after.**
Before: `search_recipes, scale_recipe, get_allergen_profile`.
After: those three plus `get_ingredient_allergens, get_ingredient_nutrition`.
The script launches the servers from each config and counts what `tools/list` returns.

**4. Raw wire, annotated by hand** — `eval/week9/wire.json`

Seven frames captured verbatim from the pipe: `initialize` request and response, the `notifications/initialized` notification (no `id`, so no reply), `tools/list` request and response, and `tools/call` request and response. Every top-level field of every frame has a hand-written annotation.

> **Where the model call happens:** in the host (`mcp_agent.py` → Groq), between the `tools/list` result coming in and the `tools/call` going out. It does **not** happen in the MCP server or on the wire; the server only does a dictionary lookup.

**5. Docstring as prompt + recoverable error** — `eval/week9/error_before_after.md`

`scale_recipe` went from `"Scale a recipe to a number of servings."` / `Error 3` to a description that says when to call it, what an id looks like, what it does not do, and an error that says `No recipe has id 'shakshuka'. Valid ids are R001…R006 … Call search_recipes with the dish name … then call scale_recipe again.` The same failing call was injected, so the only variable was the text.

**Honest result:** the recovery rate did not move (5/5 before, 5/5 after). `gpt-oss-20b` already recovered from `Error 3`. What moved was cost: about 35% more tokens (2072 → 2799), because the longer docstring is re-sent every lap. It also made the path deterministic: with the matrix attached, the old model skipped `search_recipes`, while the new error always sends it there (one extra call). The `Error 3` here was a *constructed* "before", since no earlier Week 9 build existed, so treat the baseline as a controlled comparison, not history.

**6. Risk note** — `eval/week9/risk_note.md` (exactly five lines). Verdict: ship with conditions. Pin the version, scrub the environment, route through the audit gateway with an allergen-only scope, and read `lookup failed` as "unverified", never as "no allergens".
Writing it found a real bug: the client passed the full parent environment (including `GROQ_API_KEY`) to every server subprocess. `src/mcp_lite/client.py` now passes only `PATH/HOME/LANG/...` plus the variables named in config. The note describes the stand-in. The real server's authorship, logging and token scope must be confirmed with the content team.

**Bonus: gateway + scoped token** — `eval/week9/bonus_gateway.md`

`src/gateway/gateway.py` is itself an MCP server in front of both servers. The agent's config (`config/mcp_servers.gateway.json`) lists one server, and the agent diff is again 0 lines. Each `tools/call` writes one audit line: caller, tool, downstream, ingredient queried, ALLOW/DENY. With the allergen-only token, `get_ingredient_nutrition` was denied and the model received:
`Access denied … Do not guess nutrition numbers: tell the user nutrition is unavailable here, and answer with the allergen flags instead.`
It then called `get_ingredient_allergens` and answered accordingly. The denial is a tool result with `isError: true`, not a protocol error, which is why the model can recover. The denied tool is still listed on purpose; a stricter design would hide it.

## What could still go wrong (named, not fixed)

- **Right answer, unverified path.** In two runs the model said paneer is "dairy" without calling an allergen tool (`get_ingredient_nutrition` returns no allergens). It was correct by luck. This is the Week 8 outcome-vs-trajectory gap again, and the system prompt alone does not stop it.
- **The stand-in is not the real server.** Its opaque `lookup failed` error, its exact-name lookup and its query log are my assumptions about a third-party server.
- **Nutrition numbers are rounded reference values**, not a certified source.
- **One model, five trials per cell.** Differences of one trial are noise.

## Reproduce

```bash
python scripts/run_week9_agent.py "How many kcal in 100 g of paneer?"
python scripts/week9_evidence.py              # agent_diff, config_diff, tool_counts, server-two query
python scripts/week9_capture_wire.py          # wire.json
python scripts/week9_error_before_after.py    # error_before_after.md (20 live model runs)
python scripts/week9_gateway_demo.py          # bonus_gateway.md
git tag: week9-server-one, week9-server-two
```
