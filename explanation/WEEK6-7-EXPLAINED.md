# Week 6 and 7 — judge, then agent (study notes)

Same six recipe cards. Week 6 asks whether the model that prints the quality score agrees with a human. Week 7 asks whether adapting a recipe needs a loop that picks tools, or three fixed steps.

`WEEK6.md` and `WEEK7.md` are the recaps. This file is the lesson.

---

## Week 6 — LLM judge

A substitution is a recipe rewritten under one constraint: vegan, nut-free, gluten-free, chicken breast instead of thigh. The food team was about to publish one model score for that. An allergy swap that is wrong is not a rounding error.

The judge is a second model call. It does not cook. It reads the constraint, the source card, and the substitution, then writes `VERDICT: PASS` or `VERDICT: FAIL`.

### What a human marks first

Week 5 was the manual read: 20 traces, one sentence each, then groups. Week 6 keeps that habit and changes the object. Twenty-seven substitutions are frozen. Two of them are replayed from week 5 traces: T08 (`d04bc002`, incomplete vegan paneer) and T06 (`fdceede3`, hybrid gate refusal on an unfamiliar curry paste). Each of the 27 is tagged with one week-5 failure mode so the score can be sliced later.

A person then marks all 27 **PASS or FAIL by hand**, saved in `eval/week6/labels_25.json` at 16:10:10Z. No judge verdict is in that file. The judge is not allowed to run until the file exists.

The one question on the label:

> Does this substitution honour the constraint without a new hazard, and without contradicting a swap the card already specifies?

Five easier checks never go to the model. `src/assertions.py` does them in Python: method ingredients listed, allergen warning present, oven temperature has a unit, servings echoed, quantities are numbers. That is **5 assertions, 1 judged criterion**. Paying a model to see whether `"250 C"` has a unit is an expensive `if`.

### Judge v1 mismatches the hand labels

`eval/week6/judge_v1.txt` is a short prompt with no examples. "Is this a reasonable honouring of the constraint?"

Agreement with the hand labels: **25/27 (92.6%)**. Two mismatches, both the same shape. The human said FAIL. v1 said PASS.

| id | What was asked | Card | v1 | Human |
| --- | --- | --- | --- | --- |
| **S05** | Gluten-free margherita, rice flour | Cannot be made gluten-free without changing the dough entirely | PASS | FAIL |
| **S19** | 3-day sourdough starter instead of yeast | 3 g fresh yeast, 24-hour fridge. No starter | PASS | FAIL |

Both times the judge used general cooking knowledge. A cookbook might call rice flour a gluten-free flour, and a starter a yeast substitute. This card does not. The human was right. Labels were not edited after the judge ran.

The headline **20/27 (74%)** product pass rate hides the slice that matters. On v1, flavour was 9/11 and structural swaps were 5/5. Allergen safety was 6/9. The two week-5 regressions were **0/2**.

### v2 is the same judge with the prompt updated

`prediction.txt` is written after v1 and before v2: those two cases, shown as FAIL examples, will flip to FAIL, and card-specified swaps (S08 lemon for amchur, S14 tempeh for tofu) will stay PASS.

`eval/week6/judge_v2.txt` is v1 plus three changes:

- One new rule: the source card is the ground truth, not general cooking knowledge.
- Example 1: S05, previous verdict PASS, correct verdict FAIL, and why.
- Example 2: S19, same shape.

That is few-shot. The model is shown the exact mistake it just made, with the right verdict beside it.

Re-measured agreement: **27/27 (100%)**. S05 and S19 flip to FAIL. S08 and S14 stay PASS. The published quality number drops from **20/27 to 18/27**, because those two had been free passes. The ruler got stricter. The food got the same. The lower number is the result of fixing the judge.

Order, from the timestamps:

```text
labels   16:10:10Z    hand marks, no judge
judge v1 16:25:14Z    25/27 agree, S05 and S19 wrong
prediction           filed before v2 exists
judge v2 16:30:00Z    27/27 agree, product score 18/27
```

### Langfuse — where you would watch v1 and v2

Langfuse is an LLM observability app. It is not wired into this repo. The same audit is on disk.

In Langfuse, one judge call is a trace. You would store:

| What | Week 6 equivalent in this repo |
| --- | --- |
| Prompt name and version (`judge-v1`, `judge-v2`) | `eval/week6/judge_v1.txt`, `judge_v2.txt` |
| Model, latency, raw output | `judge_v1_results.json`, `judge_v2_results.json` |
| Human label as the score to compare | `labels_25.json` |
| Which rows disagree | `eval/week6/disagreements.md` |

The screen people mean by "fixed in Langfuse" is a side-by-side of two prompt versions on the same 27 inputs. v1's scores diverge from the human on S05 and S19. v2's scores match. This project prints that comparison from `python scripts/run_week6.py` instead of from a Langfuse dashboard.

### The score that looks perfect and is wrong

Faithfulness asks "did the substitution stick to the text it was given?" Context precision asks "was that text the right card?"

**S03.** Request: drop fish sauce from the tofu curry (R005). Retrieved text: the chicken curry (R004). The rewrite copies R004, including fish sauce and a 12-minute simmer.

| | S03 | average of the set |
| --- | --- | --- |
| Faithfulness | **1.0** | 0.273 |
| Context precision | **0.0** | 0.864 |

Ranked by faithfulness, S03 is the best row. It is grounded in the wrong recipe. Implemented in `src/ragas_lite.py`.

```bash
python scripts/run_week6.py
```

---

## Week 7 — agent

An agent here is a loop. Each lap the model looks at the request and at what the tools have already returned, and it chooses the next tool. That choice is the reasoning step. The tool then runs in Python. The result goes back into the conversation. The loop repeats until the model emits the recipe JSON, or a budget stops it.

A tool has one use case. The description says what it will not do, so the model cannot ask one tool to cover another.

| Tool | The one job | It will not |
| --- | --- | --- |
| `search_recipes` | Dish name → `recipe_id`, title, base servings, tags | Return ingredient rows |
| `scale_recipe` | Multiply quantities to the requested servings | Search, or swap an allergen |
| `get_allergen_profile` | **One** allergen per call: nuts, dairy, gluten, fish, shellfish, egg, or meat. Returns the card's swap, plus `introduces` / `leaves` when the substitute is itself an allergen | Search, scale, or clear two allergens in one call |

Code: `src/agent/tools.py` for the three jobs, `src/agent/loop.py` for `run_agent`. Model for the loop: `openai/gpt-oss-20b` (`WEEK7_MODEL`).

### What "reasoning" is in this loop

The model does not receive a script that says "call tool 2 now." Each lap it writes either a tool call or the final JSON.

Example, vegan and nut-free paneer (W07):

1. Reason: I need the card. Call `search_recipes`.
2. Reason: servings are not 4. Call `scale_recipe`.
3. Reason: vegan means clear dairy. Call `get_allergen_profile` with `dairy`.
4. The tool says the dairy swap still leaves cashews, or introduces nuts.
5. Reason: the user also asked nut-free, so one profile is not enough. Call `get_allergen_profile` again with `nuts`.
6. Apply every `card_swap` to the scaled list. Emit the JSON.

Step 5 exists only because step 4's result changed the plan. That dependence is the case for an agent.

Four budgets are checked at the start of every lap: max iterations, max tokens, max dollars, wall clock. Tokens are summed across laps, because the whole message list is sent again each time. W07 with `max_iters=2` stops with `stopped_by: max_iters` instead of spinning.

### The other system has no reasoning step

The workflow (`scripts/run_week7_workflow.py`) is fixed Python:

```text
parse the request → search_recipes → scale_recipe → at most one get_allergen_profile → JSON
```

It never reads `introduces` or `leaves`. The next step does not depend on the last tool result. Cost is $0 and latency is under a millisecond, because no model is choosing tools.

### Same 10 requests, both systems

| ids | Class | Does the next tool depend on the last result? |
| --- | --- | --- |
| W01–W04 | Scale only | No. Always search, then scale. |
| W05–W06 | One allergen | No. Always search, scale, one profile. |
| W07–W09 | Allergen cascade | Yes. The substitute carries another allergen. |
| W10 | Cannot adapt | Gluten-free pizza. The card forbids it. |

Cascades in the three:

- W07 vegan + nut-free paneer. Dairy swap leaves cashews.
- W08 vegan + gluten-free chicken curry. The soy swap introduces gluten.
- W09 vegan shakshuka. Dropping feta leaves the eggs.

### The race

| | Agent | Workflow |
| --- | ---: | ---: |
| Pass | **9/10** | 7/10 |
| Scale + one allergen (7 requests) | 7/7 | **7/7** |
| Cascade (3 requests) | **2/3** (W07, W09) | 0/3 |
| p50 latency | ~42 s | **<1 ms** |
| Tokens | 76 921 | **0** |
| Cost / request | ~$0.001 | **$0** |

W08 beat both. The agent stopped that cascade after four laps.

Use the workflow when the path is the same for every input of that class. Scale-only and single-allergen are that class. Use the agent when the next allergen enum depends on `introduces` / `leaves`. That is the only class in the ten that forces a loop. The agent is ahead on pass rate because of W07 and W09. The workflow is ahead on time, tokens, and cost.

```bash
python scripts/run_week7_agent.py --id W07
python scripts/run_week7_workflow.py --id W07
python scripts/run_week7_race.py
```

---

## How the two weeks sit on week 5

```text
week 5   read 20 traces by hand, group them, keep the prompt and model on the trace
week 6   freeze 27 swaps (two of them from those traces)
         hand-label PASS/FAIL
         judge v1 disagrees on S05 and S19
         judge v2 adds those two to the prompt
         agreement 25/27 → 27/27
         Langfuse would show that prompt diff and those scores; this repo stores the files
week 7   three tools, one use case each
         agent = the model reasons about which tool to call next
         workflow = the steps are already written
         cascade (introduces / leaves) is the case that needs the agent
```
