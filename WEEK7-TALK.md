# Week 7 — speaking brief

What we built, how the race came out, and the numbers to say out loud.

About **6–8 minutes** if you read the long version. Use the **90-second version** if they cut you short.

---

## Open (20 seconds)

Week 5 asked what kind of failure we had. Week 6 asked whether the substitution judge meant anything. Week 7 is a different question: **does recipe adaptation need an agent loop, or would three hard-coded steps be faster, cheaper, and more debuggable?**

We did not settle that with an opinion. We ran the same ten requests through both systems and compared four numbers.

---

## What we built — same job, two systems

Find the recipe, scale it to the requested servings, swap an allergen if asked, return the method. **Same ten requests. Same three tools. Same JSON contract.**

**The agent** is a loop. The model picks tools. Tokens are summed across laps — we re-send the whole message list every time. Four budgets get checked every lap: `max_iters`, `max_tokens`, `max_cost`, `wall_clock`.

**The workflow** is hard-coded: parse, then `search_recipes`, then `scale_recipe`, then at most **one** `get_allergen_profile`, then assemble the JSON in Python. No loop. It does not read `introduces` or `leaves`.

The model for the loop is `openai/gpt-oss-20b`. Cost is Groq 20B list: $0.075 input / $0.30 output per million tokens.

---

## The three tools — one job each

Two we already had:

- `search_recipes` — match a dish query to a recipe_id. No ingredients.
- `scale_recipe` — multiply quantities. No search, no swap.

The third is `get_allergen_profile(recipe_id, allergen)`. One enum value per call: `nuts`, `dairy`, `gluten`, `fish`, `shellfish`, `egg`, or `meat`. It returns the swap the card writes, plus `introduces` and `leaves` when the substitute is itself an allergen.

The descriptions do not overlap. Search does not inspect allergens. Scale does not search. Profile does not rewrite the method. You can read the diff in `eval/week7/tool_description.diff`.

---

## The ten requests

Four classes. The mix is the experiment.

| id | class | What to say |
| --- | --- | --- |
| W01–W04 | scale_only | Servings only. Paneer to 8, chana for 2, pizza for 4, shakshuka for 8. |
| W05–W06 | single_allergen | Dairy-free paneer. Nut-free paneer. One profile call is enough. |
| W07–W09 | allergen_cascade | Second swap depends on the first profile. At least three of these. |
| W10 | cannot_adapt | Gluten-free pizza. The card forbids it. |

The three cascades, in spoken English:

**W07** — vegan and nut-free paneer. The dairy swap is not enough if cashews remain.

**W08** — vegan and gluten-free chicken curry. Replacing fish sauce with soy is not enough if soy carries wheat.

**W09** — vegan shakshuka. Dropping feta still leaves the eggs.

Those three are the only requests where the next tool call depends on what the last profile returned.

---

## The race — four numbers, two columns

Same ten. Per-row log is `eval/week7/race.csv`.

| | agent | workflow |
| --- | ---: | ---: |
| pass rate | **9/10** | **7/10** |
| p50 latency | 41 576 ms | **<1 ms** |
| total tokens | 76 921 | **0** |
| cost / request | $0.001057 | **$0** |

Say this next, or someone will think the workflow forgot to call a model.

Workflow tokens are **zero** because the path is fixed and the tools are Python. That is the point. The agent’s 76 921 tokens are every lap re-sent, not the last call only.

And do **not** declare the agent the overall winner. The workflow is ahead on latency, tokens, and cost. The agent only leads on pass rate, and only because of W07 and W09.

---

## What it resolves

The decision rule is: **if the path varies by input, use an agent; otherwise a workflow.**

Seven of the ten do not need a loop — scale-only and single-allergen are always search, then scale, then at most one profile. On those the workflow matches the agent at **7/7**, with 0 tokens and under a millisecond versus 42 seconds p50 and 76 921 tokens.

Three requests are allergen-cascade. The substitute itself carries another allergen, so the next enum depends on `introduces` and `leaves`. The workflow makes one profile call and scores **0/3**. The agent scores **2/3** — W07 vegan-and-nut-free paneer, and W09 vegan shakshuka.

**W08 beat both.** Vegan gluten-free chicken curry, soy introducing wheat. The agent stopped after four laps. That cascade class is the only one of the ten that forces an agent. It does not win the race.

---

## Budget termination — it stopped, it did not spin

We ran W07 with `max_iters=2`. Race default is 8. The log is `eval/week7/budget_termination.log`.

`stopped_by: max_iters`. Two laps. 4 113 tokens. It returned instead of calling the model again. Clean stop, not a spin.

---

## Close (the one sentence they should remember)

Recipe adaptation does not need an agent for every request. Use the workflow when the path is search, scale, one profile. Use the agent only when the next allergen depends on the last swap. The table does not let you call the agent the winner: 9/10 versus 7/10 on pass rate, and the workflow wins latency, tokens, and cost.

---

## 90-second version

Week 7 asked whether recipe adaptation needs an agent loop, or whether three hard-coded steps would be faster, cheaper, and more debuggable. Same ten requests, same three tools, same JSON contract. Search, scale, and one allergen profile — one job each, enums on the third, no overlapping descriptions.

Four scale-only, two single-allergen, three allergen-cascades, and a cannot-adapt gluten-free pizza. The race: agent 9/10, 41 576 ms p50, 76 921 tokens, $0.001057 a request. Workflow 7/10, under a millisecond, 0 tokens, $0. Workflow tokens are zero because the path is Python. The agent’s tokens are every lap re-sent.

The path does not vary for scale-only or single-allergen — workflow matches 7/7. It does vary for allergen-cascade: workflow 0/3, agent 2/3, W08 beat both. That class is the one that forces an agent. Do not call the agent the overall winner. Budget test: W07, `max_iters=2`, `stopped_by max_iters`. Clean stop.

---

## If they ask

**“So the agent won?”**
No. It won pass rate, 9/10 versus 7/10, and only because of two cascades. The workflow is ahead on latency, tokens, and cost. Declaring an overall winner would contradict the table.

**“Why are workflow tokens zero?”**
The path is fixed. The tools are Python. There is no model in that path. That is the comparison, not a missing call.

**“Why not always use the agent if it passes more?”**
Seven of ten never needed a loop. You would pay 42 seconds p50 and 76 921 tokens to match a workflow that already scores 7/7 on those.

**“What does allergen-cascade actually mean?”**
The next enum depends on what `get_allergen_profile` returned. Vegan paneer still has cashews. Soy for fish sauce still has wheat. Dropping feta still leaves the eggs. The workflow is allowed one profile call, so it misses them.

**“Did the agent at least finish W08?”**
No. W08 beat both. The agent stopped after four laps.

**“How do you know the loop doesn’t spin?”**
W07 with `max_iters=2`. `stopped_by: max_iters`. It checked the budget at the top of the next lap and returned.

**“What did you not do?”**
We did not pick a single system for production. We produced a decision rule. Path varies by input: agent. Path does not: workflow.

---

## Numbers cheat-sheet

| Claim | Number |
| --- | --- |
| Requests | 10 |
| Tools | 3 |
| Agent pass rate | 9/10 |
| Workflow pass rate | 7/10 |
| Agent p50 latency | 41 576 ms |
| Workflow p50 latency | <1 ms |
| Agent total tokens | 76 921 |
| Workflow total tokens | 0 |
| Agent cost / request | $0.001057 |
| Workflow cost / request | $0 |
| Groq 20B list | $0.075 / $0.30 per 1M |
| Path-fixed classes (workflow = agent) | 7/7 |
| Cascade: agent / workflow | 2/3 / 0/3 |
| W08 | both fail (agent 4 laps) |
| Budget demo | W07, `max_iters=2`, `stopped_by: max_iters` |
| Budget demo laps / tokens | 2 / 4 113 |

Run it:

```bash
python scripts/run_week7_agent.py --id W07
python scripts/run_week7_workflow.py --id W07
python scripts/run_week7_race.py
python scripts/run_week7_race.py --budget-demo
```

Model: `WEEK7_MODEL` (default `openai/gpt-oss-20b`). Longer write-up: `WEEK7.md`. Verdict: `eval/week7/verdict.md`. Per-row log: `eval/week7/race.csv`.
