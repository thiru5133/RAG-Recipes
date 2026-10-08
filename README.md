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
| `api.py` | one HTTP API over weeks 1-10 (`uvicorn api:app`) |
| `src/mcp_lite/`, `src/mcp_servers/`, `third_party/ingredient_db/` | week 9: MCP protocol, recipe server, ingredient server |
| `src/gateway/` | week 9 bonus: audit and scoped-token gateway |
| `src/multi/` | week 10: orchestrator and workers |
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

That command also uploads judge v1 and v2 to Langfuse when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set in `.env`. Blank keys leave the eval local.

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

## Agents (week 9)

Read **`WEEK9.md`**. The agent gets its tools from MCP servers listed in `config/mcp_servers.json`; the ingredient server was added with a config edit and zero agent changes.

```bash
python scripts/run_week9_agent.py "How many kcal in 100 g of paneer?"
python scripts/week9_evidence.py
python scripts/week9_capture_wire.py
python scripts/week9_gateway_demo.py
```

## Agents (week 10)

Single MCP agent vs a kitchen squad (planner, substitution worker, allergen worker, synthesis) on the same 10 cases, plus a failure-injection run.

```bash
python scripts/run_week10_race.py
python scripts/run_week10_race.py --only failure
python scripts/week10_report.py
```

## Run the API (all weeks)

One FastAPI app exposes every part of the project. Run it locally (not in Docker):

```bash
python -m venv .venv                 # first time only
.venv\Scripts\activate               # Windows. macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # first time only; put GROQ_API_KEY in .env
python scripts/ingest.py             # first time only; builds the Chroma index for /rag/ask
uvicorn api:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs (Swagger UI) to try every endpoint.

| Endpoint | Covers | Model call |
| --- | --- | --- |
| `GET /health` | key and index status | no |
| `POST /rag/ask` | weeks 1-5: retrieval + guarded answer | yes |
| `POST /agent/ask` | weeks 7-8: three-tool agent, optional guards and injection test | yes |
| `GET /eval/week8` | week 8: saved baseline / after / injection results | no |
| `GET /mcp/tools` | week 9: tools discovered across MCP servers | no |
| `POST /mcp/ask` | week 9: MCP agent, `direct` or `gateway` config | yes |
| `POST /squad/ask` | week 10: planner + workers + synthesis | yes |

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/mcp/ask -H "Content-Type: application/json" \
  -d '{"question": "How many kcal in 100 g of paneer?"}'
```

Keep real keys in `.env` only, never in `.env.example`.

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