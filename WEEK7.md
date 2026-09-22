# Week 7 — agent loop vs fixed workflow

The question is not “can we build an agent.” It is: **does recipe adaptation need a loop, or would three hard-coded steps be faster, cheaper, and more debuggable?** Settled with four numbers, not an opinion.

## The task both systems do

Find the recipe, scale it to the requested servings, swap an allergen if asked, return the method. Same ten requests. Same three tools. Same JSON contract.

## The third tool

Existing two:

- `search_recipes` — match a dish query to a recipe_id. No ingredients.
- `scale_recipe` — multiply quantities. No search, no swap.

Added:

- `get_allergen_profile(recipe_id, allergen)` — **one** enum value per call (`nuts | dairy | gluten | fish | shellfish | egg | meat`). Returns `card_swap`, plus `introduces` / `leaves` when the substitute is itself an allergen.

Diff: `eval/week7/tool_description.diff`. Descriptions do not overlap.

## Two systems

**Agent** (`scripts/run_week7_agent.py`) — a loop. The model picks tools. Tokens are **summed across laps** (re-sending the whole message list every time). Four budgets checked every lap: `max_iters`, `max_tokens`, `max_cost`, `wall_clock`.

**Workflow** (`scripts/run_week7_workflow.py`) — hard-coded: parse → `search_recipes` → `scale_recipe` → at most **one** `get_allergen_profile` → assemble JSON in Python. No loop. It does not read `introduces` / `leaves`.

## The 10 requests

| id | class | What |
| --- | --- | --- |
| W01–W04 | scale_only | servings only |
| W05–W06 | single_allergen | dairy-free / nut-free paneer |
| W07–W09 | allergen_cascade | second swap depends on the first profile |
| W10 | cannot_adapt | gluten-free pizza; card forbids it |

Cascades (step 3 depends on step 2): vegan+nut-free paneer (cashews remain after dairy swap); vegan+GF chicken curry (soy introduces gluten); vegan shakshuka (dropping feta leaves the eggs).

## Race (same 10, `openai/gpt-oss-20b` for the loop; Groq 20B list price $0.075 / $0.30 per 1M)

| | agent | workflow |
| --- | ---: | ---: |
| pass rate | **9/10** | **7/10** |
| p50 latency | 41 576 ms | **<1 ms** |
| total tokens | 76 921 | **0** |
| cost / request | $0.001057 | **$0** |

Per-row log: `eval/week7/race.csv`.

Workflow tokens are 0 because the path is fixed and the tools are Python. That is the point, not a missing model call. The agent’s 76k tokens are every lap re-sent, not the last call only.

## Budget termination

`eval/week7/budget_termination.log` — W07 with `max_iters=2`. `stopped_by: max_iters`. It returned instead of spinning.

## Verdict

`eval/week7/verdict.md` (under 150 words).

The path does **not** vary for scale-only or single-allergen. Use the workflow. The path **does** vary for allergen-cascade: the next enum depends on `introduces` / `leaves`. That class is the one that forces an agent. Declaring the agent the overall winner would contradict the table: the workflow is ahead on latency, tokens, and cost. The agent only leads on pass rate, and only because of W07 and W09.

W08 beat both — a three-class cascade the agent stopped after four laps.

## Commands

```bash
python scripts/run_week7_agent.py --id W07
python scripts/run_week7_workflow.py --id W07
python scripts/run_week7_race.py
python scripts/run_week7_race.py --budget-demo
```

Model: `WEEK7_MODEL` (default `openai/gpt-oss-20b`). 120b was over the Groq day cap; both systems still share one model id.
