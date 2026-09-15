# Week 5 Practical — Task Set B · Taxonomy

**Domain:** Recipes & food | **Date:** 2026-09-15 | **Sample:** 20 traces, seed=42

## Failure Mode Taxonomy

| Mode | Count | Freq % | Severity | Example trace_id |
|------|-------|--------|----------|-----------------|
| Citation cites wrong-recipe chunk — answer correct, provenance fabricated | 5 | 25% | Annoys the cook: the dish name in the citation is wrong, eroding trust even when the number is right | fc9c535e |
| Cross-recipe quantity swap — vegan curry paste returns chicken-curry quantity | 4 | 20% | Ruins the dish: 45 g instead of 50 g changes paste intensity; 200 g vs 250 g chickpeas changes texture and yield | be634b47 |
| Refusal gate fires on answerable question — correct chunk retrieved but model still refuses | 2 | 10% | Annoys the cook: user receives no answer when one exists | 22d78acc |
| Answer template corrupts non-quantity reply — procedure or timing answer wrapped in "you'll need ... approx" frame | 2 | 10% | Annoys the cook: grammatically broken output confuses meaning of correct information | 392630b1 |
| False positive on unanswerable question — model answers instead of refusing, topic unrelated to question | 2 | 10% | Ruins the dish / misleads: user receives confident wrong information and may act on it | 6ca4d1c2 |
| Citation chunk_id does not exist — answer correct but chunk_id in citation is not in the index | 1 | 5% | Annoys the cook: citation verification fails; citation is unfalsifiable | e105547b |

**Correct / refusal-correct / off-topic-correct traces:** 4 / 20 (20%)

---

## Notes

- **7 traces (35%)** show either a cross-recipe quantity swap or a citation pointing to the wrong recipe — both of these collapse into the same root: R004 and R005 ingredient tables are so similar that the retriever returns them interchangeably, and the generator does not notice the mismatch.
- **2 traces** (T10, T19) show refusals that are *correct* because the right chunk was absent from top-k — these are retrieval failures, not gate misfires; they are not counted in the taxonomy above.
- **2 correct refusals on off-topic** (T02, T07) and **1 correct refusal on unanswerable** (T14, T15) are counted as successes.
- Zero code changes were made during the coding step. This taxonomy was derived purely from reading the 20 traces.

## Prediction (filed 2026-09-15)

Chunking full ingredient tables as single atomic chunks will drop the cross-recipe-quantity + wrong-recipe-citation cluster from 7/20 (35%) to under 3/20 (15%) on the next seeded 20-trace draw (seed=43) after deployment.
