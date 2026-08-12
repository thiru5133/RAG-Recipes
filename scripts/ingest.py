"""Index the 6 supplied recipe cards under both chunking strategies.

Both collections are dropped and rebuilt from the same 6 files on every run, so
the corpus is never extended and the two strategies always see identical input.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chunking import chunk_basic, chunk_structured  # noqa: E402
from config import COLLECTION_BASIC, COLLECTION_STRUCTURED  # noqa: E402
from loader import load_corpus  # noqa: E402
from store import add_chunks, reset_collection  # noqa: E402

REQUIRED_METADATA = ["source_file", "recipe_id", "cuisine", "dietary_tags"]


def build():
    recipes = load_corpus()
    if len(recipes) != 6:
        raise SystemExit(f"expected exactly 6 recipe cards, found {len(recipes)}")

    basic = [c for r in recipes for c in chunk_basic(r)]
    structured = [c for r in recipes for c in chunk_structured(r)]

    for name, chunks in (("basic", basic), ("structured", structured)):
        for c in chunks:
            missing = [f for f in REQUIRED_METADATA if not c.metadata.get(f)]
            if missing:
                raise SystemExit(f"{name} chunk {c.chunk_id} missing metadata: {missing}")

    return recipes, basic, structured


def main():
    recipes, basic, structured = build()
    print(f"Loaded {len(recipes)} recipe cards: {', '.join(r.recipe_id for r in recipes)}")

    for collection_name, chunks in (
        (COLLECTION_BASIC, basic),
        (COLLECTION_STRUCTURED, structured),
    ):
        coll = reset_collection(collection_name)
        add_chunks(coll, chunks)
        print(f"{collection_name}: {len(chunks)} chunks indexed "
              f"(avg {sum(len(c.text) for c in chunks) // len(chunks)} chars)")

    print(f"All chunks carry: {', '.join(REQUIRED_METADATA)}")
    return recipes, basic, structured


if __name__ == "__main__":
    main()
