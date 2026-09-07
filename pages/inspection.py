"""Inspection view: side-by-side debug view showing
Question → Retrieved Chunks → Generated Answer → Failure Label.

This is a Streamlit multi-page app page. Place in pages/ next to app.py.
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from config import REFUSAL_THRESHOLD, STRATEGIES, TOP_K  # noqa: E402
from eval.questions import QUESTIONS  # noqa: E402
from evaluate import hit_rate_at, hits_at, mrr  # noqa: E402
from failure_labelling import label_one  # noqa: E402
from guardrails import answer_question  # noqa: E402
from retrieve import search  # noqa: E402
from store import get_collection  # noqa: E402

st.set_page_config(page_title="Inspection View", layout="wide")
st.title("🔍 Inspection View — Failure Debugging")
st.caption("Side-by-side: Question → Retrieved Chunks → Answer → Failure Label")

# ----- Sidebar controls -----
with st.sidebar:
    st.header("Settings")
    strategy = st.radio("Chunking strategy", list(STRATEGIES), index=1)
    mode = st.radio("Search mode", ["semantic", "bm25", "hybrid"], index=0)
    k = st.slider("Top-K", 1, 10, TOP_K)
    run_gen = st.checkbox("Run generation (needs API key)", value=False)

# ----- Run evaluation on all questions -----
collection_name = STRATEGIES[strategy]
try:
    coll = get_collection(collection_name)
except Exception:
    st.error(f"Collection '{collection_name}' not found. Run ingestion first!")
    st.stop()

# Label all questions
with st.spinner("Evaluating all questions..."):
    labels = [label_one(coll, q, k=k, run_generation=run_gen) for q in QUESTIONS]

# ----- Summary metrics -----
counts = {"retrieval_failure": 0, "generation_failure": 0, "success": 0}
for r in labels:
    counts[r["label"]] += 1

col1, col2, col3 = st.columns(3)
col1.metric("✅ Success", counts["success"])
col2.metric("❌🔍 Retrieval Failures", counts["retrieval_failure"])
col3.metric("❌🤖 Generation Failures", counts["generation_failure"])

st.divider()

# ----- Per-question inspection -----
for lbl in labels:
    emoji = {"success": "✅", "retrieval_failure": "❌🔍", "generation_failure": "❌🤖"}
    e = emoji.get(lbl["label"], "")

    with st.expander(f"{e} {lbl['qid']}: {lbl['question']}  —  `{lbl['label']}`",
                     expanded=(lbl["label"] != "success")):

        left, mid, right = st.columns([1, 2, 1])

        # ----- Left: Question + Expected -----
        with left:
            st.markdown("#### Question")
            st.write(lbl["question"])
            st.markdown("**Gold**")
            st.write(lbl["gold"])
            st.markdown("**Expected answer**")
            st.write(lbl["expected_answer"])

        # ----- Middle: Retrieved chunks -----
        with mid:
            st.markdown("#### Retrieved Chunks")
            for h in lbl["retrieved_chunks"]:
                color = "🟢" if h["correct"] else "🔴"
                ans_mark = " 📝" if h["has_answer"] else ""
                st.markdown(
                    f"{color} **Rank {h['rank']}** · `{h['chunk_id']}` · "
                    f"{h['recipe_id']} / {h['section']} · "
                    f"score {h['score']:.4f}{ans_mark}"
                )
                st.caption(h["snippet"][:120] + "…" if len(h.get("snippet", "")) > 120 else h.get("snippet", ""))

        # ----- Right: Label + Evidence -----
        with right:
            st.markdown("#### Failure Label")
            st.markdown(f"**{e} `{lbl['label']}`**")
            st.markdown("**Reason**")
            st.write(lbl["reason"])
            if lbl.get("generated_answer"):
                st.markdown("**Generated answer**")
                st.write(lbl["generated_answer"][:300])

st.divider()

# ----- Compare search modes -----
st.subheader("🔄 Compare: Semantic vs Hybrid")
st.caption("Run both modes and compare hit-rate@3 side by side.")

if st.button("Run comparison", type="primary"):
    with st.spinner("Running semantic evaluation..."):
        sem_results = []
        for q in QUESTIONS:
            hits = search(q["question"], strategy=strategy, k=k, mode="semantic")
            from evaluate import judge
            first_hit = None
            for h in hits:
                recipe_ok, section_ok, _ = judge(h, q)
                if recipe_ok and section_ok and first_hit is None:
                    first_hit = h["rank"]
            sem_results.append({"qid": q["qid"], "first_hit_rank": first_hit})

    with st.spinner("Running hybrid evaluation..."):
        hyb_results = []
        for q in QUESTIONS:
            hits = search(q["question"], strategy=strategy, k=k, mode="hybrid")
            first_hit = None
            for h in hits:
                recipe_ok, section_ok, _ = judge(h, q)
                if recipe_ok and section_ok and first_hit is None:
                    first_hit = h["rank"]
            hyb_results.append({"qid": q["qid"], "first_hit_rank": first_hit})

    # Display comparison
    st.markdown("| Q | Semantic rank | Hybrid rank | Changed? |")
    st.markdown("| --- | --- | --- | --- |")
    rows = []
    for s, h in zip(sem_results, hyb_results):
        s_rank = s["first_hit_rank"] or "—"
        h_rank = h["first_hit_rank"] or "—"
        changed = "✅ Improved" if (h["first_hit_rank"] and (not s["first_hit_rank"] or h["first_hit_rank"] < s["first_hit_rank"])) else \
                  "⚠️ Regressed" if (s["first_hit_rank"] and (not h["first_hit_rank"] or h["first_hit_rank"] > s["first_hit_rank"])) else \
                  "—"
        rows.append(f"| {s['qid']} | {s_rank} | {h_rank} | {changed} |")
    st.markdown("\n".join(rows))

    sem_hr = sum(1 for r in sem_results if r["first_hit_rank"] and r["first_hit_rank"] <= 3)
    hyb_hr = sum(1 for r in hyb_results if r["first_hit_rank"] and r["first_hit_rank"] <= 3)
    n = len(QUESTIONS)

    c1, c2 = st.columns(2)
    c1.metric("Semantic hit-rate@3", f"{sem_hr}/{n} ({sem_hr/n:.2%})")
    c2.metric("Hybrid hit-rate@3", f"{hyb_hr}/{n} ({hyb_hr/n:.2%})",
              delta=f"{hyb_hr - sem_hr:+d}")
