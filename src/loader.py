"""Parse recipe cards into a structured form.

Every card is markdown with YAML-ish front matter, one H1 title and a fixed set of
H2 sections. Sections are classified as table or prose so the chunkers can treat
them differently.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from config import RECIPE_DIR

# Canonical short names, so evaluation labels do not depend on exact headings.
SECTION_ALIASES = {
    "overview": "Overview",
    "ingredients": "Ingredients",
    "method": "Method",
    "notes": "Notes",
    "nutrition": "Nutrition",
}


def canonical_section(heading: str) -> str:
    low = heading.strip().lower()
    for prefix, name in SECTION_ALIASES.items():
        if low.startswith(prefix):
            return name
    return heading.strip()


@dataclass
class Section:
    heading: str
    name: str
    kind: str  # "table" or "prose"
    lines: List[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()

    @property
    def table_header(self) -> List[str]:
        """The header row plus its separator, if this section holds a table."""
        rows = [l for l in self.lines if l.strip().startswith("|")]
        return rows[:2]

    @property
    def table_rows(self) -> List[str]:
        rows = [l for l in self.lines if l.strip().startswith("|")]
        return rows[2:]


@dataclass
class Recipe:
    recipe_id: str
    title: str
    cuisine: str
    dietary_tags: List[str]
    servings: str
    source_file: str
    sections: List[Section]

    @property
    def flat_text(self) -> str:
        return self.flat_with_spans()[0]

    def flat_with_spans(self):
        """Flattened card plus (start, end, section_name) character spans.

        The spans let blind fixed-size chunks be labelled with the sections they
        happen to straddle, so strategy A can be scored on the same basis as B.
        """
        text = f"# {self.title}"
        spans = []
        for s in self.sections:
            block = f"\n\n## {s.heading}\n{s.text}"
            start = len(text)
            text += block
            spans.append((start, len(text), s.name))
        return text, spans


def _parse_front_matter(lines: List[str]):
    meta, body_start = {}, 0
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                body_start = i + 1
                break
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
    return meta, body_start


def load_recipe(path: Path) -> Recipe:
    lines = path.read_text(encoding="utf-8").splitlines()
    meta, start = _parse_front_matter(lines)

    title = ""
    sections: List[Section] = []
    current = None

    for line in lines[start:]:
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            heading = line[3:].strip()
            current = Section(heading=heading, name=canonical_section(heading), kind="prose")
            sections.append(current)
        elif current is not None:
            current.lines.append(line)

    for s in sections:
        # A section counts as a table if most of its non-blank lines are table rows.
        rows = [l for l in s.lines if l.strip().startswith("|")]
        body = [l for l in s.lines if l.strip()]
        s.kind = "table" if body and len(rows) >= max(3, 0.6 * len(body)) else "prose"

    tags = [t.strip() for t in meta.get("dietary_tags", "").split(",") if t.strip()]
    return Recipe(
        recipe_id=meta.get("recipe_id", path.stem),
        title=title,
        cuisine=meta.get("cuisine", ""),
        dietary_tags=tags,
        servings=meta.get("servings", ""),
        source_file=path.name,
        sections=sections,
    )


def load_corpus(directory: Path = RECIPE_DIR) -> List[Recipe]:
    """Load exactly the supplied recipe cards. Nothing else is ever indexed."""
    paths = sorted(directory.glob("*.md"))
    return [load_recipe(p) for p in paths]
