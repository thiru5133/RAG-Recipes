"""Streamlit UI: ad-hoc retrieval with a dietary filter, and grounded answers."""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from chunking import chunk_basic, chunk_structured  # noqa: E402
from config import COLLECTION_BASIC, COLLECTION_STRUCTURED, RECIPE_DIR, REFUSAL_THRESHOLD  # noqa: E402
from guardrails import answer_question  # noqa: E402
from loader import load_corpus, load_recipe  # noqa: E402
from retrieve import dietary_filter, search  # noqa: E402
from store import get_collection, reset_collection, upsert_chunks  # noqa: E402

st.set_page_config(page_title="Recipe RAG", layout="wide")
st.title("Recipe RAG — retrieval and grounded answers")


@st.cache_data
def all_tags():
    tags = set()
    for r in load_corpus():
        tags.update(r.dietary_tags)
    return sorted(tags)


with st.sidebar:
    st.header("Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload files (PDF, DOCX, TXT, MD, JSON, CSV, etc.)",
        type=["pdf", "docx", "doc", "md", "txt", "json", "csv", "html"],
        accept_multiple_files=True,
        help="Upload document files to ingest dynamically into ChromaDB",
    )
    if uploaded_files:
        if st.button("Ingest Uploaded Files", type="secondary"):
            count = 0
            RECIPE_DIR.mkdir(parents=True, exist_ok=True)
            for file_obj in uploaded_files:
                save_path = RECIPE_DIR / file_obj.name
                save_path.write_bytes(file_obj.getvalue())
                recipe = load_recipe(save_path)
                basic_chunks = chunk_basic(recipe)
                struct_chunks = chunk_structured(recipe)

                for name, chunks in (
                    (COLLECTION_BASIC, basic_chunks),
                    (COLLECTION_STRUCTURED, struct_chunks),
                ):
                    try:
                        coll = get_collection(name)
                    except Exception:
                        coll = reset_collection(name)
                    upsert_chunks(coll, chunks)
                count += 1
            st.success(f"Successfully ingested {count} file(s) into ChromaDB!")
            st.cache_data.clear()

    st.divider()
    st.header("Retrieval settings")
    strategy = st.radio("Chunking strategy", ["structured", "basic"], index=0)
    k = st.slider("Top-K", 1, 10, 5)
    tag = st.selectbox("Filter by dietary_tags", ["(none)"] + all_tags())
    threshold = st.slider("Refusal threshold (cosine similarity)", 0.0, 1.0,
                          REFUSAL_THRESHOLD, 0.01)
    st.caption("The threshold gate refuses before spending an LLM call when the "
               "best chunk is too far away.")


question = st.text_input(
    "Question",
    value="How much green curry paste do I need?",
    placeholder="Ask about the 6 indexed recipe cards",
)

if question:
    where = None if tag == "(none)" else dietary_filter(tag)
    try:
        hits = search(question, strategy=strategy, k=k, where=where)
    except Exception as exc:
        st.error(f"Retrieval failed — has the index been built? `python scripts/ingest.py`\n\n{exc}")
        st.stop()

    st.subheader(f"Retrieved chunks ({len(hits)})")
    if where:
        st.caption(f"Chroma filter applied: `{where}`")
    if not hits:
        st.warning("Nothing matched that filter.")

    st.dataframe(
        [
            {
                "rank": h["rank"],
                "chunk_id": h["chunk_id"],
                "recipe_id": h["metadata"]["recipe_id"],
                "recipe": h["metadata"]["recipe_title"],
                "section": h["metadata"]["section"],
                "cuisine": h["metadata"]["cuisine"],
                "dietary_tags": h["metadata"]["dietary_tags"],
                "score": h["score"],
            }
            for h in hits
        ],
        use_container_width=True,
        hide_index=True,
    )

    for h in hits:
        with st.expander(f"{h['rank']}. {h['chunk_id']} — score {h['score']:.4f}"):
            st.code(h["text"])

    if st.button("Generate grounded answer", type="primary"):
        with st.spinner("Asking the model…"):
            result = answer_question(question, hits, threshold=threshold)

        if result["error"]:
            st.error(result["error"])
        elif result["refused"]:
            st.warning(f"Refused (gate: {result['refused_by']})")
            st.write(result["answer"])
        else:
            st.success("Answer")
            st.write(result["answer"])
            c = result["citations"]
            if c:
                st.caption(
                    f"Citations {c['cited']} — valid: {c['valid']}; "
                    f"unknown chunk_ids: {c['unknown_chunk_ids'] or 'none'}; "
                    f"recipe_id mismatches: {c['recipe_id_mismatches'] or 'none'}"
                )
