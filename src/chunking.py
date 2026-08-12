"""Chunking strategies.

Strategy A (basic): fixed-size character windows over the flattened document,
split blind at whitespace with a fixed overlap. Headings, tables and row
boundaries are invisible to it.

Strategy B (structure-aware): split on section boundaries; keep every ingredient
row attached to its table header and to the recipe title, and never cut a row or
a numbered step in half.
"""
import re
from dataclasses import dataclass
from typing import Dict, List

from config import (
    BASIC_CHUNK_SIZE,
    BASIC_OVERLAP,
    STRUCT_MAX_CHARS,
    STRUCT_OVERLAP_ROWS,
    STRUCT_ROWS_PER_CHUNK,
)
from loader import Recipe, Section

STEP_RE = re.compile(r"^\s*\d+\.\s")


@dataclass
class Chunk:
    chunk_id: str
    text: str
    metadata: Dict[str, object]


def _tag_key(tag: str) -> str:
    return "tag_" + re.sub(r"[^a-z0-9]+", "_", tag.strip().lower())


def build_metadata(
    recipe: Recipe,
    section: str,
    sections_covered: List[str],
    chunk_type: str,
    strategy: str,
) -> Dict[str, object]:
    """Metadata carried by every chunk in both collections.

    The four required fields are source_file, recipe_id, cuisine and
    dietary_tags. Chroma only stores scalars, so dietary_tags is a display
    string and each tag also becomes its own boolean for `where` filtering.
    """
    meta: Dict[str, object] = {
        "source_file": recipe.source_file,
        "recipe_id": recipe.recipe_id,
        "cuisine": recipe.cuisine,
        "dietary_tags": ", ".join(recipe.dietary_tags),
        "recipe_title": recipe.title,
        "section": section,
        "sections_covered": "|" + "|".join(sections_covered) + "|",
        "chunk_type": chunk_type,
        "strategy": strategy,
    }
    for tag in recipe.dietary_tags:
        meta[_tag_key(tag)] = True
    return meta


# --------------------------------------------------------------------------
# Strategy A: basic
# --------------------------------------------------------------------------

def _windows(text: str, size: int, overlap: int):
    """Yield (start, end) character windows, nudged to the nearest whitespace."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than chunk size")
    spans, start, n = [], 0, len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            cut = text.rfind(" ", start + int(size * 0.5), end)
            if cut != -1:
                end = cut
        spans.append((start, end))
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return spans


def chunk_basic(
    recipe: Recipe,
    chunk_size: int = BASIC_CHUNK_SIZE,
    overlap: int = BASIC_OVERLAP,
) -> List[Chunk]:
    """Naive fixed-size chunking: no awareness of headings, tables or rows."""
    text, spans = recipe.flat_with_spans()
    chunks = []
    for i, (start, end) in enumerate(_windows(text, chunk_size, overlap)):
        body = text[start:end].strip()
        if not body:
            continue
        # Which sections does this blind window happen to straddle?
        covered = [(name, min(end, e) - max(start, s))
                   for s, e, name in spans if s < end and e > start]
        names = [n for n, _ in covered]
        primary = max(covered, key=lambda x: x[1])[0] if covered else "Title"
        chunks.append(
            Chunk(
                chunk_id=f"{recipe.recipe_id}-A{i:02d}",
                text=body,
                metadata=build_metadata(recipe, primary, names, "mixed", "basic"),
            )
        )
    return chunks


# --------------------------------------------------------------------------
# Strategy B: structure-aware
# --------------------------------------------------------------------------

def _breadcrumb(recipe: Recipe, section: Section) -> str:
    return (
        f"Recipe: {recipe.title} ({recipe.recipe_id}) | Cuisine: {recipe.cuisine} "
        f"| Dietary: {', '.join(recipe.dietary_tags)} | Section: {section.heading}"
    )


def _prose_units(section: Section) -> List[str]:
    """Split prose into indivisible units: numbered steps, or paragraphs."""
    units, current = [], []
    for line in section.lines:
        stripped = line.strip()
        starts_unit = bool(STEP_RE.match(line)) or (not stripped and current)
        if starts_unit and current:
            block = "\n".join(current).strip()
            if block:
                units.append(block)
            current = []
        if stripped:
            current.append(line)
    block = "\n".join(current).strip()
    if block:
        units.append(block)
    return units


def chunk_structured(
    recipe: Recipe,
    max_chars: int = STRUCT_MAX_CHARS,
    rows_per_chunk: int = STRUCT_ROWS_PER_CHUNK,
    overlap_rows: int = STRUCT_OVERLAP_ROWS,
) -> List[Chunk]:
    """Section-aware chunking that keeps table rows with their header and title."""
    chunks: List[Chunk] = []
    idx = 0

    for section in recipe.sections:
        crumb = _breadcrumb(recipe, section)

        if section.kind == "table":
            header = section.table_header  # header row + separator row
            rows = section.table_rows
            step = max(1, rows_per_chunk - overlap_rows)
            for start in range(0, len(rows), step):
                group = rows[start : start + rows_per_chunk]
                if not group:
                    continue
                # Title, section heading and table header are re-emitted with
                # every row group, so a row is never orphaned from its context.
                text = "\n".join([crumb, f"## {section.heading}"] + header + group)
                chunks.append(
                    Chunk(
                        chunk_id=f"{recipe.recipe_id}-B{idx:02d}",
                        text=text,
                        metadata=build_metadata(
                            recipe, section.name, [section.name], "table", "structured"
                        ),
                    )
                )
                idx += 1
                if start + rows_per_chunk >= len(rows):
                    break
        else:
            # Pack whole units up to max_chars; a unit is never split.
            buffer: List[str] = []
            size = 0
            for unit in _prose_units(section):
                if buffer and size + len(unit) > max_chars:
                    text = "\n".join([crumb, f"## {section.heading}"] + buffer)
                    chunks.append(
                        Chunk(
                            chunk_id=f"{recipe.recipe_id}-B{idx:02d}",
                            text=text,
                            metadata=build_metadata(
                                recipe, section.name, [section.name], "prose", "structured"
                            ),
                        )
                    )
                    idx += 1
                    buffer, size = [], 0
                buffer.append(unit)
                size += len(unit)
            if buffer:
                text = "\n".join([crumb, f"## {section.heading}"] + buffer)
                chunks.append(
                    Chunk(
                        chunk_id=f"{recipe.recipe_id}-B{idx:02d}",
                        text=text,
                        metadata=build_metadata(
                            recipe, section.name, [section.name], "prose", "structured"
                        ),
                    )
                )
                idx += 1

    return chunks
