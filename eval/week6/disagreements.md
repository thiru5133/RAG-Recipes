# Two disagreements — who was right

Blind labels vs judge v1, then the same two cases after v2. Labels were not edited.

## S05 — gluten-free margherita (rice flour 1:1)

- Human: FAIL. The pizza card says the recipe "cannot be made gluten-free without changing the dough entirely."
- Judge v1: PASS. Reason: "replaces all wheat flour with rice flour, eliminating gluten while keeping the rest of the recipe intact."
- **Human was right.** The judge scored general GF baking knowledge, not this card. A rice-flour dough is a different bread; it is not a substitution the corpus supports.
- Judge v2: FAIL (flipped).

## S19 — sourdough starter for pizza yeast

- Human: FAIL. The card lists 3 g fresh yeast (or 1 g instant) and a 24-hour fridge. It has no starter and no levain schedule.
- Judge v1: PASS. Reason: "a 100 g 100% hydration sourdough starter with adjusted water and longer fermentation reasonably replaces the small amount of yeast."
- **Human was right.** "Reasonably" is cookbook common sense. The criterion is whether *this* card supports the swap.
- Judge v2: FAIL (flipped).

## Prediction scored against the outcome

Filed in `prediction.txt` before `judge_v2.txt` was written:

> Few-shotting S05 and S19 as FAIL examples will stop the judge treating general cooking knowledge as a pass when the source card forbids or simply does not contain the swap; I expect both disagreements to flip to FAIL and I do not expect card-specified swaps (S08 lemon-for-amchur, S14 tempeh) to flip with them.

What held: S05 and S19 both flipped FAIL. S08 and S14 stayed PASS.

Where it was wrong: it treated this as a judge-only story. After v2 the published product pass rate drops from **20/27 to 18/27**, because those two cases had been carrying the number on a ruler that was too generous. The prediction never said the quality score would get worse once the judge agreed with the labels — and that drop is the reason you validate a judge before you ship on its number.
