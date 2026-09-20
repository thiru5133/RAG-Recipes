# Week 6 — what we did and why

This week is not "make a better substitution generator." It is: **prove the LLM judge that prints the quality number actually agrees with a human**, then move that agreement with evidence.

The assignment pages stay as they were written:

| File | What it is |
| --- | --- |
| `eval/week6/labels_25.json` | 27 blind PASS/FAIL labels. `labeled_at` is **2026-09-20T16:10:10Z**. No judge verdicts in this file. |
| `eval/week6/judge_v1.txt` | naive binary judge, no examples |
| `eval/week6/judge_v2.txt` | same judge + the two v1 disagreements as few-shots |
| `eval/week6/prediction.txt` | one-sentence prediction, written after v1 and **before** v2 |
| `eval/week6/disagreements.md` | who was right on S05 and S19, and where the prediction was wrong |
| `WEEK6.md` | this recap |

Live judge calls are cached in `eval/week6/judge_v1_results.json` and `judge_v2_results.json`. Frozen substitution texts are in `eval/substitutions.py` / `eval/week6/substitutions.json`. Changing those texts without relabelling is refused (sha256 pin).

## The product being judged

A substitution is a rewritten recipe under one constraint (vegan, nut-free, no amchur, chicken breast instead of thigh, …). The food team was about to publish on a single LLM quality score. An allergy swap being wrong is not a rounding error.

## What we actually did, in order

1. **Froze 27 substitutions** tagged with one Week-5 taxonomy mode each. Two are regression fixtures replayed from real traces in `notes.md`: T08 `d04bc002` (incomplete vegan paneer, full-width citation) and T06 `fdceede3` (hybrid gate refusal on unfamiliar curry paste). The other 25 are structured rewrites against the six cards.
2. **Moved five criteria out of the judge and into `src/assertions.py`**: method ingredients listed, allergen-warning string present when a tracked allergen is in the name column, oven temperature carries units, SERVINGS echoed, quantities parse as numbers. The judge prompt is forbidden from scoring those. Count: **5 assertions, 1 judged criterion**.
3. **Hand-labelled all 27 blind** on the one binary criterion (*does this honour the constraint without a new hazard, and without contradicting a swap the card already specifies?*). Saved `labels_25.json` **before** any judge call. Binary PASS/FAIL, not a 1–10 with a ±1 fudge.
4. **Ran judge v1**, a naive "is this a reasonable honouring?" prompt. Agreement **92.6% (25/27)**. Two disagreements, both the same shape: human FAIL, judge PASS.
5. **Filed `prediction.txt`**, then built v2 from those two disagreements as few-shots, then re-measured. Agreement **100% (27/27)**.

```
labels  16:10:10Z
judge v1 16:25:14Z
judge v2 16:30:00Z
```

## Why assertions vs judge

Paying a model to check whether `"250 C"` has a unit, or whether `"cashews"` appears in a warning string, is how you get an expensive `if` with an off day. Code does that. The model is left with the one question `if` cannot answer: is this swap *the right swap for this constraint on this card*.

That split is also why pass rate is **assertions AND judge**, not judge alone. S24 still stirs heavy cream into a "vegan" method — the assertion catches the missing ingredient row; the judge catches that it is not vegan. S20 (the T08 regression) fails the assertions because it is unstructured tofu-only prose, and the judge fails it for being an incomplete vegan swap.

## Why pass rate is sliced

One overall number hides the slice that matters. On judge v1:

| Week-5 mode | pass |
| --- | --- |
| citation_header | 3/3 (100%) |
| no_defect | 5/6 (83%) |
| hybrid_search_gate | 5/6 (83%) |
| citation_fullwidth | 3/4 (75%) |
| citation_padded | 3/4 (75%) |
| ingredient_table_miss | 1/4 (25%) |
| **OVERALL** | **20/27 (74%)** |

| slice | pass |
| --- | --- |
| structural_swap | 5/5 (100%) |
| flavour_plausibility | 9/11 (82%) |
| allergen_safety | 6/9 (67%) |
| retrieval_regression | 0/2 (0%) |

Flavour and "no defect" carry the 74%. Allergen-safety is already worse; the two regressions are 0/2. After v2 the overall product pass rate is **18/27**, because S05 and S19 stop getting a free pass.

## The two disagreements

**S05** rice-flour pizza. Card: cannot be made gluten-free without changing the dough entirely. v1 passed it as a clean GF swap. Human fail. Human was right.

**S19** 3-day sourdough starter. Card: 3 g fresh yeast, 24-hour fridge. v1 passed it as a reasonable yeast substitute. Human fail. Human was right.

Both are the same judge bug: **general cooking knowledge beating the source card.**

v2 adds those two as few-shots. Both flip to FAIL. Card-specified swaps (S08 lemon for amchur, S14 tempeh for tofu) stay PASS — the prediction held there.

Where the prediction was wrong: it never said the *published quality number* would drop. Calibrating the ruler made the score worse. That is the point of this week.

## Bonus — faithfully wrong

RAGAS-shaped faithfulness (claims supported by retrieved context) and context precision (retrieved chunks from the gold recipe), implemented in `src/ragas_lite.py` without the RAGAS package.

**S03** is the trap. Request: vegan fish-sauce substitute for the *tofu* curry (R005). Retrieved context: the *chicken* curry (R004). The substitution faithfully copies R004, fish sauce and 12-minute simmer included.

| | S03 | set average |
| --- | --- | --- |
| faithfulness | **1.0** | 0.273 |
| context precision | **0.0** | 0.864 |

If you rank by faithfulness, S03 is the best substitution in the set. It is also the one grounded in the wrong recipe. Faithfulness never asks "was this the right card?"; it only asks "did you stick to whatever you were given?" The average does not warn you — the peak score *is* the failure.

## Scripts you will actually run

```bash
python scripts/run_week6.py
```

One command. Prints pass rate by Week-5 mode, pass rate by allergen/flavour slice, `agreement_before` / `agreement_after`, assertion count vs judged-criteria count, and the faithfully-wrong case.

The judge will not run if `labels_25.json` is missing. That is the protocol, encoded.

```bash
python scripts/run_week6.py --judge none          # assertions + RAGAS only
python scripts/run_week6.py --judge v1 --force    # re-call the model
```

Do not `--regenerate` the frozen texts while labels exist. The sha256 pin will refuse to score them.

## Commits to remember

| When | What |
| --- | --- |
| labels file `labeled_at` 16:10:10Z | 27 human labels, no judge verdicts |
| judge v1 `judged_at` 16:25:14Z | naive judge, 92.6% agreement |
| `prediction.txt` then `judge_v2.txt` | prediction filed before the few-shot prompt existed |
| judge v2 `judged_at` 16:30:00Z | 100% agreement; product pass rate 20/27 → 18/27 |
