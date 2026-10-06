# Week 5 — what we did and how we fixed it

This is the reading map for the error-analysis week. The assignment artefacts stay as they were written:

| File | What it is |
| --- | --- |
| `taxonomy.md` | one-screen ranked failure table (counts, %, severity, example `trace_id`) |
| `notes.md` | the 20 observation sentences, seeds, replay pair, dated prediction, bonus demo sample |
| `WEEK5.md` | this recap: pipeline, what we found, what we changed |

Live trace JSON is **not** in git. It is produced on your machine and listed in `.gitignore`. How to rebuild it is below.

## The system we analysed

Six recipe cards in `data/recipes/` are chunked two ways (basic windows vs structure-aware), stored in Chroma, and answered by Groq `openai/gpt-oss-120b` through two gates: a score threshold (`0.30`) and a prompt that must refuse when the context has no answer. Citations must look like `[chunk_id | recipe_id]`.

Search modes: **semantic** (cosine), **bm25**, **hybrid** (RRF fusion of the two).

## What we actually did, in order

1. **Log real traces**, not invented ones. `src/tracing.py` appends one JSON line per question from the UI and from `scripts/collect_traces.py`. Each line stores the question, prompt version, model + params, retrieved **chunk text** (not just ids), scores, and `raw_output`.
2. **Drew a seeded sample of 20** with `random.Random(42)` over 386 live traces (`scripts/sampling.py`). Seed and ids are in `notes.md`.
3. **Open-coded those 20 by hand** — one sentence per trace of what was on the screen, no fixes while reading. `scripts/read_traces.py` is the reader.
4. **Clustered into 5 named modes** in `taxonomy.md`. The largest was hybrid search: fused RRF scores sit near `0.03`, the gate compares them to cosine `0.30`, and the model is never called. That was 6/20 (30%).
5. **Proved replay.** Trace `bf0e4580` was picked with seed `11` from the 20. Prompts rebuilt from the trace hashed to the recorded sha256; original and replayed output matched. Evidence: `notes.md` section 4.
6. **Filed a dated, numbered prediction in commit `2e82edf`**, before any behaviour change: gate hybrid on cosine instead of RRF, and hybrid score-gate refusals go from 6/20 to 0/20; answerable refusals from 7/20 to under 3/20.
7. **Made that one change** in `retrieve._rrf_fuse` / `guardrails.gate_value`. Ranking is still RRF. `score` / `gate_score` is cosine. Then collected a **new** log and ran `scripts/verify_prediction.py` (seed 43): both claims **held** (0 hybrid gate refusals, 1 answerable refusal).

We threw away the synthetic generator (`generate_traces.py`). It had baked the failure names into the code, so “reading” it only recovered its own weights.

## What was broken, and what we used to fix it

### 1. Hybrid answers nothing (the mode we attacked)

**Seen.** Every hybrid trace in the 20 refused at `score_threshold`. Top chunks were the right recipe sections, but scores were `0.016–0.033`.

**Cause.** Reciprocal Rank Fusion writes `1/(60 + rank)` into `score`. The refusal gate in `guardrails.below_threshold` was calibrated on cosine similarity (`REFUSAL_THRESHOLD = 0.30` in `src/config.py`). Those two numbers are not on the same scale, so hybrid can never clear the gate.

**Fix.** In `src/retrieve.py`, `_rrf_fuse` still **ranks** by RRF (`rrf_score`). It copies the semantic list’s cosine onto each hit as `score` / `gate_score`. `guardrails.gate_value` is what the 0.30 check reads.

**Check.** After the change, a hybrid question such as “How much chickpea cooking liquid should I reserve?” returns cosine `~0.53` (clears 0.30) and the model answers `250 ml`. Seed-43 on the post-fix log: hybrid gate refusals `0/20`.

### 2. Citations the verifier cannot parse (not fixed this week)

Three shapes showed up, 7/20 together: full-width `【 】`, spaces inside `[ R003-A00 | R003 ]`, and the context-header form `[chunk_id: X | recipe_id: Y]`. The number in the answer was right; `CITATION_RE` in `src/generate.py` only accepts ASCII `[id | id]`. Next week’s job if we keep going down the table.

### 3. Ingredient table missing from top-3 (1/20)

Semantic k=3 on “how many grams of paneer” retrieved method/nutrition/notes and the model refused. Retrieval, not the gate-scale bug. Left alone.

## Scripts you will actually run

```bash
cp .env.example .env          # paste a Groq key; never commit .env
python scripts/ingest.py      # rebuild the Chroma index locally
python scripts/collect_traces.py --n 120 --rpm 25
python scripts/read_traces.py
python scripts/week5_analysis.py
python scripts/replay_trace.py
python scripts/verify_prediction.py --traces traces/traces_after_hybrid_gate.jsonl
```

Traces land in `traces/*.jsonl` and stay on disk only. The argument we made from them is in `taxonomy.md` and `notes.md`.

## Commits to remember

| Commit | When | What |
| --- | --- | --- |
| `2e82edf` | 2026-09-18 | taxonomy, notes, real traces, **prediction, no fix** |
| `25b6f37` | 2026-09-20 | deleted the synthetic generator; **hybrid cosine gate**; post-fix check held |
