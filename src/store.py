"""Thin wrapper over ChromaDB: build collections and query them."""
from typing import Dict, List, Optional

import chromadb
from chromadb.utils import embedding_functions

from chunking import Chunk
from config import CHROMA_DIR

_EF = embedding_functions.DefaultEmbeddingFunction()


def client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _create(c, name: str):
    # Older Chroma takes the space as metadata; newer builds reject the key.
    # Fall back to the default space rather than failing the whole run.
    try:
        return c.create_collection(
            name=name, embedding_function=_EF, metadata={"hnsw:space": "cosine"}
        )
    except Exception:
        return c.create_collection(name=name, embedding_function=_EF)


def reset_collection(name: str):
    """Drop and recreate a collection so re-ingesting is never additive."""
    c = client()
    try:
        c.delete_collection(name)
    except Exception:
        pass
    return _create(c, name)


def get_collection(name: str):
    return client().get_collection(name=name, embedding_function=_EF)


def ephemeral_collection(chunks: List[Chunk], name: str = "sweep"):
    """In-memory collection for parameter sweeps, so the persisted index is
    never touched by experiments."""
    c = chromadb.EphemeralClient()
    coll = _create(c, name)
    add_chunks(coll, chunks)
    return coll


def add_chunks(collection, chunks: List[Chunk], batch: int = 100):
    for i in range(0, len(chunks), batch):
        part = chunks[i : i + batch]
        collection.add(
            ids=[c.chunk_id for c in part],
            documents=[c.text for c in part],
            metadatas=[c.metadata for c in part],
        )


def query(collection, question: str, k: int = 5, where: Optional[Dict] = None):
    """Return top-k hits as dicts with a cosine similarity score."""
    res = collection.query(
        query_texts=[question],
        n_results=k,
        where=where or None,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for rank, (cid, doc, meta, dist) in enumerate(
        zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]),
        start=1,
    ):
        hits.append(
            {
                "rank": rank,
                "chunk_id": cid,
                "text": doc,
                "metadata": meta,
                "distance": round(float(dist), 4),
                "score": round(1.0 - float(dist), 4),
            }
        )
    return hits
