"""Embedding and in-memory vector search.

Design note: the embedder is injected rather than imported. That keeps the
index testable with no network access and no API key, which is why the test
suite runs in CI for free, and it means swapping embedding models is a
one-line change rather than a refactor.
"""
from __future__ import annotations

import hashlib
from typing import Protocol, Sequence

import numpy as np

from .ingest import Chunk


class Embedder(Protocol):
    """Anything that turns text into fixed-length vectors."""

    def embed(self, texts: Sequence[str]) -> np.ndarray: ...


class HashingEmbedder:
    """Deterministic offline embedder: hashed token counts, L2-normalised.

    Not competitive with a real model, but it is free, reproducible and has no
    network dependency, so the retrieval logic can be tested on its own.
    """

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def _vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for token in text.lower().split():
            token = token.strip(".,:;()[]{}\"'`")
            if not token:
                continue
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            vec[int.from_bytes(digest, "big") % self.dim] += 1.0
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm else vec

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        return np.vstack([self._vector(t) for t in texts])


class OpenAIEmbedder:
    """Embeddings from the OpenAI API. Requires OPENAI_API_KEY."""

    def __init__(self, client, model: str = "text-embedding-3-small") -> None:
        self.client = client
        self.model = model

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        response = self.client.embeddings.create(model=self.model, input=list(texts))
        vectors = np.array([item.embedding for item in response.data], dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


class VectorIndex:
    """Flat cosine-similarity index.

    Flat search is deliberate. The knowledge base this was built for was a few
    thousand chunks; an approximate index would have added an operational
    dependency to save single-digit milliseconds.
    """

    def __init__(self, embedder: Embedder) -> None:
        self.embedder = embedder
        self.chunks: list[Chunk] = []
        self._matrix: np.ndarray | None = None

    def add(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return
        vectors = self.embedder.embed([c.for_embedding() for c in chunks])
        self.chunks.extend(chunks)
        self._matrix = vectors if self._matrix is None else np.vstack([self._matrix, vectors])

    def search(self, query: str, k: int = 4, min_score: float = 0.0):
        """Return the top k (chunk, score) pairs above min_score, best first."""
        if self._matrix is None or not self.chunks:
            return []
        query_vector = self.embedder.embed([query])[0]
        scores = self._matrix @ query_vector
        order = np.argsort(-scores)[:k]
        return [
            (self.chunks[i], float(scores[i]))
            for i in order
            if float(scores[i]) > min_score
        ]
