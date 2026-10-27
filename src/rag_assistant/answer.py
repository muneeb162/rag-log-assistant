"""Retrieve, then generate — with citation treated as a hard requirement.

Design note: the single most important decision in this system is that an
answer without a source is treated as a failure, not a degraded success. An
engineer reading an uncited answer mid-incident has no way to check it, which
makes it worse than no answer at all. So the prompt forbids outside knowledge,
the retrieval floor is enforced before the model is called at all, and the
caller gets the sources back alongside the text.
"""
from __future__ import annotations

from dataclasses import dataclass

from .ingest import Chunk
from .store import VectorIndex

SYSTEM_PROMPT = """You are a troubleshooting assistant for an engineering team.

Rules, in order of priority:
1. Answer ONLY from the numbered context passages given to you. Never use
   outside knowledge, even if you are confident it is correct.
2. Cite the source of every factual claim inline, in the form [doc#chunk],
   using the exact identifiers shown with each passage.
3. If the context does not contain enough to answer, say so plainly and name
   what is missing. Do not guess, and do not pad the answer.
4. Be short. An engineer is reading this during an incident.
"""

NO_CONTEXT_MESSAGE = (
    "I could not find anything in the knowledge base that matches this log. "
    "Nothing was sent to the model, because an answer with no source behind it "
    "is not useful during an incident."
)


@dataclass(frozen=True)
class Answer:
    text: str
    sources: list[Chunk]
    grounded: bool


def build_context(hits: list[tuple[Chunk, float]]) -> str:
    blocks = []
    for chunk, score in hits:
        header = f"[{chunk.citation}] {chunk.heading}".rstrip()
        blocks.append(f"{header} (similarity {score:.3f})\n{chunk.text}")
    return "\n\n---\n\n".join(blocks)


def build_messages(error_log: str, hits: list[tuple[Chunk, float]]) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Context passages:\n\n{build_context(hits)}\n\n"
                f"---\n\nError log from the engineer:\n\n{error_log.strip()}\n\n"
                "What is going wrong, and what should they check first?"
            ),
        },
    ]


def answer(
    error_log: str,
    index: VectorIndex,
    client=None,
    k: int = 4,
    min_score: float = 0.05,
    model: str = "gpt-4o-mini",
) -> Answer:
    """Answer an error log from the knowledge base, or decline to answer."""
    hits = index.search(error_log, k=k, min_score=min_score)
    if not hits:
        return Answer(text=NO_CONTEXT_MESSAGE, sources=[], grounded=False)

    if client is None:
        # Retrieval-only mode: no API key needed, useful for inspecting what
        # the model would have been given before paying to generate.
        listing = "\n".join(f"  [{c.citation}] {c.heading} ({s:.3f})" for c, s in hits)
        return Answer(
            text=f"Retrieval-only mode. Passages that would be sent to the model:\n{listing}",
            sources=[c for c, _ in hits],
            grounded=True,
        )

    response = client.chat.completions.create(
        model=model,
        messages=build_messages(error_log, hits),
        temperature=0,
    )
    return Answer(
        text=response.choices[0].message.content.strip(),
        sources=[c for c, _ in hits],
        grounded=True,
    )
