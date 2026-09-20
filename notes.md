# Week 5 — Notes

Recipes & food · error analysis run 2026-09-18

## 1. Where the traces came from

`traces/traces.jsonl` is written by `scripts/collect_traces.py` and by the Streamlit UI. Each line is a real question that went through real retrieval over the ChromaDB index and, unless a gate stopped it first, a real call to `openai/gpt-oss-120b`. The `raw_output` field is whatever the model said, unedited.

- records in file: **424**
- excluded, because the API call itself failed: **38** (RateLimitError ×32, AuthenticationError ×3, APIConnectionError ×3) — these hold no model output to read
- population sampled from: **386** traces
- distinct question phrasings: **104**, each paired with a config drawn from 2 chunking strategies × 3 search modes × k ∈ {3, 5}
- collection seed: `20260916` (`scripts/collect_traces.py`)
- file sha256 when sampled: `c983e80032e5fc00bc2ad684e12179e40bbca4e721c1161a0f853983d23b664d`

A seed only reproduces a sample against the same file, so the hash pins the file state. `scripts/sampling.py:population_fingerprint()` reprints it.

The 32 rate-limited records are the Groq free tier's 200,000 tokens per day running out mid-run. That capped the population at 386 rather than the thousand-plus lines the brief pictures; the sample is still drawn at random from all of it.

## 2. The seeded random sample

**Seed: `42`**, drawn as `random.Random(42).sample(population, 20)` in `scripts/sampling.py`. No sorting, no filtering by outcome, no hand-picking. The only records held back are the 38 failed API calls counted above.

| # | trace_id | search | k | question |
| --- | --- | --- | --- | --- |
| T01 | `7370504c-ab45-4269-bb4a-e95171d49477` | semantic/structured | 3 | What wine should I serve with the shakshuka? |
| T02 | `a110140c-27b1-4704-be28-87887cd76726` | semantic/structured | 5 | How many calories per serving does the shakshuka have? |
| T03 | `e4efb2fa-b8c1-439b-803c-a164de0185c4` | hybrid/structured | 3 | How much chickpea cooking liquid should I reserve? |
| T04 | `8d3a3a6a-30d4-4e89-ae93-5e7b20f88d65` | hybrid/basic | 5 | butter masala simmering time after adding water |
| T05 | `ccb74140-ee6e-4bdb-a5f6-048fab9b8c99` | semantic/structured | 3 | how many grams of paneer do I need for butter masala |
| T06 | `fdceede3-57db-4b22-b1f2-76b5e03d9a8f` | hybrid/basic | 5 | I have an unfamiliar brand of curry paste, how much should I start with? |
| T07 | `ac25b5bd-e810-47a3-97cb-4a72bca842c6` | semantic/basic | 5 | How long are the shakshuka eggs cooked after covering the pan? |
| T08 | `d04bc002-0f49-40a1-a96c-f031cab89303` | semantic/structured | 3 | What can I use instead of paneer to make the butter masala vegan? |
| T09 | `2338da4d-0d8b-4886-b222-845f42c84871` | hybrid/basic | 3 | How many calories per serving? |
| T10 | `9c9db0d4-15ea-4295-8a25-63d1224b1b7d` | semantic/basic | 3 | How much water goes in the pizza dough? |
| T11 | `6a8e7a17-55b2-4da3-bc76-954ebc70e36e` | bm25/structured | 5 | How long is the tofu pressed for the vegan green curry? |
| T12 | `760b9e64-cd6d-4462-831d-99448239308d` | hybrid/basic | 5 | How much paneer is in the butter masala? |
| T13 | `f051e419-ab7b-4652-8b7e-61043f8c652d` | bm25/basic | 5 | What kitchen scale should I buy? |
| T14 | `fdcb0d08-516f-4075-8fbd-12e3607ef778` | bm25/structured | 5 | How much fish sauce does the chicken green curry use? |
| T15 | `bf0e4580-f15c-40ba-b2d6-def5f3c8ce44` | bm25/basic | 3 | If I use chicken breast instead of thigh, how long do I simmer it? |
| T16 | `a2ee7a80-b331-4ed6-90db-7b6cde4766a3` | semantic/basic | 5 | sourdough starter schedule for this pizza |
| T17 | `a0425747-ef71-44f9-bfe5-91f7d06b0d87` | semantic/structured | 3 | How many grams of green curry paste are in the vegan green curry? |
| T18 | `59947af2-f029-4070-9c74-bbed429786f2` | semantic/basic | 3 | how much dried chana for chana masala |
| T19 | `1197eca6-08de-44d6-95f4-c85ea38120dd` | hybrid/basic | 3 | butter masala simmering time after adding water |
| T20 | `b87a58ef-61ac-44e5-b0a2-70dd91a5c8dc` | semantic/basic | 3 | What wine should I serve with the shakshuka? |

## 3. Open coding — 20 sentences, one per trace

One pass, written while reading with `scripts/read_traces.py`, before any mode existed. No code changed during the pass: the last edit to `src/` before it added `finish_reason` to the logger, and the first behaviour change lands after the prediction commit in section 5. Each sentence describes what was on the screen for one trace — no categories, no causes, no fixes; those come in the taxonomy, built afterwards from these sentences.

**T01 · `7370504c`** — Asked which wine to serve with the shakshuka; the three chunks returned were R006's method, ingredient and nutrition sections at 0.55 to 0.59, none of them mentioning a drink, and the reply was the fixed refusal sentence.

**T02 · `a110140c`** — The reply reads "The Shakshuka provides 298 kcal per serving【R006-B06 | R006】", which is the figure on R006's nutrition table, and the brackets around the citation are the full-width pair, with the trace's citation list empty and `citation_check.valid` false.

**T03 · `e4efb2fa`** — Asked how much chickpea cooking liquid to reserve; the top chunk was the R002 method chunk that contains "250 ml", it scored 0.0325, and the reply was the fixed refusal sentence recorded as `score_threshold` with no model call made.

**T04 · `8d3a3a6a`** — Asked for the butter masala simmering time; five chunks came back scoring 0.0164 to 0.0323 including R001's method chunk, the reply was the fixed refusal sentence recorded as `score_threshold`, and `model_params` is null because no call happened.

**T05 · `ccb74140`** — Asked how many grams of paneer; the three chunks returned were R001's method, nutrition and notes sections at 0.74 to 0.78, the ingredients table was not among them, and the model replied with the fixed refusal sentence.

**T06 · `fdceede3`** — Asked how much of an unfamiliar paste brand to start with; R004's notes chunk, the one carrying the 30 g advice, was ranked first at 0.0323 and the reply was the fixed refusal sentence recorded as `score_threshold`.

**T07 · `ac25b5bd`** — The reply gives 6 to 8 minutes with the detail about the whites being set and the yolks still moving, cites `[R006-A03 | R006]` in plain square brackets, and the citation check passed.

**T08 · `d04bc002`** — The reply names extra-firm tofu of the same weight pressed for 30 minutes and stops there, leaving out the oil-for-butter and coconut-cream swaps written in the same chunk, and its citation 【R001-B05 | R001】 uses full-width brackets.

**T09 · `2338da4d`** — Asked for calories per serving without naming a dish; three nutrition and notes chunks from three different recipes came back at 0.0164 to 0.0323 and the reply was the fixed refusal sentence recorded as `score_threshold`.

**T10 · `9c9db0d4`** — The reply reads "The dough uses 325 ml of water [ R003-A00 | R003 ]"; 325 ml is the figure on the card, R003-A00 does contain the water row, and each bracket carries a space inside it, with no citation recorded on the trace.

**T11 · `6a8e7a17`** — The reply gives 30 minutes and writes its citation as `[chunk_id: R005-B01 | recipe_id: R005]`, the same shape as the header line in the context block, and the trace recorded no citation.

**T12 · `760b9e64`** — Asked how much paneer; all five chunks were R001's, scoring 0.0308 to 0.0328 with the ingredients table at rank 2, and the reply was the fixed refusal sentence recorded as `score_threshold`.

**T13 · `f051e419`** — Asked which kitchen scale to buy; BM25 returned three recipe chunks scoring 2.55 to 2.96 and two more scoring exactly 0.0000, and the model replied with the fixed refusal sentence.

**T14 · `fdcb0d08`** — The reply gives 2 tablespoons of fish sauce, which matches R004's ingredient table, and cites `[ R004-B01 | R004 ]` with a space inside each bracket; no citation was recorded on the trace.

**T15 · `bf0e4580`** — The reply says to simmer breast for only 7 minutes to avoid drying it out and cites `[R004-A04 | R004]`, which is the notes chunk that says exactly that; the citation check passed.

**T16 · `a2ee7a80`** — Asked for a sourdough starter schedule; five R003 and R006 chunks came back at 0.32 to 0.59, none of them mentioning a starter, and the reply was the fixed refusal sentence.

**T17 · `a0425747`** — The reply reads "The recipe calls for \*\*50 g of green curry paste\*\*【R005-B01 | R005】", with markdown asterisks around the quantity and full-width brackets around the citation, and no citation was recorded on the trace.

**T18 · `59947af2`** — The reply gives 200 g of dried chickpeas and cites `[ R002‑A00 | R002 ]`, where the brackets are padded with spaces and the hyphen inside the chunk id is a non-ASCII character rather than a plain one; no citation was recorded.

**T19 · `1197eca6`** — The same butter masala simmering question as an earlier trace but with three chunks instead of five; R001's method chunk sat at rank 2 with 0.0323 and the reply was the fixed refusal sentence recorded as `score_threshold`.

**T20 · `b87a58ef`** — Asked which wine to serve with the shakshuka; the three chunks returned were R004's and R001's at 0.27 to 0.32 with no shakshuka chunk at all, and the reply was the fixed refusal sentence.

### What the sample looked like once the sentences were written

Nine of the 20 produced an answer and eleven were refused. All nine answers carried the number printed on the card. Of the eleven refusals, four were correct — three unanswerable or off-topic questions and one off-corpus — and seven refused a question the corpus answers.

## 4. Replay evidence

Trace picked by `random.Random(11).choice(sample)` — a seeded draw from the 20, not a trace chosen for looking good: **`bf0e4580-f15c-40ba-b2d6-def5f3c8ce44`**.

- question: *If I use chicken breast instead of thigh, how long do I simmer it?*
- config from the trace: `basic` / `bm25`, k=3, threshold 0.30, top_score 10.5241
- model from the trace: `openai/gpt-oss-120b`, `{"temperature": 0, "max_tokens": 400}`, prompt `v1.2.0`

Rebuilt from the trace alone, with nothing supplied by hand (`python scripts/replay_trace.py`):

| Check | Result |
| --- | --- |
| system prompt rebuilt from `prompt_version` via the registry, sha256 matches the recorded one | **True** |
| user prompt rebuilt from the stored chunk text, sha256 matches the recorded one | **True** |
| refusal gate re-run from `top_score` and `threshold`, same verdict as the trace | **True** |
| fields needed for replay that were missing | **none** |

**Original output**

> Use chicken breast instead of thigh and simmer it for only 7 minutes to avoid drying it out. [R004-A04 | R004]

**Replayed output** — same two prompts re-sent to the same model at temperature 0

> Use chicken breast instead of thigh and simmer it for only 7 minutes to avoid drying it out. [R004-A04 | R004]

**Identical: True.** Evidence written to `results/replay_evidence.json`.

### The field I had to add

The first log recorded which chunks were retrieved but not what they said, so the prompt could not be rebuilt. Those 20 traces were missing `retrieved_chunks[].text`, `system_prompt_sha256`, `user_prompt_sha256`, `threshold`, and `top_score`. `src/tracing.py` now stores each chunk's text alongside its id and score, plus the sha256 of both prompts actually sent and the threshold the gate used. Those hashes are what make the byte-for-byte match above checkable instead of merely asserted.

### What I could not reconstruct

- **`finish_reason` and `usage` were absent from this trace.** An earlier replay returned an empty answer where the original was cut off mid-sentence, and without `finish_reason` a trace cannot say whether the model stopped on its own or ran into the 400-token ceiling. Both fields are now recorded, so traces from here on can answer it; the 386 already written cannot.
- **Gate-refused traces have no generation step to reproduce.** They never reach the model, so they carry no `model_params` and no prompt hashes. Their gate decision replays exactly, and that is all there is to replay.
- **Identical output is not guaranteed in general**, even at temperature 0. This trace matched; one earlier replay of a different trace did not.

## 5. Prediction, filed 2026-09-18

**Mode attacked next:** *Hybrid search answers nothing: fused scores land near 0.03 and the 0.30 gate refuses before the model is called* — 6/20, 30%, the largest single row.

**The change.** Stop comparing three different score scales against one number. The 0.30 threshold in `guardrails.below_threshold` was calibrated on cosine similarity, but `retrieve._rrf_fuse` hands it Reciprocal Rank Fusion scores whose ceiling is 1/(60+1) = 0.0164 per list, so in hybrid mode the gate can never be cleared. The change is to carry the top hit's cosine similarity through fusion and gate on that, leaving the 0.30 value itself untouched.

**Exact numbers expected.** Traces refused at the score gate in hybrid mode drop from **6/20 (30%) to 0/20**, and refusals of answerable questions across all modes drop from **7/20 (35%) to under 3/20 (15%)**.

**Measured on.** 20 traces drawn with `random.Random(43).sample(...)` from traces collected after the change, same question bank and same config grid as this run. `python scripts/verify_prediction.py` prints both counts.

**The prediction is wrong if** any hybrid-mode trace in that draw is still refused by `score_threshold`, or 3 or more answerable questions in the draw are refused by either gate.

**Committed as `2e82edf` on 2026-09-18**, before any fix — `git show 2e82edf` contains this prediction and no change to retrieval, the refusal gate or the citation extractor. `git log --oneline` shows the fix landing after it, never before.

## 6. Why a public benchmark would have missed these

A public benchmark scores the answer string, and in this sample the answer strings were right — every one of the nine answered traces carried the number printed on the card — so a leaderboard would have reported near-perfect accuracy on exactly the traces that failed here. It would not have caught the top mode at all, because a benchmark harness calls the retriever in one fixed configuration, and this failure exists only in hybrid mode, where a fusion score is measured against a cosine threshold belonging to a different scale. It would not have caught the citation modes either, because those are defects in a bracket shape that only our own verifier reads, and no public benchmark checks whether the provenance a product prints can be parsed by the tool that is supposed to check it.

## 7. Bonus — the demo set we show at reviews

**Seed: `4242`**, 10 traces drawn from the 8 review questions in `eval/questions.py` — the Q1–Q8 written up in `results.md` and demoed every week, matched to their phrasings in the question bank — and disjoint from the random 20.

**D01 · `b7446b8c`** (R003-preheat, hybrid/basic, k=5) — The review question about the oven and stone: five R003 chunks came back with the two method chunks that carry 250 C at the top, all scoring 0.0299 to 0.0325, and the reply was the fixed refusal sentence.

**D02 · `bcbc2761`** (R003-kcal, semantic/structured, k=3) — The reply gives 892 kcal per serving and cites 【R003-B06 | R003】 in full-width brackets; R003-B06 is the nutrition chunk and no citation was recorded.

**D03 · `e28b0f08`** (R002-chickpeas, hybrid/structured, k=5) — Asked how much dried chana; five R002 chunks came back scoring 0.0310 to 0.0318 and the reply was the fixed refusal sentence recorded as `score_threshold`.

**D04 · `df915db5`** (R003-kcal, semantic/basic, k=3) — The reply gives 892 kcal citing 【R003-A05 | R003】; that window does contain the 892 row, the brackets are full-width, and no citation was recorded.

**D05 · `8808f714`** (R003-preheat, hybrid/structured, k=5) — Asked how hot to get the stone and for how long; R003's two method chunks ranked first and second at 0.0328 and 0.0320 and the reply was the fixed refusal sentence.

**D06 · `eaf2e670`** (R003-kcal, semantic/basic, k=5) — The same calories question as the k=3 run with the same top three chunks plus two more; the reply is worded "contains 892 kcal per serving" instead of "provides", again with full-width brackets and no recorded citation.

**D07 · `a6cc04ae`** (AMB-paste, hybrid/structured, k=3) — Asked how much curry paste without naming a dish; the vegan ingredients chunk ranked first at 0.0325 and the chicken one third at 0.0315, and the reply was the fixed refusal sentence.

**D08 · `3edb4cd3`** (R002-chickpeas, bm25/structured, k=3) — The reply gives 200 g of dried chickpeas and cites `[ R002-B01 | R002 ]` with padded brackets; R002-B01 holds the 200 g row and no citation was recorded.

**D09 · `156fbe2a`** (R005-paste, bm25/basic, k=5) — The reply gives 50 g of green curry paste in markdown bold with a 【R005-A01 | R005】 citation; BM25 scored the top chunk 10.81 and no citation was recorded.

**D10 · `1585ae45`** (R006-sauce-simmer, hybrid/structured, k=3) — The review question about the shakshuka sauce simmer; R006's method chunk ranked first at 0.0325 and the reply was the fixed refusal sentence.

### Top mode: random sample versus demo set

> **6/20 (30%)** in the random sample · **5/10 (50%)** in the demo set

Same mode, same system, 30% against 50%. And where the random 20 held 6 clean traces (30%), the demo 10 held **zero**: every one of the ten showed either the hybrid refusal or an unparseable citation.

### What we have been telling ourselves

What the team has been telling itself for the last month is written down in `results.md`: Hit-in-Top-5 of 8/8 on the chunking strategy we shipped, decision justified, decision closed. That number is true, and it is measured on retrieval alone — it stops before the refusal gate and before the citation verifier, which is exactly where all ten demo traces fail. Nobody was lying and nobody was lazy: the demo questions are the eight we tuned chunking against, they retrieve beautifully, and the metric we chose to celebrate ends at the moment retrieval succeeds. So we have been reviewing a component and reporting it as a product. Worse, the demo set is not flattering us by accident — it is *worse* than production, because on stage we reach for hybrid search, which in these 386 traces has never once cleared the refusal gate. The 8/8 was never wrong. It was just never an answer to the question the food editor was asking.
