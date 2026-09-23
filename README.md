# Recipe RAG — chunking strategy comparison

A small RAG application over 6 recipe cards, built to **measure** retrieval
quality rather than just demonstrate it: two chunking strategies indexed over the
identical corpus, scored with Hit-in-Top-5 on a known-answer golden set, plus
metadata filtering, grounded answers with verified citations, and refusals.

- **Vector DB:** ChromaDB (persistent, cosine space)
- **Embeddings:** ChromaDB default `all-MiniLM-L6-v2` (ONNX, runs locally, free)
- **LLM:** Groq `llama-3.3-70b-versatile` (free tier) — used only for answer generation
- **UI:** Streamlit

Only the 6 cards in `data/recipes/` are ever indexed. Both collections are
dropped and rebuilt on every ingest, so the corpus is never extended.

## Run it

Everything runs in Docker; nothing is installed on the host.

```bash
cp .env.example .env    # then put your free Groq key in it
```

Full pipeline — ingest, evaluate, sweep, filter demo, answers, refusals, and
write `results.md`:

```bash
docker compose run --rm rag
```

Interactive UI on http://localhost:8501:

```bash
docker compose up ui
```

Individual steps:

```bash
docker compose run --rm rag python scripts/ingest.py
```

```bash
docker compose run --rm rag python scripts/run_eval.py
```

```bash
docker compose run --rm rag python scripts/demo_filter.py
```

Ad-hoc search:

```bash
docker compose run --rm rag python scripts/search.py "how much cream in the paneer curry?"
```

## Layout

| Path | What it is |
| --- | --- |
| `data/recipes/` | the 6 recipe cards (markdown, front matter + ingredient and nutrition tables) |
| `src/loader.py` | parses cards into titled sections, classifying each as table or prose |
| `src/chunking.py` | **strategy A** `chunk_basic`, **strategy B** `chunk_structured`, and the shared metadata builder |
| `src/store.py` | ChromaDB collections, `where` filtering, cosine scores |
| `src/evaluate.py` | Hit-in-Top-K and the stricter answer-present check |
| `src/generate.py` | Groq call with a citation-enforcing prompt, versioned and hashed for replay |
| `src/guardrails.py` | score threshold, refusal detection, citation verification |
| `src/tracing.py` | builds a trace record and appends it to `traces/traces.jsonl` |
| `eval/questions.py` | known-answer golden set (Q1–Q8 original, Q9+ extras) with gold recipe and section |
| `eval/unanswerable.py` | the 3 out-of-corpus questions |
| `eval/question_bank.py` | the wider bank used to collect traces: many phrasings, plus unanswerable and off-topic |
| `scripts/run_all.py` | regenerates `results.md` end to end |
| `scripts/run_week6.py` | one-command substitution eval: assertions, judge v1/v2, pass rate by mode |
| `eval/substitutions.py` | 27 mode-tagged substitution cases with frozen texts |
| `eval/week6/` | labels, judge prompts, prediction, agreement artefacts |
| `scripts/run_week7_race.py` | agent vs workflow race; writes `eval/week7/race.csv` |
| `src/agent/` | three tools, loop with four budgets, fixed workflow |
| `diff/strategy_b_and_metadata.diff` | the required code diff: strategy B + metadata fields |
| `results.md` | generated report |

## Error analysis (week 5)

Read **`WEEK5.md`** for what we did and how we fixed the hybrid gate. The assignment pages are `taxonomy.md` (ranked modes) and `notes.md` (20 sentences, replay, prediction).

```bash
python scripts/ingest.py
python scripts/collect_traces.py --n 120 --rpm 25
python scripts/read_traces.py
python scripts/week5_analysis.py
python scripts/replay_trace.py
```

## Evals (week 6)

Read **`WEEK6.md`** for the judge-validation protocol: blind labels, assertions vs one judged criterion, agreement before → after. Artefacts live in `eval/week6/`.

```bash
python scripts/run_week6.py
```

## Agents (week 7)

Read **`WEEK7.md`**. Race an agent loop against a three-step workflow on the same 10 adaptation requests.

```bash
python scripts/run_week7_agent.py --id W07
python scripts/run_week7_workflow.py --id W07
python scripts/run_week7_race.py
```

## Agents (week 8)

Read **`WEEK8.md`**. Score the path, not just the plate; attack the agent with a poisoned card; then close the top failure.

```bash
python scripts/run_week8.py --offline
python scripts/run_week8.py --phase trajectory
python scripts/run_week8.py --phase injection
python scripts/run_week8.py --phase after
```

## The two strategies

**A — basic.** Fixed-size character windows (default 500 chars, 80 overlap) over
the flattened card. Blind to headings, tables and row boundaries.

**B — structure-aware.** Splits on section boundaries. Table sections are split
into row groups that re-emit the recipe title, the section heading and the table
header row with every group, so an ingredient row is never orphaned. Prose is
packed into whole units — a numbered step or a paragraph is never cut in half.

The same ingredient row, under each strategy:

```
# Strategy B
Recipe: Paneer Butter Masala (R001) | Cuisine: Indian | Dietary: vegetarian, ... | Section: Ingredients
## Ingredients
| Ingredient | Quantity | Unit | Notes |
| --- | --- | --- | --- |
...
| Heavy cream | 60 | ml | stirred in at the end, off the heat |

# Strategy A
|
| Paneer | 400 | g | cut into 2 cm cubes |
...
| Heavy cream | 60 | ml | stirred in at the end, off the heat |
...
| Dried
```

The strategy A chunk has no header row, no section heading, no recipe title, and
ends mid-row. It contains the answer but nothing that ties it to the dish.

## Metadata

Every chunk in both collections carries `source_file`, `recipe_id`, `cuisine` and
`dietary_tags`, plus `chunk_id`, `recipe_title`, `section`, `sections_covered`,
`chunk_type` and `strategy`.

ChromaDB metadata values must be scalars, so `dietary_tags` is stored as a
display string *and* expanded into one boolean per tag (`tag_vegan`,
`tag_gluten_free`, …) so `where={"tag_vegan": True}` filtering works.

## Metrics

- **Hit-in-Top-5** (primary): a top-5 chunk from the correct recipe covering the
  correct section. Blind strategy-A windows straddle several sections and are
  credited for any they overlap — the generous reading, in A's favour.
- **Answer-in-Top-5** (secondary): the retrieved chunk from the correct recipe
  actually contains the answer text. A chunk can satisfy the primary metric while
  having had the answer row sliced off.
