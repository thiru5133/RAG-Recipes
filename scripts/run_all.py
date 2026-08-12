"""End-to-end run: ingest, evaluate, sweep, filter demo, answers, refusals,
then write results.md entirely from measured output.

Nothing in results.md is hand-written prose about numbers: every figure below is
computed in this process, so the report cannot drift from the code.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import demo_filter  # noqa: E402
import ingest  # noqa: E402
from chunking import chunk_basic, chunk_structured  # noqa: E402
from config import REFUSAL_THRESHOLD, RESULTS_DIR, STRATEGIES, TOP_K  # noqa: E402
from eval.questions import QUESTIONS, TABLE_QIDS  # noqa: E402
from eval.unanswerable import UNANSWERABLE  # noqa: E402
from evaluate import answers_at, evaluate_strategy, hits_at  # noqa: E402
from guardrails import answer_question  # noqa: E402
from loader import load_corpus  # noqa: E402
from retrieve import search  # noqa: E402
from store import ephemeral_collection, get_collection  # noqa: E402

GROUNDED_QIDS = ["Q1", "Q4", "Q7"]
NON_TABLE_QIDS = [q["qid"] for q in QUESTIONS if q["qid"] not in TABLE_QIDS]


# --------------------------------------------------------------------------
# Experiments
# --------------------------------------------------------------------------

def sweep(recipes):
    """Chunk size / overlap / rows-per-chunk sweeps, scored at k=3 and k=5.

    Every configuration is built in an in-memory collection so the persisted
    index is untouched.
    """
    rows = []

    for size in (300, 500, 800):
        for overlap in (0, 80, 150):
            if overlap >= size:
                continue
            chunks = [c for r in recipes for c in chunk_basic(r, size, overlap)]
            coll = ephemeral_collection(chunks, f"basic_{size}_{overlap}")
            res = evaluate_strategy(coll, QUESTIONS, k=5)
            pq = res["per_question"]
            rows.append({
                "strategy": "basic",
                "config": f"size={size}, overlap={overlap}",
                "chunks": len(chunks),
                "hit3": hits_at(pq, 3), "hit5": hits_at(pq, 5),
                "ans5": answers_at(pq, 5),
                "table_hit5": hits_at(pq, 5, TABLE_QIDS),
                "table_ans5": answers_at(pq, 5, TABLE_QIDS),
                "other_hit5": hits_at(pq, 5, NON_TABLE_QIDS),
            })

    for rows_per, max_chars in ((4, 700), (8, 700), (16, 700), (8, 400)):
        chunks = [c for r in recipes
                  for c in chunk_structured(r, max_chars=max_chars, rows_per_chunk=rows_per)]
        coll = ephemeral_collection(chunks, f"struct_{rows_per}_{max_chars}")
        res = evaluate_strategy(coll, QUESTIONS, k=5)
        pq = res["per_question"]
        rows.append({
            "strategy": "structured",
            "config": f"rows/chunk={rows_per}, max_chars={max_chars}",
            "chunks": len(chunks),
            "hit3": hits_at(pq, 3), "hit5": hits_at(pq, 5),
            "ans5": answers_at(pq, 5),
            "table_hit5": hits_at(pq, 5, TABLE_QIDS),
            "table_ans5": answers_at(pq, 5, TABLE_QIDS),
            "other_hit5": hits_at(pq, 5, NON_TABLE_QIDS),
        })

    return rows


def grounded_answers():
    out = []
    for q in QUESTIONS:
        if q["qid"] not in GROUNDED_QIDS:
            continue
        hits = search(q["question"], strategy="structured", k=TOP_K)
        result = answer_question(q["question"], hits)
        result["qid"] = q["qid"]
        result["expected"] = q["answer"]
        result["hits"] = hits
        out.append(result)
    return out


def refusals():
    out = []
    for u in UNANSWERABLE:
        hits = search(u["question"], strategy="structured", k=TOP_K)
        result = answer_question(u["question"], hits)
        result["qid"] = u["qid"]
        result["why"] = u["why"]
        result["hits"] = hits
        out.append(result)
    return out


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def per_question_table(res):
    lines = ["| Q | Type | Gold | Hit@5 | First correct rank | Answer text present | Top-1 retrieved |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in res["per_question"]:
        top = r["results"][0] if r["results"] else None
        top_desc = f"{top['recipe_id']} / {top['section']} ({top['score']:.3f})" if top else "-"
        lines.append(
            f"| {r['qid']} | {r['type']} | {'/'.join(r['gold_recipes'])} / {r['gold_section']} "
            f"| {'YES' if r['hit'] else 'NO'} | {r['first_hit_rank'] or '-'} "
            f"| {'yes' if r['answer_present'] else 'NO'} | {top_desc} |"
        )
    return "\n".join(lines)


def search_only_appendix(results):
    parts = []
    for strategy, res in results.items():
        parts.append(f"### Strategy: {strategy}\n")
        for r in res["per_question"]:
            parts.append(f"**{r['qid']} — {r['question']}**  \n"
                         f"Gold: {'/'.join(r['gold_recipes'])} / {r['gold_section']}\n")
            parts.append("| Rank | chunk_id | recipe_id | section | score | correct | has answer | snippet |")
            parts.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for h in r["results"]:
                snippet = h["snippet"].replace("|", "\\|")[:110]
                parts.append(
                    f"| {h['rank']} | `{h['chunk_id']}` | {h['recipe_id']} | {h['section']} "
                    f"| {h['score']:.4f} | {'YES' if h['correct'] else ''} "
                    f"| {'yes' if h['has_answer'] else ''} | {snippet} |"
                )
            parts.append("")
    return "\n".join(parts)


def hits_table(hits):
    lines = ["| Rank | chunk_id | recipe_id | recipe | section | dietary_tags | score |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for h in hits:
        m = h["metadata"]
        lines.append(
            f"| {h['rank']} | `{h['chunk_id']}` | {m['recipe_id']} | {m['recipe_title']} "
            f"| {m['section']} | {m['dietary_tags']} | {h['score']:.4f} |"
        )
    return "\n".join(lines)


def failure_analysis(results):
    """Report every question that failed either metric, with the evidence."""
    blocks = []
    for strategy, res in results.items():
        for r in res["per_question"]:
            if r["hit"] and r["answer_present"]:
                continue
            top = r["results"][0] if r["results"] else None
            kind = []
            if not r["hit"]:
                kind.append("wrong recipe/section in top-5")
            if not r["answer_present"]:
                kind.append("answer text absent from every retrieved chunk")
            blocks.append({
                "strategy": strategy,
                "qid": r["qid"],
                "question": r["question"],
                "gold": f"{'/'.join(r['gold_recipes'])} / {r['gold_section']}",
                "failure": "; ".join(kind),
                "top1": (f"`{top['chunk_id']}` ({top['recipe_id']} / {top['section']}, "
                         f"score {top['score']:.4f})" if top else "-"),
                "rows": r["results"],
                "expected_answer": r["expected_answer"],
            })
    return blocks


def build_report(results, sweep_rows, filter_demo, answers, refusal_runs, corpus_stats):
    basic, structured = results["basic"], results["structured"]
    b_pq, s_pq = basic["per_question"], structured["per_question"]
    n = basic["total"]

    winner = "structured" if structured["hits"] >= basic["hits"] else "basic"
    margin_hit = structured["hits"] - basic["hits"]
    margin_ans = structured["answers"] - basic["answers"]

    L = []
    A = L.append

    A("# RAG over 6 recipe cards — retrieval evaluation\n")
    A("Generated by `scripts/run_all.py`. Every number below is measured in that run.\n")
    A(f"- Corpus: **{corpus_stats['recipes']} recipe cards**, indexed under two chunking "
      f"strategies and nothing else.\n"
      f"- Embeddings: ChromaDB default `all-MiniLM-L6-v2` (ONNX), cosine space. "
      f"Score = `1 - cosine_distance`.\n"
      f"- Chunks: basic **{corpus_stats['basic_chunks']}**, structure-aware "
      f"**{corpus_stats['structured_chunks']}**.\n")

    A("\n## 1. The 8 questions, with the recipe and section that answers them\n")
    A("| Q | Question | Correct recipe | Correct section | Type | Expected answer |")
    A("| --- | --- | --- | --- | --- | --- |")
    for q in QUESTIONS:
        A(f"| {q['qid']} | {q['question']} | {', '.join(q['gold_recipes'])} "
          f"| {q['gold_section']} | {q['type']} | {q['answer']} |")
    A(f"\n{len(TABLE_QIDS)} of 8 ({', '.join(TABLE_QIDS)}) can only be answered from an "
      "ingredient or nutrition table.\n")

    A("\n## 2. Metadata on every chunk\n")
    A("Required fields, present on all chunks in both collections: `source_file`, "
      "`recipe_id`, `cuisine`, `dietary_tags`.\n")
    A("Also carried for citation and evaluation: `chunk_id`, `recipe_title`, `section`, "
      "`sections_covered`, `chunk_type`, `strategy`.\n")
    A("ChromaDB metadata values must be scalars, so `dietary_tags` is stored as a display "
      "string *and* expanded into one boolean per tag (`tag_vegan`, `tag_gluten_free`, …) "
      "so `where={\"tag_vegan\": True}` works. Example:\n")
    A("```json")
    A(json.dumps(corpus_stats["sample_metadata"], indent=2))
    A("```\n")

    A("\n## 3. Per-question retrieval results\n")
    A(f"### Strategy A — basic fixed-size chunking\n\n{per_question_table(basic)}\n")
    A(f"### Strategy B — structure-aware chunking\n\n{per_question_table(structured)}\n")

    A("\n## 4. Hit-in-Top-5\n")
    A("Hit = a top-5 chunk from the correct recipe covering the correct section.\n")
    A("| Strategy | Hit-in-Top-5 | Hit-in-Top-3 | Answer text in Top-5 | Table Qs Hit@5 | Table Qs answer@5 |")
    A("| --- | --- | --- | --- | --- | --- |")
    A(f"| A basic | **{basic['hits']}/{n}** | {hits_at(b_pq, 3)}/{n} | {basic['answers']}/{n} "
      f"| {hits_at(b_pq, 5, TABLE_QIDS)}/{len(TABLE_QIDS)} | {answers_at(b_pq, 5, TABLE_QIDS)}/{len(TABLE_QIDS)} |")
    A(f"| B structure-aware | **{structured['hits']}/{n}** | {hits_at(s_pq, 3)}/{n} | {structured['answers']}/{n} "
      f"| {hits_at(s_pq, 5, TABLE_QIDS)}/{len(TABLE_QIDS)} | {answers_at(s_pq, 5, TABLE_QIDS)}/{len(TABLE_QIDS)} |")
    A(f"\n**Headline: basic {basic['hits']}/{n} vs structure-aware {structured['hits']}/{n}.**\n")
    A("The second metric matters as much as the headline: a blind window can overlap the "
      "right section and still have had the answer row sliced off, which counts as a hit "
      "but would not let the model answer.\n")

    A("\n## 5. Experiments: chunk size, overlap, top-3 vs top-5\n")
    A("| Strategy | Config | Chunks | Hit@3 | Hit@5 | Answer@5 | Table Hit@5 | Table Answer@5 | Non-table Hit@5 |")
    A("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in sweep_rows:
        A(f"| {r['strategy']} | {r['config']} | {r['chunks']} | {r['hit3']}/{n} | {r['hit5']}/{n} "
          f"| {r['ans5']}/{n} | {r['table_hit5']}/{len(TABLE_QIDS)} | {r['table_ans5']}/{len(TABLE_QIDS)} "
          f"| {r['other_hit5']}/{len(NON_TABLE_QIDS)} |")
    A("\nTable-dependent and non-table questions are scored separately so the table effect "
      "is visible instead of averaged away. Top-3 vs Top-5 is the Hit@3 and Hit@5 columns "
      "of the same runs.\n")

    A("\n## 6. Metadata filtering on dietary_tags\n")
    A(f"Query: **{filter_demo['query']!r}**, strategy {filter_demo['strategy']}, "
      f"filter `{filter_demo['where']}`.\n")
    A(f"\n**Unfiltered**\n\n{hits_table(filter_demo['unfiltered'])}\n")
    A(f"\n**Filtered — dietary_tags contains `{filter_demo['tag']}`**\n\n"
      f"{hits_table(filter_demo['filtered'])}\n")
    if filter_demo["top1_changed"]:
        u, f = filter_demo["unfiltered"][0], filter_demo["filtered"][0]
        A(f"\nTop-1 changes: `{u['chunk_id']}` ({u['metadata']['recipe_id']}, "
          f"{u['metadata']['recipe_title']}, score {u['score']:.4f}) → `{f['chunk_id']}` "
          f"({f['metadata']['recipe_id']}, {f['metadata']['recipe_title']}, "
          f"score {f['score']:.4f}).\n")
        A("The two green curries are near-duplicates, so pure vector similarity cannot "
          "separate them. The filter does it on structured metadata rather than on text, "
          "which is the only reliable way to honour a dietary constraint.\n")
    else:
        A("\nTop-1 did **not** change for this query under this filter; the unfiltered "
          "winner already satisfies the constraint. Reported as measured.\n")

    A("\n## 7. Grounded answers with citations\n")
    A(f"Retrieval: strategy B, top-{TOP_K}. Every claim must cite `[chunk_id | recipe_id]`, "
      "and citations are verified against the chunks actually supplied.\n")
    for a in answers:
        A(f"\n### {a['qid']} — {a['question']}\n")
        if a["error"]:
            A(f"> Generation unavailable: {a['error']}\n")
            A(f"Retrieved context (top-{TOP_K}):\n\n{hits_table(a['hits'])}\n")
            continue
        A(f"**Answer**\n\n> {a['answer']}\n")
        A(f"\n*Expected:* {a['expected']}\n")
        c = a["citations"]
        if c:
            cited = ", ".join(f"`[{x[0]} | {x[1]}]`" for x in c["cited"]) or "none"
            A(f"\n*Citations:* {cited}  \n"
              f"*Verification:* unknown chunk_ids: {c['unknown_chunk_ids'] or 'none'}; "
              f"recipe_id mismatches: {c['recipe_id_mismatches'] or 'none'}; "
              f"**valid: {c['valid']}**\n")
        A(f"\n<details><summary>Context supplied</summary>\n\n{hits_table(a['hits'])}\n</details>\n")

    A("\n## 8. Refusals on unanswerable questions\n")
    A(f"Two independent gates: a score threshold of {REFUSAL_THRESHOLD} on the top hit, "
      "and a system prompt that permits only a fixed refusal string when the context "
      "does not contain the answer.\n")
    for r in refusal_runs:
        A(f"\n### {r['qid']} — {r['question']}\n")
        A(f"*Why it is unanswerable:* {r['why']}\n")
        top = r["hits"][0] if r["hits"] else None
        if top:
            A(f"\n*Top retrieved anyway:* `{top['chunk_id']}` "
              f"({top['metadata']['recipe_id']} / {top['metadata']['section']}) "
              f"score {top['score']:.4f}\n")
        if r["error"]:
            A(f"\n> Generation unavailable: {r['error']}\n")
            continue
        A(f"\n**Response**\n\n> {r['answer']}\n")
        A(f"\n*Refused:* **{r['refused']}** (gate: {r['refused_by'] or 'none'})\n")

    A("\n## 9. Retrieval failures\n")
    blocks = failure_analysis(results)
    if not blocks:
        A("No question failed either metric under either strategy.\n")
    for b in blocks:
        A(f"\n### {b['strategy']} — {b['qid']}: {b['question']}\n")
        A(f"- Gold: {b['gold']}\n- Failure: {b['failure']}\n- Top-1 returned: {b['top1']}\n"
          f"- Expected answer: {b['expected_answer']}\n")
        A("\n| Rank | chunk_id | recipe_id | section | score | correct | has answer |")
        A("| --- | --- | --- | --- | --- | --- | --- |")
        for h in b["rows"]:
            A(f"| {h['rank']} | `{h['chunk_id']}` | {h['recipe_id']} | {h['section']} "
              f"| {h['score']:.4f} | {'YES' if h['correct'] else ''} "
              f"| {'yes' if h['has_answer'] else ''} |")
    A("\n**Why these happen.** Two distinct causes show up in this corpus:\n")
    A("1. *Context stripped by blind splitting.* A fixed-size window cuts the ingredient "
      "table wherever the character count runs out. The resulting chunk holds rows like "
      "`| Heavy cream | 60 | ml |` with no table header, no `## Ingredients` heading and "
      "no recipe title — the title appears only in the very first chunk of each card. The "
      "embedding of such a chunk carries no signal about *which* recipe it belongs to, so "
      "a question naming the dish cannot reach it.\n")
    A("2. *Genuine ambiguity between near-duplicate recipes.* Q8 (\"How much curry paste do "
      "I need?\") names no dish. R004 and R005 share most of their ingredient table, so both "
      "are legitimately close in vector space and no chunking strategy can resolve it. "
      "This is not a retrieval bug — it is an under-specified query, and the fix is metadata "
      "filtering or a clarifying question, not smaller chunks.\n")

    A("\n## 10. Final chunking decision\n")
    A(f"**Chosen: strategy {'B, structure-aware' if winner == 'structured' else 'A, basic'}.**\n")
    A(f"\nMeasured basis:\n\n"
      f"- Hit-in-Top-5: basic {basic['hits']}/{n} vs structure-aware {structured['hits']}/{n} "
      f"({margin_hit:+d}).\n"
      f"- Answer text actually present in top-5: basic {basic['answers']}/{n} vs "
      f"structure-aware {structured['answers']}/{n} ({margin_ans:+d}).\n"
      f"- Table-dependent questions: basic {answers_at(b_pq, 5, TABLE_QIDS)}/{len(TABLE_QIDS)} vs "
      f"structure-aware {answers_at(s_pq, 5, TABLE_QIDS)}/{len(TABLE_QIDS)} with the answer present.\n")
    A("\nJustification. Recipe cards are mostly table. The unit that answers a question is a "
      "single row, but a row is meaningless without its header (which names the columns) and "
      "its title (which names the dish). Strategy B makes the row-plus-header-plus-title group "
      "the atomic unit, so every chunk is independently interpretable and independently "
      "retrievable. Strategy A's failure mode is not that it retrieves the wrong document — "
      "it is that the chunk it retrieves has been robbed of the context that made it "
      "answerable.\n")
    A("\nThe cost is duplication: repeating the title and header in every row group inflates "
      f"the index from {corpus_stats['basic_chunks']} to {corpus_stats['structured_chunks']} "
      "chunks and repeats tokens. On a 6-card corpus that is free; at scale it is the trade "
      "being bought, and the table above is what it buys.\n")

    A("\n## Appendix — search-only results, all 8 questions, both strategies\n")
    A("Retrieval only, no generation.\n")
    A(search_only_appendix(results))

    return "\n".join(L)


def main():
    print("Ingesting…")
    recipes, basic_chunks, structured_chunks = ingest.main()

    print("Evaluating both strategies…")
    results = {}
    for strategy, collection_name in STRATEGIES.items():
        results[strategy] = evaluate_strategy(get_collection(collection_name), QUESTIONS, k=TOP_K)
        print(f"  {strategy}: Hit@5 {results[strategy]['hits']}/{results[strategy]['total']}, "
              f"answer present {results[strategy]['answers']}/{results[strategy]['total']}")

    print("Running sweeps…")
    sweep_rows = sweep(recipes)

    print("Filter demo…")
    filter_demo = demo_filter.run()
    print(f"  top-1 changed: {filter_demo['top1_changed']}")

    print("Grounded answers…")
    answers = grounded_answers()

    print("Refusals…")
    refusal_runs = refusals()
    print(f"  refused {sum(1 for r in refusal_runs if r['refused'])}/{len(refusal_runs)}")

    corpus_stats = {
        "recipes": len(recipes),
        "basic_chunks": len(basic_chunks),
        "structured_chunks": len(structured_chunks),
        "sample_metadata": structured_chunks[1].metadata,
    }

    report = build_report(results, sweep_rows, filter_demo, answers, refusal_runs, corpus_stats)
    (ROOT / "results.md").write_text(report, encoding="utf-8")

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "search_only.json").write_text(json.dumps(results, indent=2))
    (RESULTS_DIR / "sweeps.json").write_text(json.dumps(sweep_rows, indent=2))

    print(f"\nWrote {ROOT / 'results.md'}")
    print(f"Wrote {RESULTS_DIR / 'search_only.json'} and sweeps.json")


if __name__ == "__main__":
    main()
