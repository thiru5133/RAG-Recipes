# Week 5 & Week 6 — speaking brief

What we did, how it performs, and the numbers to say out loud.

About **6–8 minutes** if you read the long version. Use the **90-second version** if they cut you short.

---

## Open (20 seconds)

We built a small RAG over six recipe cards — paneer butter masala, chana masala, pizza, two Thai curries, shakshuka. It retrieves, it answers with citations, it refuses when it shouldn’t guess.

Week 5 asked: **when it fails, what kind of failure is it?**
Week 6 asked: **if we put a quality score on substitutions, does that score mean anything?**

Those are different questions. We treated them that way.

---

## Week 5 — we read real traces, then we changed one thing

We did **not** invent traces. We ran real questions through the live pipeline, logged 386 traces, and drew a seeded sample of 20 with seed 42.

Then we open-coded: one sentence per trace of what was on the screen. No categories while reading. Categories came after.

**14 of 20 had a defect.** And here’s the surprise: **not one answered trace got a quantity wrong.** The food editor’s “it sometimes gets the numbers wrong” is not what these 20 show. They show answers that **never arrive**, or arrive **unverifiable**.

### Ranked failure table

| Mode | Count | What to say |
| --- | --- | --- |
| Hybrid search answers nothing | 6/20 (30%) | RRF scores around 0.03 were compared to a cosine gate of 0.30. Wrong scale. Model never called. |
| Citations the verifier cannot parse | 7/20 (35%) | Three shapes: full-width `【 】`, padded `[ id \| id ]`, header form `[chunk_id: X \| recipe_id: Y]`. Number was right. Regex only accepts `[id \| id]`. |
| Ingredient table missing from top-3 | 1/20 (5%) | Retrieval, not the gate. Left alone. |
| No defect | 6/20 (30%) | — |

We **replayed** one trace from the JSON alone. Prompts hashed to the recorded sha256. Output matched. So we weren’t reading a log we couldn’t reproduce.

Then — and this is the discipline — we **filed a numbered prediction in a commit before any fix**: gate hybrid on cosine, hybrid refusals go from 6/20 to 0/20, answerable refusals under 3/20.

One change: ranking is still RRF. The number the gate reads is cosine. Fresh log, new seed. **Both claims held. Zero hybrid gate refusals.**

A question like “how much chickpea cooking liquid should I reserve?” now returns cosine around 0.53 and the model says **250 ml**. Before the fix, hybrid never even called the model.

That’s Week 5: **find the top mode, predict a number, change one thing, check the number.**

### How Week 5 performs now

Hybrid is usable. Semantic and BM25 were already usable. The citation-shape bugs are **still there** — we didn’t polish the UI. We attacked the row that cost 30% of traces. Citations are next if we keep walking down the table.

| Commit | What |
| --- | --- |
| `2e82edf` (2026-09-18) | taxonomy, notes, **prediction, no fix** |
| Post-fix check | hybrid gate refusals 6/20 → 0/20 |

---

## Week 6 — we stopped trusting the judge’s number

New product: **recipe substitutions.** “Make this vegan.” “Nut-free.” “No amchur.” The team was about to publish on an LLM quality score. An allergy swap being wrong is not a rounding error.

So Week 6 is not “make a better generator.” It is: **prove the judge agrees with a human, or find out it doesn’t.**

### What we did, in the only order that counts

1. **27 cases**, each tagged with a Week-5 mode, plus two regressions replayed from real failed traces — the incomplete vegan paneer answer (T08), and the hybrid refusal on unfamiliar curry paste (T06).
2. **Five checks left the judge and became `if` statements:** method ingredients listed, allergen warning present, oven temp has units, servings echoed, quantities parse as numbers. **5 assertions, 1 judged criterion.** Paying a model to check whether “250 C” has a C is an expensive `if` with an off day.
3. **We labelled 27 substitutions blind — PASS or FAIL, not 1-to-10.** Saved the file. **Then** ran the judge.
4. Naive judge v1, then a one-sentence prediction, then v2 with the judge’s own disagreements as few-shots.

```
labels     16:10:10Z
judge v1   16:25:14Z
judge v2   16:30:00Z
```

If you reverse that order, you’re agreeing with yourself.

### Agreement

| | Number |
| --- | --- |
| Judge v1 vs human | **92.6% (25/27)** |
| Judge v2 vs human | **100% (27/27)** |

Two disagreements, same bug: **the model used general cooking knowledge instead of the card.**

**S05 — gluten-free pizza with rice flour.** Judge said pass. The card says this recipe **cannot** be made gluten-free without changing the dough entirely. Human was right. v2 flipped to fail.

**S19 — three-day sourdough starter for pizza yeast.** Judge said pass — “reasonable substitute.” The card has 3 g fresh yeast and a 24-hour fridge. No starter. Human was right. v2 flipped to fail.

Lemon-for-amchur and tempeh-for-tofu stayed pass — those swaps **are** on the card.

### How Week 6 performs — and why the score got worse

After we calibrated the judge, the **product pass rate dropped from 20/27 to 18/27 — 74% down to 67%.** Those two free passes were carrying the number. The ruler was too generous. **A worse score on a validated judge is more honest than a better score on a judge nobody checked.**

And one overall number still lies. After v2:

| Slice | Pass |
| --- | --- |
| Structural swaps | 5/5 (100%) |
| Flavour plausibility | 8/11 (~73%) |
| Allergen-safety | 5/9 (~56%) |
| Real regressions | 0/2 (0%) |
| **Overall** | **18/27 (67%)** |

Flavour carries the average. Allergen-safety is already worse. If we only reported 67%, you’d never see that.

### Bonus trap — faithfully, confidently wrong

A vegan fish-sauce swap for the **tofu** curry. Retrieval returned the **chicken** curry. The substitution copied it perfectly — fish sauce, 12-minute simmer.

| | S03 | Set average |
| --- | --- | --- |
| Faithfulness | **1.0** | 0.273 |
| Context precision | **0.0** | 0.864 |

If you rank by faithfulness, that’s the *best* substitution in the set. It’s also grounded in the wrong recipe. Faithfulness never asks “was this the right card?”

---

## Close (the one sentence they should remember)

Week 5: we found hybrid was measuring fusion scores against a cosine gate, predicted the fix, and the prediction held.

Week 6: we found the quality judge was grading cookbook common sense, not our cards. We moved agreement from 93% to 100%, and the published pass rate **fell**, which is how you know we moved the thing being measured, not the ruler.

---

## 90-second version

We have a recipe RAG. Week 5 we sampled 20 real traces. 30% of them were hybrid search refusing because RRF scores around 0.03 were compared to a cosine threshold of 0.30. We predicted that gating on cosine would take that from 6/20 to 0/20, changed only that, and it held. Quantities were never the bug — unverifiable citations and silent refusals were.

Week 6 we validated the substitution judge. Five mechanical checks became assertions. One binary criterion stayed with the model. 27 blind labels before the judge ran. Agreement 93% to 100% after two few-shots. Both disagreements: the judge passed swaps the **card forbids or doesn’t contain** — rice-flour pizza, invented sourdough. Product pass rate dropped 74% to 67% because those two had been inflating it. Allergen-safety is 56% while flavour is 73%, so the average still hides the slice that matters.

---

## If they ask

**“Did you just overfit the judge to two examples?”**
We checked the card-specified swaps didn’t flip. Lemon for amchur and tempeh for tofu stayed pass. We also did not relabel the disagreements.

**“Why not a 1–10 score?”**
A model cannot tell a 6 from a 7, and neither can we. Within-1 agreement inflates the number into meaninglessness.

**“Is the system ready to publish substitutions?”**
No. Allergen-safety is 5/9. The two regressions still fail. The judge now agrees with us; the product does not yet pass the slices that matter.

**“What did you not fix?”**
Citation bracket shapes (Week 5, 7/20). Ingredient table missing from top-3 (1/20). Those were lower on the ranked table. We attacked the top mode, then we validated the judge.

---

## Numbers cheat-sheet

| Claim | Number |
| --- | --- |
| Traces logged | 386 |
| Sample read | 20 (seed 42) |
| Defects in sample | 14/20 |
| Hybrid gate refusals before | 6/20 (30%) |
| Hybrid gate refusals after | 0/20 |
| Unparseable citations | 7/20 (35%) |
| Eval cases (Week 6) | 27 |
| Assertions vs judged criteria | 5 vs 1 |
| Agreement before → after | 92.6% → 100% |
| Product pass rate before → after | 20/27 (74%) → 18/27 (67%) |
| Allergen-safety (v2) | 5/9 (56%) |
| Flavour (v2) | 8/11 (73%) |
| S03 faithfulness / context precision | 1.0 / 0.0 |

Run it:

```bash
python scripts/run_week6.py
```

Longer write-ups: `WEEK5.md`, `WEEK6.md`. Assignment pages: `taxonomy.md`, `notes.md`, `eval/week6/`.
