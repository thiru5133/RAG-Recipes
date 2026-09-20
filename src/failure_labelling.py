"""Failure labelling: classify each question as retrieval failure, generation
failure, or success.

Retrieval failure = the correct chunk never appeared in top-k.
Generation failure = the correct chunk was retrieved but the answer was wrong.
Success = correct chunk retrieved and answer was correct (or close enough).

This is the core Week 4 deliverable: before you can fix anything, you need to
know *which kind* of wrong you're looking at.
"""
from typing import Dict, List, Optional

from config import REFUSAL_THRESHOLD
from evaluate import evaluate_hits
from guardrails import answer_question
from retrieve import search
from store import query


def _answer_matches(generated: Optional[str], expected: str, markers: List[str]) -> bool:
    """Check whether the generated answer is roughly correct.

    Uses the same marker-based approach as the retrieval eval: if any of the
    gold markers appear in the generated text, we treat it as correct.
    Falls back to checking whether key expected-answer fragments appear.
    """
    if not generated:
        return False
    gen_lower = generated.lower()
    # Check markers (exact substrings from the source card)
    for m in markers:
        if m.lower() in gen_lower:
            return True
    # Check if key parts of the expected answer appear
    for part in expected.split(","):
        part = part.strip()
        if len(part) > 3 and part.lower() in gen_lower:
            return True
    return False


def label_one(
    collection,
    q: Dict,
    k: int = 5,
    threshold: float = REFUSAL_THRESHOLD,
    run_generation: bool = True,
    strategy: Optional[str] = None,
    mode: str = "semantic",
    rerank: bool = False,
) -> Dict:
    """Label a single question as retrieval_failure, generation_failure, or success.

    Returns a dict with the label and all the evidence needed to justify it.
    When `strategy` is set, retrieval goes through `search()` so mode and
    rerank match the inspection sidebar. Otherwise this is plain Chroma cosine.
    """
    if strategy:
        hits = search(
            q["question"], strategy=strategy, k=k, mode=mode, rerank=rerank
        )
    else:
        hits = query(collection, q["question"], k=k)
    retrieval = evaluate_hits(hits, q)
    hit = retrieval["hit"]  # correct chunk in top-k?
    answer_present = retrieval["answer_present"]  # answer text in a retrieved chunk?

    gold_str = "/".join(q["gold_recipes"]) + " / " + q["gold_section"]

    result = {
        "qid": q["qid"],
        "question": q["question"],
        "type": q["type"],
        "gold": gold_str,
        "expected_answer": q["answer"],
        "hit_in_topk": hit,
        "answer_text_in_topk": answer_present,
        "first_hit_rank": retrieval["first_hit_rank"],
        "first_answer_rank": retrieval["first_answer_rank"],
        "retrieved_chunks": retrieval["results"],
    }

    # Step 2: classify
    if not hit:
        result["label"] = "retrieval_failure"
        result["reason"] = (
            f"The correct chunk ({q['gold_section']} from "
            f"{'/'.join(q['gold_recipes'])}) did not appear in top-{k}. "
            "No model can fix this — the context was wrong."
        )
        result["generated_answer"] = None
        result["generation_correct"] = None
        return result

    # Correct chunk IS in top-k. Now check generation.
    if not run_generation:
        # If we can't run generation (no API key), infer from answer_present
        result["label"] = "success" if answer_present else "generation_failure"
        result["reason"] = (
            "Correct chunk retrieved. "
            + ("Answer text is present in retrieved chunks."
               if answer_present
               else "Answer text was NOT found in the retrieved chunks, "
                    "so even a perfect model would struggle.")
        )
        result["generated_answer"] = None
        result["generation_correct"] = None
        return result

    # Step 3: run generation on the same hits the label used
    gen_result = answer_question(q["question"], hits, threshold=threshold)
    generated = gen_result.get("answer")
    result["generated_answer"] = generated

    if gen_result.get("error"):
        result["label"] = "success" if answer_present else "generation_failure"
        result["reason"] = (
            f"Correct chunk retrieved but generation failed: {gen_result['error']}. "
            "Labelled based on whether the answer text is in the retrieved chunks."
        )
        result["generation_correct"] = None
        return result

    if gen_result.get("refused"):
        result["label"] = "generation_failure"
        result["reason"] = (
            f"Correct chunk was in top-{k} but the model refused to answer "
            f"(gate: {gen_result['refused_by']}). This is a generation-side problem."
        )
        result["generation_correct"] = False
        return result

    # Step 4: check answer correctness
    markers = q.get("markers", [])
    correct = _answer_matches(generated, q["answer"], markers)
    result["generation_correct"] = correct

    if correct:
        result["label"] = "success"
        result["reason"] = "Correct chunk retrieved and answer matches expected."
    else:
        result["label"] = "generation_failure"
        result["reason"] = (
            f"Correct chunk was in top-{k} (rank {retrieval['first_hit_rank']}), "
            f"but the generated answer does not match. "
            f"Expected markers: {markers}. A smarter prompt or model might fix this."
        )

    return result


def label_all(
    collection,
    questions: List[Dict],
    k: int = 5,
    threshold: float = REFUSAL_THRESHOLD,
    run_generation: bool = True,
    strategy: Optional[str] = None,
    mode: str = "semantic",
    rerank: bool = False,
) -> Dict:
    """Label every question and return a summary."""
    labelled = [
        label_one(
            collection,
            q,
            k=k,
            threshold=threshold,
            run_generation=run_generation,
            strategy=strategy,
            mode=mode,
            rerank=rerank,
        )
        for q in questions
    ]

    counts = {"retrieval_failure": 0, "generation_failure": 0, "success": 0}
    for r in labelled:
        counts[r["label"]] += 1

    return {
        "total": len(labelled),
        "counts": counts,
        "per_question": labelled,
    }


def format_label_report(label_results: Dict) -> str:
    """Human-readable report of failure labels."""
    lines = []
    lines.append("## Failure Classification\n")
    c = label_results["counts"]
    lines.append(f"- **Success**: {c['success']}/{label_results['total']}")
    lines.append(f"- **Retrieval failures**: {c['retrieval_failure']}/{label_results['total']}")
    lines.append(f"- **Generation failures**: {c['generation_failure']}/{label_results['total']}")
    lines.append("")

    for r in label_results["per_question"]:
        emoji = {"success": "✅", "retrieval_failure": "❌🔍", "generation_failure": "❌🤖"}
        lines.append(f"### {r['qid']}: {r['question']}")
        lines.append(f"")
        lines.append(f"- **Label**: {emoji.get(r['label'], '')} `{r['label']}`")
        lines.append(f"- **Gold**: {r['gold']}")
        lines.append(f"- **Expected**: {r['expected_answer']}")
        lines.append(f"- **Correct chunk in top-k**: {'Yes' if r['hit_in_topk'] else 'No'}")
        if r['first_hit_rank']:
            lines.append(f"- **First correct rank**: {r['first_hit_rank']}")
        lines.append(f"- **Reason**: {r['reason']}")
        if r.get('generated_answer'):
            lines.append(f"- **Generated**: {r['generated_answer'][:200]}")
        lines.append("")

        # Show retrieved chunks as evidence
        lines.append("| Rank | chunk_id | recipe_id | section | score | correct | has_answer |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for h in r["retrieved_chunks"]:
            lines.append(
                f"| {h['rank']} | `{h['chunk_id']}` | {h['recipe_id']} | {h['section']} "
                f"| {h['score']:.4f} | {'YES' if h['correct'] else ''} "
                f"| {'yes' if h['has_answer'] else ''} |"
            )
        lines.append("")

    return "\n".join(lines)
