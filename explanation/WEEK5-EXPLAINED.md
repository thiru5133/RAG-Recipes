# Week 5 — Tracing (study notes)

Week 5 is error analysis. The app does not get a new feature. We record what it already did, read a fixed sample by hand, group the failures, and prove one case can be run again.

Six recipe cards. Question comes in. Retrieval finds chunks. A gate may refuse. If it does not, Groq `openai/gpt-oss-120b` answers from the chunks. Every one of those steps is written down. That write-down is a **trace**.

The assignment files stay as they are: `taxonomy.md` (the ranked table), `notes.md` (the 20 sentences, seeds, replay), `WEEK5.md` (what we changed). This file is the lesson.

---

## 1. Tracing

A trace is one JSON line for one question. `src/tracing.py` appends it to `traces/traces.jsonl`. The UI and `scripts/collect_traces.py` both go through the same function: `answer_and_trace`.

That function is the whole path:

1. Search the index (`search`).
2. Run the gates and, if the score clears, call the model (`answer_question`).
3. Build one record (`build_trace`).
4. Append it (`append_trace`).

The record is the audit. It stores enough to rebuild the call later, not only the final sentence.

| Field | Why it is there |
| --- | --- |
| `trace_id` | Name of this one run. Replay and the taxonomy point at it. |
| `question` | What was asked. |
| `prompt_version` | Which instruction text was used (`v1.2.0` in this run). |
| `system_prompt_sha256`, `user_prompt_sha256` | Fingerprint of the exact prompt bytes, so "v1.2.0" cannot silently mean a different paragraph. |
| `model` | Which LLM. Here `openai/gpt-oss-120b`. |
| `model_params` | `temperature` and `max_tokens`. Here temperature is `0`, max tokens `400`. |
| `strategy`, `mode`, `k`, `threshold` | Chunking, search mode, how many chunks, the refusal cutoff `0.30`. |
| `retrieved_chunks[].text` | The chunk **words**, not only the ids. Without the words the prompt cannot be rebuilt. |
| `raw_output` | Whatever the model said, unedited. |
| `refused`, `refused_by`, `top_score` | Gate decision. Some traces never call the model. |
| `citations`, `citation_check` | Whether the bracket shape the verifier accepts was actually there. |
| `finish_reason`, `usage` | Did the model stop, or hit the token ceiling. |

Live JSON is not in git. Rebuild it on your machine. The argument made from it is in `taxonomy.md` and `notes.md`.

---

## 2. Temperature

Temperature is how random the next word is. Same prompt, same model, different temperature, different answers.

| Temperature | What the model does | Hallucination | Use it when |
| --- | --- | --- | --- |
| **0** | Picks the most likely next word every time. Re-sending the same prompt usually returns the same sentence. | Lowest. It can still invent a quantity if the prompt is weak. Zero temperature is not a truth guarantee. | Facts, citations, replay. This project sets `TEMPERATURE = 0` in `src/generate.py`. |
| **about 0.5** (inside 0–1) | Mixes the top choices. Wording changes between calls. | Rises. A recipe number can drift off the card. | Chat where variety is useful and a wrong gram is not dangerous. |
| **1** | Default on many APIs. Each call can differ a lot. | Higher. | Drafting, brainstorming. |
| **above 1, up to 2** | Unlikely words get picked on purpose. | Highest. Answers wander, citations break, replay will not match. | Almost never for this app. |

For this corpus the failure we care about is a gram, a minute, or a citation that is not on the card. Variety is not a feature. Temperature stays at 0 so a replay is even possible.

Even at 0, identical output is not a promise. One replay in this project matched. An earlier replay of a different trace did not. The trace still has to record `finish_reason`, or a cut-off answer looks like a new hallucination.

---

## 3. Prompt version and the model — the audit

A prompt is the instruction block sent with the chunks. When the wording changes, the name changes: `v1`, then `v1.2.0`, later a `v2` if the rules change. The version id is not decoration. It is how you know which rules produced an answer.

Every trace stores four audit facts together:

- **prompt version** — `prompt_version`, for example `v1.2.0`
- **exact text** — sha256 of the system prompt and of the user prompt that were actually sent
- **which LLM** — `model`
- **how it was sampled** — `model_params.temperature` and `max_tokens`

`PROMPT_REGISTRY` in `src/generate.py` maps the version id back to the system-prompt string. Replay loads `v1.2.0` from that registry and checks the hash. If someone edits the prompt and forgets to bump the version, the hash fails. That is the point of the audit.

Do not compare a v1 answer with a v2 answer and call it the same test. The scenario belongs to the version that ran it.

---

## 4. Sampling — random with a seed, and curated

There were **386** real traces (424 lines in the file, 38 dropped because the API call failed and there is no model output to read). Reading all 386 by hand is not the method. Read a sample. Two kinds.

### Random, fixed by a seed

```text
random.Random(42).sample(population, 20)
```

`42` is the seed. The draw is random in the sense that nobody picked the rows because they looked bad or good. It is fixed in the sense that the same file plus the same seed returns the same 20 ids. `scripts/sampling.py` is the only place a sample is drawn. The file sha256 is recorded too, because a seed only repeats against the same file.

That sample is T01–T20 in `notes.md`. No sorting, no "skip the boring ones".

### Curated

The demo sample is the eight questions already shown at reviews (Q1–Q8). Seed `4242` draws 10 traces from that list only, and those 10 are disjoint from the random 20.

Curated means you chose the pool on purpose. It answers a different question: "what do we see on stage?" It does not answer "what does production do?"

In this run the same hybrid-gate failure was **6/20 (30%)** in the random sample and **5/10 (50%)** in the demo set. The review set was worse, because reviews reach for hybrid search. A curated demo can flatter you or indict you. It is not a substitute for the seeded random 20.

---

## 5. Read first, group second

Open coding: one sentence per trace, written while reading, before any failure name exists. `scripts/read_traces.py` is the reader. No fix is made during the pass.

The sentence says what was on the screen. It does not say the cause and it does not say the fix. Those come after, in the taxonomy, built from the sentences.

Once the 20 sentences existed: 9 answers, 11 refusals. All 9 answers carried the number printed on the card. Of the 11 refusals, 4 were correct (the question is not in the corpus) and 7 refused a question the cards do answer.

---

## 6. Failure modes — group the 20, then rank severity

A failure mode is a named pile. You do not file 14 separate bugs if 6 of them are the same bug.

Of the 20, **14 had a defect** (the "about 10–15 fail" picture). They grouped into five modes. Six traces had no defect.

| Mode | Count | What it is |
| --- | --- | --- |
| Hybrid search answers nothing | 6/20 (30%) | Fused RRF scores sit near `0.03`. The gate compares them to cosine `0.30`. The model is never called. Top chunks were often the right section. |
| Citation in full-width brackets `【 】` | 3/20 | Number is right. Verifier records no citation. |
| Citation padded with spaces `[ R003-A00 \| R003 ]` | 3/20 | Same consequence, different shape. |
| Citation copied from the context header `[chunk_id: X \| recipe_id: Y]` | 1/20 | Same consequence, third shape. |
| Ingredients table missing from top 3 | 1/20 | Semantic k=3 never retrieved the table, so the model refused a quantity that is on the card. |

The three citation rows are separate shapes (each needs its own check) and one consequence: **7/20 (35%)** answers the verifier cannot parse.

Severity is how bad it is for the cook, not how annoyed the engineer is.

- **Poisons the dish** — a wrong gram, time, or allergen. None of these 20 did that. Every answered trace had the number on the card.
- **Annoys the cook** — no answer arrives, or the answer is right but the source cannot be checked. Every defect row in `taxonomy.md` is this level.

The table is ordered by what to fix first. The top row is one mismatched score scale, 30% of the sample. That is the mode named in the prediction, then fixed: rank still uses RRF, the gate reads cosine. After the fix, a new seeded draw (seed `43`) had 0 hybrid gate refusals.

---

## 7. Taxonomy

Taxonomy is the manual step after the sentences:

1. Group traces that failed the same way.
2. Count them and write the percent.
3. Give each group a severity.
4. Attach one example `trace_id`.
5. Leave the clean traces as their own row so the denominator stays 20.

That table is `taxonomy.md`. It is written by hand from the 20 sentences. It is not a dashboard and it is not a model judging itself.

Fix order follows the table. Do not start with the rare retrieval miss while the hybrid gate is refusing 30%.

---

## 8. Replay

Replay answers: "If I send this exact scenario again, do I get this answer?"

The 20 traces are the reading set. Replay does not re-label all 20. One trace is picked from them with another seed, so it is not the one that looks best:

```text
random.Random(11).choice(sample)  →  bf0e4580
```

Scenario that was stored under prompt `v1.2.0`:

- question: chicken breast instead of thigh, how long to simmer
- config from the trace: basic chunks, bm25, k=3
- model from the trace: `openai/gpt-oss-120b`, temperature `0`, max tokens `400`

`scripts/replay_trace.py` rebuilds both prompts from the trace alone. Checks:

| Check | Result on `bf0e4580` |
| --- | --- |
| System prompt rebuilt from `prompt_version`, sha256 matches | True |
| User prompt rebuilt from stored chunk text, sha256 matches | True |
| Gate re-run from `top_score` and `threshold`, same verdict | True |
| Original output and replayed output | Identical |

If a replay comes back wrong, the usual causes are: the chunk text was never stored, the prompt hash was never stored, temperature was not 0, or `finish_reason` is missing so a truncated answer cannot be explained. Gate-refused traces have no generation to replay. Their gate decision replays. That is all.

A public score on the answer string would have missed this week. The nine answered traces had the right number. The largest failure never called the model.

---

## How the pieces sit together

```text
question
  → answer_and_trace          (the function that logs)
  → one JSON line             (prompt version, model, temperature, chunks, raw output)
  → many lines on disk
  → seeded random sample 20   (seed 42, not hand-picked)
  → curated demo sample       (review questions only — a different question)
  → 20 sentences by hand
  → group into failure modes
  → severity, count, example id     = taxonomy
  → replay one scenario on the same prompt version and the same model
  → predict the top mode, then change only that
```

## Commands

```bash
python scripts/collect_traces.py --n 120 --rpm 25
python scripts/read_traces.py
python scripts/week5_analysis.py
python scripts/replay_trace.py
```
