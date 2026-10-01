# Week 5 Guide — Error Analysis, explained from zero

This guide assumes you know nothing about RAG. Read it top to bottom once, then
use Part 6 to run everything.

---

## Part 1 — What is RAG? (the 2-minute version)

A language model (like ChatGPT) only knows what it learned in training. It does
not know *your* documents. If you ask it "how much cream is in my paneer
recipe?", it will guess — and guessing is how you get wrong quantities.

**RAG = Retrieval-Augmented Generation.** Instead of letting the model guess, we:

1. **Retrieve** — search our own documents for the few passages most likely to
   contain the answer.
2. **Augment** — paste those passages into the prompt.
3. **Generate** — tell the model: "answer using ONLY these passages, and say
   which passage you used."

Think of it as an open-book exam. The search step picks the pages; the model
reads them and writes the answer.

### The pieces in this project

| Word | Meaning | Where in this repo |
|---|---|---|
| **Corpus** | The documents we search: 6 recipe cards | `data/recipes/` |
| **Chunk** | A small piece of a document (a few table rows, a few steps). We search chunks, not whole files | `src/chunking.py` |
| **Embedding** | A list of numbers that represents the *meaning* of a text. Similar meanings → similar numbers | ChromaDB's built-in MiniLM model |
| **Vector database** | Stores chunks + embeddings and finds the closest ones to a question | ChromaDB, `src/store.py` |
| **Semantic search** | Find chunks whose *meaning* is close to the question | `mode = semantic` |
| **BM25** | Classic keyword search (matches words) | `mode = bm25`, `src/bm25_search.py` |
| **Hybrid search** | Combine semantic + BM25 rankings (using "RRF") | `mode = hybrid` |
| **Rerank** | Re-sort the top results with extra signals | `src/rerank.py` |
| **Top-K / k** | How many chunks we hand to the model (3 or 5) | `k` setting |
| **Cosine similarity** | Score 0–1 for how close a chunk is to the question. 1 = identical meaning | `score` field |
| **Refusal gate** | If the best chunk scores below 0.30, don't even ask the model; say "I cannot answer" | `src/guardrails.py` |
| **Citation** | The model must tag claims like `[R001-B02 \| R001]` (chunk id \| recipe id) so we can verify the source | `src/generate.py` |
| **LLM** | The language model that writes the answer: Groq `gpt-oss-120b` | `src/generate.py` |

### The flow of one question

```
Question
  → search the vector DB (semantic / bm25 / hybrid)  → top-k chunks
  → refusal gate: best score < 0.30?  → YES: refuse, stop
  → send chunks + question to the LLM
  → LLM answers with [chunk_id | recipe_id] citations
  → verifier checks the citations are real
  → save everything as a TRACE
```

---

## Part 2 — What was Week 5 asking for?

Source: `task.md` (Week 5 · Module 3 · "Error Analysis — Reading Traces Like a
Professional"). Our track is **B — Recipes & food**.

**The problem they describe:** until now you fixed whatever bugs you happened to
notice. That misses the ones you didn't notice. This week you become
*systematic*.

**The deliverable:** read about **20 real traces**, write an honest note on each,
group the notes into named problems, **rank** them, pick **one** to fix next,
and write down **what you expect to happen before you fix it**.

### Vocabulary from the task

| Term | Plain meaning |
|---|---|
| **Trace** | A full record of ONE request: the question, the chunks retrieved, the prompt sent, the model's answer, scores, settings. Complete enough to replay later |
| **Random sampling** | Pick traces by a random draw, not the nice-looking ones. Otherwise you only see what already works |
| **Seed** | A number that makes the "random" draw repeatable (we used 42) |
| **Open coding** | Read each trace and write ONE honest sentence about what happened, *before* inventing categories. Categories come afterwards from the sentences |
| **Taxonomy** | The list of named failure types, with counts |
| **Frequency × severity** | Rank by how often it happens AND how badly it hurts |
| **Prediction** | Before changing code, write what number you expect to change, to what. Then check. This stops you from fooling yourself |
| **Benchmarks (MMLU, HumanEval)** | Public tests for models. They don't tell you how *your app* fails — that is why we read our own traces |

### How the mentor checks (Friday, no marks)

1. Did you read a **fair random sample**, not just good examples?
2. Is there an **honest note per failure, written before grouping**?
3. Do the groups have **clear names a stranger would understand**?
4. Are they **ranked, with a chosen target to fix next**?

---

## Part 3 — What we did, step by step

### Step 0 — Build the app first (Weeks 1–4)
The RAG app already existed: ingest recipes, two chunking strategies, three search
modes, rerank, refusal gate, citations. Week 5 does not build the app — it
*analyses* it.

### Step 1 — Make traces complete
`src/tracing.py` writes one JSON line per question to `traces/traces.jsonl`.
We found our first traces were not replayable (they didn't store chunk text or
prompt hashes), so we added: chunk text, SHA-256 of both prompts, threshold,
top score, `finish_reason`, token usage.

### Step 2 — Collect lots of real traces
`scripts/collect_traces.py` pushes a bank of question phrasings
(`eval/question_bank.py`) through the real pipeline with random settings
(2 chunking strategies × 3 search modes × k of 3 or 5).
Result: 424 records; 38 were API errors (Groq free-tier rate limit) and were
excluded; **386 usable traces**.

### Step 3 — Take a fair random sample
`scripts/sampling.py` draws 20 traces with `random.Random(42)`. It also stores
the file's hash so the same seed reproduces the same 20 only if the file is
unchanged. No hand-picking.

### Step 4 — Read and write one sentence each (open coding)
`scripts/read_traces.py` prints the 20 traces. We wrote one factual sentence per
trace in `notes.md` §3 (T01–T20), with no categories yet.

### Step 5 — Group into named failure modes → taxonomy
`taxonomy.md` is the result. Of 20 traces, 14 had a defect:

| Rank | Failure mode (plain English) | Count |
|---|---|---|
| 1 | **Hybrid search refuses everything**: hybrid scores are ~0.03 but the gate wants ≥ 0.30, so the app refuses before the model is even called | 6 (30%) |
| 2 | Citation in full-width brackets `【 】` — verifier can't read it | 3 |
| 3 | Citation with spaces `[ R003-A00 \| R003 ]` — verifier can't read it | 3 |
| 4 | Citation copied in header form `[chunk_id: X \| recipe_id: Y]` | 1 |
| 5 | Refuses a plain quantity because the Ingredients chunk wasn't in the top 3 | 1 |
| – | No defect | 6 |

The three citation rows together are 7/20 (35%). Key insight: **not one answer
had a wrong quantity.** The real problems were "answer never arrives" and
"answer can't be verified", not "answer is wrong".

*Why #1 happens:* hybrid mode ranks with RRF, which produces tiny numbers
(max ≈ 0.016 per list). The gate compares against 0.30, a number calibrated for
cosine similarity. Different scales → the gate can never pass.

### Step 6 — Replay one trace
`scripts/replay_trace.py` rebuilds the prompts from a trace's own record,
re-sends them, and checks the output matches. It matched exactly (evidence in
`notes.md` §4). This proves the traces are "complete enough to replay".

### Step 7 — Write the prediction BEFORE fixing
`notes.md` §5, committed as `2e82edf` before any code change:
"Hybrid refusals by the score gate go from 6/20 (30%) to 0/20, and wrongly
refused answerable questions go from 7/20 (35%) to under 3/20." It also states
what would prove the prediction **wrong**.

### Step 8 — Make the fix
`src/retrieve.py::_rrf_fuse` still *ranks* with RRF, but now reports the
chunk's **cosine** as its score, so the 0.30 gate sees the scale it was built for.

### Step 9 — Why public benchmarks wouldn't catch this
`notes.md` §6: benchmarks grade answer text in one fixed config; our top failure
only exists in hybrid mode and in our own citation parser.

### Bonus — Demo set vs random sample
`notes.md` §7: the 8 questions we always demo showed the top failure at 50%
versus 30% in the random sample. Lesson: curated examples flatter you.

---

## Part 4 — Files to know

| File | Purpose |
|---|---|
| `task.md` (on Desktop) | The assignment |
| `taxonomy.md` | **Main deliverable**: ranked failure table |
| `notes.md` | The 20 sentences, seeds, replay evidence, prediction |
| `src/tracing.py` | Writes traces |
| `src/guardrails.py` | Refusal gate + citation check |
| `src/retrieve.py` | Search modes and the hybrid fix |
| `scripts/collect_traces.py` | Generates traces from the question bank |
| `scripts/read_traces.py` | Prints the 20 sampled traces |
| `scripts/week5_analysis.py` | Re-counts every number in taxonomy.md |
| `scripts/replay_trace.py` | Replays one trace |
| `scripts/verify_prediction.py` | Checks the prediction on a fresh draw |
| `app.py`, `pages/inspection.py` | Streamlit UI and debug view |

---

## Part 4b — Status of YOUR machine (checked 2026-10-01)

| Check | Result |
|---|---|
| Docker | **Not installed** → use the plain-Python route (Option B) |
| Python | 3.9.6 in `.venv` (works) |
| `.env` with `GROQ_API_KEY` | Set |
| ChromaDB index | Built: 38 basic + 42 structured chunks |
| Live answer test (semantic) | Works: "60 ml of heavy cream … `[R001-B01 \| R001]`", citation valid |
| Live answer test (hybrid) | Works: answers instead of refusing, so the Week 5 hybrid fix is confirmed |
| Hybrid citation check | Was `valid: False` (model wrote `[ R001-B01 \| R001 ]` with spaces). **Fixed**: `extract_citations` in `src/generate.py` now accepts padded spaces, `【 】`, non-ASCII hyphens and the `chunk_id:` header form; live re-test returns `valid: True` |
| `traces/traces.jsonl` | Only **3 traces**, all from the UI and all errors ("GROQ_API_KEY is not set", made before the key was added). They are not usable for analysis |
| `python scripts/week5_analysis.py` | **Fails** with "Sample larger than population" because 3 traces < 20 |

What this means: the app runs. To redo the Week 5 analysis on your machine you
must first collect real traces (Part 6, "Reproduce the Week 5 analysis", step 1).
The numbers in `taxonomy.md` come from the original 386 traces, which are not
on this machine.

---

## Part 5 — Setup (once)

1. Get a **free Groq API key** at https://console.groq.com (sign up → API Keys).
2. In the project folder:
   ```bash
   cd ~/Desktop/RAG-Recipes
   cp .env.example .env
   ```
3. Open `.env` and set `GROQ_API_KEY=your_key_here` (never commit this file; it
   is already gitignored).

Free-tier note: Groq limits tokens per day. If you see `RateLimitError`, wait or
use `--rpm` lower / `--n` smaller.

---

## Part 6 — How to run and test

### Option A — Docker (recommended; nothing installed on your Mac)

Install Docker Desktop first. Then from `RAG-Recipes/`:

```bash
# 1. Index the recipes into ChromaDB (do this first)
docker compose run --rm rag python scripts/ingest.py

# 2. Try one question from the command line
docker compose run --rm rag python scripts/search.py "how much cream in the paneer curry?"

# 3. Open the web UI at http://localhost:8501
docker compose up ui
```

### Option B — Plain Python (no Docker) — what you are using

First time only:
```bash
cd ~/Desktop/RAG-Recipes
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export CHROMA_DIR=./.chroma
python scripts/ingest.py
```

Every new terminal session (the venv and variable do not persist):
```bash
cd ~/Desktop/RAG-Recipes
source .venv/bin/activate
export CHROMA_DIR=./.chroma
streamlit run app.py          # UI at http://localhost:8501
```
The first ingest downloads the small embedding model, so allow a minute.
Restart Streamlit after editing `.env`, otherwise it keeps the old key.

### Using the UI
1. Sidebar: choose **strategy** (structured/basic), **search mode**
   (semantic/bm25/hybrid), **Top-K**, **Rerank**, and the refusal threshold.
2. Type a question, e.g. `How much heavy cream does the paneer butter masala need?`
3. Look at the retrieved chunks table (scores, sections).
4. Click **Generate grounded answer**. You see the answer, or "Refused (gate: …)",
   plus the citation check. Every click also appends a trace.
5. The **Inspection** page (sidebar of the app) shows
   Question → Chunks → Answer → Failure label side by side.

**Try this to see failure #1 yourself:** ask "How much paneer is in the butter
masala?" with mode = `semantic`, then again with mode = `hybrid`. Before the fix
hybrid refused; after the fix it should answer.

### Reproduce the Week 5 analysis

Run in this order (needs the Groq key for step 1 and 5):

```bash
# 1. Collect traces (--rpm keeps you under the rate limit)
python scripts/collect_traces.py --n 120 --rpm 25

# 2. Read the seeded random sample of 20 — this is what you write sentences about
python scripts/read_traces.py

# 3. Recount every figure in taxonomy.md
python scripts/week5_analysis.py

# 4. Replay one trace from its own record
python scripts/replay_trace.py

# 5. Collect fresh traces AFTER the fix, then check the prediction
python scripts/collect_traces.py --n 40 --rpm 25 --out traces/traces_after_hybrid_gate.jsonl
python scripts/verify_prediction.py --traces traces/traces_after_hybrid_gate.jsonl
```
In Docker, prefix each with `docker compose run --rm rag `.

**Important:** traces are written fresh on your machine, so your numbers will
differ from `taxonomy.md`. The counts in taxonomy.md came from the 386 original
traces, which are not stored in the repo.

### The retrieval evaluation (Weeks 3–4 part)
```bash
docker compose run --rm rag python scripts/run_eval.py   # Hit-in-Top-5 for both strategies
docker compose run --rm rag                               # full pipeline, rewrites results.md
```

### How to know it's working
- `ingest.py` prints chunk counts (basic ≈ 38, structured ≈ 42).
- `search.py` prints chunks with scores around 0.5–0.8 for good matches.
- A good UI answer has a citation like `[R001-B02 | R001]` and the caption says
  `valid: True`.
- A refusal says `Refused (gate: score_threshold)` (best chunk too far) or
  `prompt_guard` (model said it can't answer).
- `traces/traces.jsonl` gains one line per answer.

### Common problems
| Symptom | Fix |
|---|---|
| "No indexed documents found" | Run `ingest.py` first |
| "GROQ_API_KEY is not set" | Put the key in `.env` |
| `RateLimitError` | Daily free quota used; wait, or lower `--n` |
| Port 8501 busy | `docker compose down` then retry |

---

## Part 7 — How to explain this in the review (cheat sheet)

1. **"What is a trace?"** One full record of a request: question, retrieved
   chunks, exact prompt, answer, scores, settings. Enough to replay.
2. **"How did you pick traces?"** Seeded random draw of 20 from 386 — no
   cherry-picking; the seed and file hash make it reproducible.
3. **"What did you find?"** 14 of 20 had a defect. The top one: hybrid search was
   refused by the score gate (30%) because of a score-scale mismatch. Citations
   unreadable by our verifier were 35% combined. No wrong quantities.
4. **"What did you pick to fix and why?"** The hybrid gate mismatch: biggest
   single row, one clear root cause.
5. **"What did you predict?"** 6/20 → 0/20 hybrid refusals, filed in a commit
   before the fix.
6. **"Why not just use a benchmark?"** Benchmarks grade answer text in one fixed
   setup; our failures were in a specific mode and in our own citation parser.

## Part 8 — Known gaps (be honest about these)

- The 386 original traces are gitignored, so the 20 sampled ones can't be opened
  from the repo, and your local `traces/traces.jsonl` has only 3 failed UI traces.
- The prediction's outcome has not been recorded yet: run Part 6 step 5 and add
  the result to `notes.md`. A live check today agrees with it (hybrid answered
  instead of refusing), but that is one question, not the 20-trace test.
- Citation formats (`【 】`, padded spaces, header form, non-ASCII hyphen) were
  diagnosed in the taxonomy and are now fixed in `src/generate.py`
  (`extract_citations` normalises them). Not yet measured on a fresh 20-trace
  draw, and not recorded in `notes.md`, so the taxonomy's 35% is still the
  *before* number.
- The README names the wrong LLM (llama-3.3-70b); the code uses `openai/gpt-oss-120b`.
- Groq free tier has a daily token cap. Collecting 120 traces can exhaust it, so
  start with `--n 30`.

## Part 9 — Suggested next steps

1. `python scripts/collect_traces.py --n 30 --rpm 25` to get real traces.
2. Open the UI, ask a few questions in each mode, and read the traces in
   `traces/traces.jsonl` the way Part 3 steps 3–5 describe.
3. The citation fix is done; collect fresh traces and record before/after counts in `notes.md`.
