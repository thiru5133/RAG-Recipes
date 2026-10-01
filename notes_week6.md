# Week 6 — Evals notes

Track B (Recipes & food) · branch `week6-evals` · judge: the substitution judge.

## Prediction (written 2026-10-01, before any LLM eval was run)

**Change under test:** system prompt `v1.2.0` → `v1.3.0` (`src/generate.py`). The only
edit is rule 5. v1.2.0 says "two or three sentences at most"; v1.3.0 keeps that for
ordinary questions but lets a substitution answer state every swap the context
lists, up to six sentences, and forbids adding swaps not in the context.

**Why I expect it to help:** week-5 trace T08 ("what can I use instead of paneer to
make it vegan") named tofu and stopped, leaving out the oil and coconut-cream swaps
sitting in the same chunk. The brevity cap is the only thing in the prompt that
pushes toward stopping early.

**What I expect, same retrieval config (structured / semantic / k=3), same 12
substitution cases, same judge:**

- Substitution judge score goes **up**, from roughly 7/12 to at least 9/12. The gain
  should come from the multi-fact cases (S1, S3, S5, S9) that need several swaps.
- The two refuse-trap cases (S11, S12) stay passing. If they start failing, the
  "never add a swap the context does not list" clause did not hold.
- Answerable-question assertions (6 cases) and refusal assertions (4 cases) do not get
  worse. This is the regression guard: a prompt change that helps substitutions
  must not cost anything elsewhere.

**The prediction is wrong if** the substitution score does not rise by at least 2
cases, or either trap case flips to FAIL, or answer/refusal assertions lose a case.
