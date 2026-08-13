import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chunking import chunk_basic, chunk_structured  # noqa: E402
from config import COLLECTION_BASIC, COLLECTION_STRUCTURED, RECIPE_DIR  # noqa: E402
from loader import load_corpus, load_corpus_from_sources  # noqa: E402
from store import add_chunks, get_collection, reset_collection, upsert_chunks  # noqa: E402

REQUIRED_METADATA = ["source_file", "recipe_id", "cuisine"]


def build(recipes=None):
    if recipes is None:
        recipes = load_corpus()

    basic = [c for r in recipes for c in chunk_basic(r)]
    structured = [c for r in recipes for c in chunk_structured(r)]

    for name, chunks in (("basic", basic), ("structured", structured)):
        for c in chunks:
            missing = [f for f in REQUIRED_METADATA if not c.metadata.get(f)]
            if missing:
                raise SystemExit(f"{name} chunk {c.chunk_id} missing metadata: {missing}")

    return recipes, basic, structured


def parse_args():
    parser = argparse.ArgumentParser(
        description="Index recipe cards under basic and structured chunking strategies."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Optional list of markdown recipe card files to ingest.",
    )
    parser.add_argument(
        "--dir",
        "-d",
        type=str,
        default=None,
        help="Directory containing markdown recipe cards.",
    )
    parser.add_argument(
        "--glob",
        "-g",
        type=str,
        default=None,
        help="Glob pattern to search for markdown recipe cards (e.g. 'custom/**/*.md').",
    )
    parser.add_argument(
        "--append",
        "-a",
        action="store_true",
        help="Append or update chunks without resetting existing collections.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    sources = []
    if args.files:
        sources.extend(args.files)
    if args.dir:
        sources.append(args.dir)
    if args.glob:
        sources.append(args.glob)

    if not sources:
        sources = [RECIPE_DIR]

    recipes = load_corpus_from_sources(sources)
    if not recipes:
        print("No matching recipe files found for ingestion.")
        return [], [], []

    recipes, basic, structured = build(recipes)
    print(f"Loaded {len(recipes)} recipe cards: {', '.join(r.recipe_id for r in recipes)}")

    for collection_name, chunks in (
        (COLLECTION_BASIC, basic),
        (COLLECTION_STRUCTURED, structured),
    ):
        if args.append:
            try:
                coll = get_collection(collection_name)
            except Exception:
                coll = reset_collection(collection_name)
            upsert_chunks(coll, chunks)
            mode_str = "appended/updated"
        else:
            coll = reset_collection(collection_name)
            add_chunks(coll, chunks)
            mode_str = "indexed (reset)"

        print(f"{collection_name}: {len(chunks)} chunks {mode_str} "
              f"(avg {sum(len(c.text) for c in chunks) // len(chunks)} chars)")

    print(f"All chunks carry required metadata fields: {', '.join(REQUIRED_METADATA)}")
    return recipes, basic, structured


if __name__ == "__main__":
    main()

