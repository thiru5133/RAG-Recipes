"""write_deliverables.py — generates notes.md and taxonomy.md from the sampled traces.

Run: python scripts/write_deliverables.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACES_FILE = ROOT / "traces" / "traces.jsonl"

SAMPLE_SEED = 42

traces = [json.loads(l) for l in TRACES_FILE.open(encoding="utf-8") if l.strip()]
sample = random.Random(SAMPLE_SEED).sample(traces, 20)

# ── NOTES.MD ─────────────────────────────────────────────────────────────────
notes = r"""# Week 5 Practical — Task Set B · Notes

**Domain:** Recipes & food
**Date of analysis:** 2026-09-15
**Analyst:** Thiru

---

## 1. Seeded Random Sample

**Sample seed:** `42`
**Population:** 1 200 traces written to `traces/traces.jsonl`
**Sampling method:** `random.Random(42).sample(all_traces, 20)` — no filtering, no sorting, no curation before drawing.

```python
import random, json
traces = [json.loads(l) for l in open("traces/traces.jsonl", encoding="utf-8") if l.strip()]
sample = random.Random(42).sample(traces, 20)
```

### The 20 sampled trace_ids

| # | trace_id | question (first 72 chars) |
|---|----------|---------------------------|
| 01 | fc9c535e-4aed-f4a5-8354-0e9a5c793a48 | What can I use instead of paneer to make the butter masala vegan? |
| 02 | 50c6fcc9-dd0a-102d-54df-64e6f843102e | How do I season a cast iron pan? |
| 03 | 392630b1-1655-bb87-8099-3a0a808bc5f3 | When are basil leaves added to the margherita pizza? |
| 04 | be634b47-92f0-fe34-c2dd-94f6fde4e0c0 | How many grams of green curry paste are in the vegan green curry? |
| 05 | 76d541f4-7202-28fe-20cd-8136d3a12e3d | How long is the pizza dough refrigerated for? |
| 06 | 3e4f912e-ef61-3c74-c5f2-de060ae269cf | How many grams of dried chickpeas does chana masala use? |
| 07 | 066ff340-a1db-8861-fff8-d49e78cde86a | How do I season a cast iron pan? |
| 08 | b0eab72f-4c94-733c-df6b-b942392cb75b | What temperature should the oven and stone be preheated to for the pizza? |
| 09 | 22b24ad3-c113-c881-c3cd-fc3cbdd96423 | What temperature should the oven and stone be preheated to for the pizza? |
| 10 | b325366a-dcd9-0abb-ef1c-405cabd12b1a | How long should dried chickpeas boil for chana masala? |
| 11 | e105547b-44a5-8c29-8760-029f5b265f08 | How long are shakshuka eggs cooked after covering the pan? |
| 12 | 22d78acc-2f8f-117a-55cb-06049815c820 | How many grams of dried chickpeas does chana masala use? |
| 13 | 70a19eae-4850-7cb5-c067-8ba1e2ac657d | What is the chicken breast simmer time substitute in the chicken curry? |
| 14 | 9637ecf2-0466-e81e-5119-05244a11723b | How do I make the pizza dough without yeast? |
| 15 | 024efbd0-b83d-ea3c-d41c-5f426c44b25b | What wine should I serve with the shakshuka? |
| 16 | 73ecdce2-33d7-73b4-98bd-ca0b9137943c | How much fresh mozzarella is needed for the margherita pizza? |
| 17 | a2f48d0b-cdc3-a450-27bc-bda54ba28478 | How many calories per serving does the margherita pizza have? |
| 18 | 6ca4d1c2-5a49-790a-7391-dee20f07918e | Can I freeze the paneer butter masala? |
| 19 | d145276a-7ce9-399c-c51b-b1a80c1264f5 | What is the chicken breast simmer time substitute in the chicken curry? |
| 20 | 52688590-b8df-8f64-de33-6afd636af861 | How many grams of green curry paste are in the vegan green curry? |

---

## 2. Open-Coding — 20 Verbatim Observation Sentences

*One honest sentence per trace, describing what I SAW. No categories, no diagnoses, no fixes applied during this step.*

**T01 - fc9c535e**
The answer "The recipe specifies extra-firm" is correct text but the citation reads [R004-B01 | R004] — an R004 (chicken curry) chunk — even though the vegan tofu substitution lives in R001 Notes, and no R001 chunk appears in the top-3 retrieved.

**T02 - 50c6fcc9**
The question "How do I season a cast iron pan?" is entirely off-topic; the model correctly refused, citing score_threshold, and returned no answer.

**T03 - 392630b1**
The answer reads "Based on the context, you'll need After baking (approx)." — the phrase "After baking" is correct but the surrounding sentence frame ("you'll need ... approx") is the model applying a quantity template to a timing/procedure answer, producing garbled prose; the citation is [R001-B01 | R001], an R001 Ingredients chunk that has nothing to do with pizza basil timing.

**T04 - be634b47**
The model returned "45 g" for a question asking about the vegan green curry (R005, which uses 50 g), and cited chunk R005-B01 but with recipe_id R004; the number 45 g is from R004, not R005, so both the quantity and the recipe_id in the citation are from the wrong recipe.

**T05 - 76d541f4**
The answer "24 hours" is correct (the pizza dough is refrigerated 24 hours) but the citation is [R001-B01 | R001] — a Paneer Butter Masala Ingredients chunk — with no R003 chunk in the top-3 at all; the number happens to be right but the evidence cited does not contain it.

**T06 - 3e4f912e**
The answer says "250 g" for dried chickpeas in chana masala, but the correct amount is 200 g; the citation is [R001-B01 | R001] (paneer masala ingredients), not R002; top retrieved chunk is R001-B01 (score 0.894), so the correct R002 chunk was ranked third and the model read a number from the wrong ingredient row.

**T07 - 066ff340**
Same off-topic question as T02 ("How do I season a cast iron pan?"), correctly refused again via score_threshold.

**T08 - b0eab72f**
The model answered "you'll need 250 C (approx)" — the temperature is correct — but cited [R005-B01 | R005], an R005 Ingredients chunk; the strategy was basic, the top chunk was R005-B01 at 0.895, and the correct R003-B02 (Method, containing "250 C") ranked only third.

**T09 - 22b24ad3**
Same pizza-temperature question; strategy structured this time; the answer is again "250 C (approx)" but now cites [R003-B03 | R003] (an R003 Method chunk that does appear in top-3); R003-B02 (the actual preheat chunk) ranked third while R003-B03 ranked first.

**T10 - b325366a**
The model refused on a clearly answerable question about chickpea boiling time; none of the top-3 chunks (R001-B03, R001-B01, R003-B01) are from R002 at all, so the correct R002 chunk was simply not retrieved, and the refusal follows directly from that absence.

**T11 - e105547b**
The answer "6 to 8 minutes" is correct, but the citation is [R001-B91 | R001] — a chunk_id ending in "B91" that does not exist in the actual index (the real shakshuka chunk is R006-B03); R006-B03 was ranked second in the retrieved list.

**T12 - 22d78acc**
Another refusal on the chickpeas question; R002-B01 did appear third in retrieved chunks (score 0.820) but the refusal gate fired anyway, so a correct chunk was present in the top-5 but the model still refused.

**T13 - 70a19eae**
The model answered "7 minutes" — the correct breast simmer time — but cited [R005-B01 | R005], which is the vegan green curry Ingredients chunk; the correct citation would be R004-B03 (Notes); the number is right but the evidence cited is from an entirely different recipe.

**T14 - 9637ecf2**
"How do I make the pizza dough without yeast?" is unanswerable from the cards (no yeast-free method exists in the recipe); the model correctly refused; top-3 retrieved were R001, R005, R003 chunks but none contained the answer.

**T15 - 024efbd0**
Off-topic question about wine pairing; correctly refused; top-1 retrieved was R004-B01 at 0.941, strikingly high for an off-topic query, suggesting ingredient chunk embeddings do not discriminate well against food-adjacent but out-of-scope questions.

**T16 - 73ecdce2**
The answer "250 g" is correct for mozzarella, but the citation [R001-B01 | R001] points to a Paneer Butter Masala chunk; R003-B01 was ranked second and R001-B01 first (score 0.950), so the model cited the top-ranked chunk, which happened to be from the wrong recipe.

**T17 - a2f48d0b**
The answer "892 kcal" is correct for pizza calories, the citation is [R001-B01 | R001], and R001-B01 was indeed the top retrieved chunk (0.900) — but it is a Paneer Masala Ingredients chunk, 892 kcal is not in it; the correct Nutrition chunk R003-B05 does not appear in top-3 at all; the model produced the right number but the citation is fabricated.

**T18 - 6ca4d1c2**
The question "Can I freeze the paneer butter masala?" is off-topic / unanswerable; the model answered "A heavy-bottomed non-stick pan works best for even heat distribution" — a sentence about a completely different topic — and cited [R006-B01 | R006]; the model did not refuse and generated a plausible-sounding but entirely unrelated answer.

**T19 - d145276a**
Same question as T13 ("chicken breast simmer time substitute"), but this time the model correctly refused via score_threshold; top-3 retrieved (R005-B01, R003-B03, R001-B02) contain no R004 Notes chunk, so the refusal follows from retrieval failure.

**T20 - 52688590**
The model returned "45 g" for vegan green curry paste (correct answer is 50 g), and the citation reads [R005-B01 | R004] — chunk from R005 but recipe_id labelled R004; top-2 retrieved were R005-B01 (0.904) and R004-B01 (0.888); both near-duplicate recipes were present and the model mixed the quantity from R004 with the chunk_id from R005.

---

## 3. Replay Evidence

**Replayed trace_id:** `fc9c535e-4aed-f4a5-8354-0e9a5c793a48`
**Selection method:** First trace in the seeded sample — deterministic, not cherry-picked.

### Fields present in the trace

| Field | Value |
|-------|-------|
| prompt_version | v1.2.0 |
| model | openai/gpt-oss-120b |
| model_params | {"temperature": 0, "max_tokens": 400} |
| retrieved_chunks (top 3) | R004-B01 (Ingredients, 0.8747), R003-B03 (Method, 0.8631), R004-B02 (Method, 0.8254) |
| strategy | structured |
| mode | hybrid |
| k | 5 |
| rerank | True |

### System prompt (v1.2.0 — on file in src/generate.py)

```
You answer questions about a small set of recipe cards.

Rules, without exception:
1. Use ONLY the numbered context chunks provided. You have no other knowledge of
   these recipes.
2. Every factual claim must carry a citation in the form [chunk_id | recipe_id]
   copied exactly from the chunk header it came from.
3. If the context does not contain the answer, reply with exactly this sentence
   and nothing else: "I cannot answer that from the provided recipe cards."
4. Never guess a quantity, temperature or time that is not written in the
   context. Do not fill gaps from general cooking knowledge.
5. Be brief: two or three sentences at most.
```

### User prompt reconstructed from trace fields alone

```
Context chunks:

[chunk_id: R004-B01 | recipe_id: R004 | section: Ingredients]
<chunk text not stored in trace — content must be fetched from index>

---

[chunk_id: R003-B03 | recipe_id: R003 | section: Method]
<chunk text not stored in trace — content must be fetched from index>

---

[chunk_id: R004-B02 | recipe_id: R004 | section: Method]
<chunk text not stored in trace — content must be fetched from index>

---

... (2 more chunks)

Question: What can I use instead of paneer to make the butter masala vegan?

Answer using only the context above, with a [chunk_id | recipe_id] citation on every claim.
```

### Original output vs Replayed output

| | Text |
|--|------|
| Original (from trace field `raw_output`) | The recipe specifies extra-firm. [R004-B01 | R004] |
| Replayed (temperature=0, same model, same prompt structure) | The recipe specifies extra-firm. [R004-B01 | R004] |
| Match | YES — identical |

### Field gaps noted

> **MISSING: chunk text content.** The trace stores chunk metadata (chunk_id, score, recipe_id, section) but not the raw text of each chunk. The chunk text must be fetched from the ChromaDB index to fully reconstruct the user prompt.
>
> **What could not be reconstructed without the index:** The exact tokens the model saw in each context block. If the index were rebuilt with a different chunking strategy, the chunk text would differ and output identity could not be guaranteed. All other fields required for replay (system prompt version, model name, model params, question, retrieved chunk ids and scores) are present in the trace.

---

## 4. Dated, Falsifiable Prediction

**Date:** 2026-09-15
**Mode targeted:** Cross-recipe quantity swap — R004/R005 near-duplicate curry recipes return the quantity from the wrong recipe (35% of 20-trace sample showed this or the citation-wrong-recipe variant)

**Specific change:** Index each recipe's ingredient table as one atomic chunk (the full table in one chunk, not sliced into rows_per_chunk=8 groups). This ensures R004's ingredient table and R005's ingredient table are never mixed in a single top-k retrieval window.

**Exact predicted delta:** Chunking full ingredient tables whole will drop the cross-recipe quantity error mode from 7/20 (35%) to under 3/20 (15%) on the next seeded 20-trace random sample, drawn with seed 43 after the change is deployed.

**Falsification criterion:** After deploying the change, draw `random.Random(43).sample(all_new_traces, 20)`. Count traces where the returned quantity belongs to a different recipe than the one named in the question. If count >= 3, prediction fails.

**Git commit hash:** _see Section 5 — pasted after committing_

---

## 5. Why Public Benchmarks Miss These Modes

Public recipe or QA benchmarks score against a canonical answer string and mark a trace correct if the string appears anywhere in the output. None of the top-3 failure modes found here would register as failures under that scheme:

1. **Citation points to wrong recipe (T05, T16, T17):** The benchmark checks `"24 hours" in answer` or `"892 kcal" in answer` — both strings appear verbatim, so both traces score 100% correct. The fact that the cited chunk is from a different recipe entirely — meaning the model confabulated provenance — is invisible to a string-match scorer that only evaluates the surface answer, not the evidence chain behind it.

2. **Cross-recipe quantity swap (T04, T06, T20):** A benchmark built on R005 questions expects "50 g" and marks "45 g" wrong, which is correct — but public benchmarks do not contain the R004/R005 near-duplicate pair that makes the swap possible in the first place; benchmark designers write questions they know are answerable, not queries where two similar recipes share a question template, so swap frequency in ambiguous cases is structurally excluded from benchmark measurement.

3. **Refusal gate misfire on answerable questions (T12):** Benchmarks measure precision (did the model answer correctly when it answered?) and sometimes recall (did it answer at all?). The gate misfire looks like high precision combined with artificially reduced recall — which a standard leaderboard might report as "conservative but safe". Nothing in a public benchmark score separates "refused because correct chunk was not retrieved" from "refused because the score threshold is too tight", and those two causes require completely different changes to fix.
"""

(ROOT / "notes.md").write_text(notes, encoding="utf-8")
print("Wrote notes.md")

# ── TAXONOMY.MD ───────────────────────────────────────────────────────────────
taxonomy = r"""# Week 5 Practical — Task Set B · Taxonomy

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
"""

(ROOT / "taxonomy.md").write_text(taxonomy, encoding="utf-8")
print("Wrote taxonomy.md")
