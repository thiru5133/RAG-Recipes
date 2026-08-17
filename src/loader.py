"""Parse recipe cards into a structured form.

Every card is markdown with YAML-ish front matter, one H1 title and a fixed set of
H2 sections. Sections are classified as table or prose so the chunkers can treat
them differently.
"""
import glob
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

from config import RECIPE_DIR

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".doc", ".json", ".csv", ".tsv", ".yaml", ".yml", ".html", ".xml"}

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


def extract_text_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in [".md", ".txt", ".json", ".csv", ".tsv", ".yaml", ".yml", ".html", ".xml"]:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return path.read_text(encoding="latin-1", errors="ignore")
    elif ext == ".pdf":
        text_parts = []
        try:
            import pypdf
            with open(path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_parts.append(extracted)
        except Exception as exc:
            print(f"pypdf extraction error: {exc}")

        if not text_parts:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(str(path))
                for page in doc:
                    text_parts.append(page.get_text())
            except Exception:
                pass

        return "\n\n".join(text_parts).strip() if text_parts else f"# {path.stem}\n\n[PDF document text content]"
    elif ext in [".docx", ".doc"]:
        try:
            import docx
            doc = docx.Document(str(path))
            return "\n\n".join([p.text for p in doc.paragraphs if p.text]).strip()
        except Exception:
            return f"# {path.stem}\n\n[Word document text content]"
    else:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""


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
    raw_text = extract_text_from_file(path)
    lines = raw_text.splitlines()
    meta, start = _parse_front_matter(lines)

    title = ""
    sections: List[Section] = []
    current = None

    for line in lines[start:]:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## "):
            heading = line[3:].strip()
            current = Section(heading=heading, name=canonical_section(heading), kind="prose")
            sections.append(current)
        elif current is not None:
            current.lines.append(line)
        elif line.strip():
            if not sections:
                current = Section(heading="Overview", name="Overview", kind="prose")
                sections.append(current)
            current.lines.append(line)

    if not sections:
        sections = [Section(heading="Overview", name="Overview", kind="prose", lines=lines)]

    for s in sections:
        rows = [l for l in s.lines if l.strip().startswith("|")]
        body = [l for l in s.lines if l.strip()]
        s.kind = "table" if body and len(rows) >= max(3, 0.6 * len(body)) else "prose"

    tags = [t.strip() for t in meta.get("dietary_tags", "").split(",") if t.strip()]
    if not title:
        title = meta.get("title", path.stem.replace("-", " ").replace("_", " ").title())
    recipe_id = meta.get("recipe_id", re.sub(r"[^A-Za-z0-9_-]", "_", path.stem))

    return Recipe(
        recipe_id=recipe_id,
        title=title,
        cuisine=meta.get("cuisine", "General"),
        dietary_tags=tags,
        servings=meta.get("servings", ""),
        source_file=path.name,
        sections=sections,
    )


def load_corpus(directory: Path = RECIPE_DIR) -> List[Recipe]:
    """Load exactly the supplied recipe cards. Nothing else is ever indexed."""
    paths = sorted(directory.glob("*.md"))
    return [load_recipe(p) for p in paths]


def load_corpus_from_sources(sources: List[Union[str, Path]]) -> List[Recipe]:
    """Load recipe cards from a list of file paths, directory paths, or glob patterns."""
    collected_paths: List[Path] = []

    for src in sources:
        p = Path(src)
        if p.is_file():
            collected_paths.append(p)
        elif p.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                collected_paths.extend(sorted(p.glob(f"*{ext}")))
        else:
            # Try glob pattern expansion
            str_src = str(src)
            matched = [Path(f) for f in glob.glob(str_src, recursive=True) if Path(f).is_file()]
            if matched:
                collected_paths.extend(sorted(matched))
            elif "*" not in str_src and "?" not in str_src:
                print(f"Warning: source '{src}' is not a valid file or directory.")

    # Deduplicate while preserving order
    seen = set()
    unique_paths = []
    for path in collected_paths:
        abs_p = path.resolve()
        if abs_p not in seen and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            seen.add(abs_p)
            unique_paths.append(path)

    return [load_recipe(p) for p in unique_paths]


