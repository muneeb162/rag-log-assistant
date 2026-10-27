"""Load a markdown knowledge base and split it into retrievable chunks.

Design note: chunking is heading-aware before it is size-aware. Runbooks and
incident notes are written under headings, and a heading is usually the single
most useful piece of context for deciding whether a chunk answers a question.
Splitting purely on character count cut across that structure and measurably
hurt retrieval precision, so headings are the primary boundary and the size
limit only applies within a section.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class Chunk:
    """One retrievable unit of the knowledge base."""

    doc_id: str
    chunk_id: str
    heading: str
    text: str

    @property
    def citation(self) -> str:
        return f"{self.doc_id}#{self.chunk_id}"

    def for_embedding(self) -> str:
        """Heading is prepended so it contributes to the embedding, not just display."""
        return f"{self.heading}\n\n{self.text}" if self.heading else self.text


def _split_oversized(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split a single section that is longer than max_chars, on paragraph bounds."""
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    buf = ""
    for para in text.split("\n\n"):
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= max_chars or not buf:
            buf = candidate
        else:
            parts.append(buf)
            tail = buf[-overlap:] if overlap else ""
            buf = f"{tail}\n\n{para}".strip() if tail else para
    if buf:
        parts.append(buf)
    return parts


def split_markdown(
    text: str, doc_id: str, max_chars: int = 900, overlap: int = 150
) -> list[Chunk]:
    """Split one markdown document into heading-scoped chunks."""
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    body: list[str] = []

    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            if body or heading:
                sections.append((heading, body))
            heading = match.group(2).strip()
            body = []
        else:
            body.append(line)
    if body or heading:
        sections.append((heading, body))

    chunks: list[Chunk] = []
    for head, lines in sections:
        section_text = "\n".join(lines).strip()
        if not section_text:
            continue
        for part in _split_oversized(section_text, max_chars, overlap):
            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    chunk_id=f"c{len(chunks):02d}",
                    heading=head,
                    text=part.strip(),
                )
            )
    return chunks


def load_corpus(root: str | Path, max_chars: int = 900, overlap: int = 150) -> list[Chunk]:
    """Load and chunk every markdown file under root, sorted for reproducibility."""
    root = Path(root)
    chunks: list[Chunk] = []
    for path in sorted(root.rglob("*.md")):
        chunks.extend(
            split_markdown(
                path.read_text(encoding="utf-8"),
                doc_id=path.stem,
                max_chars=max_chars,
                overlap=overlap,
            )
        )
    return chunks
