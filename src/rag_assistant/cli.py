"""Paste an error log on stdin, get a source-cited answer back.

    python -m rag_assistant.cli < some_error.log
    python -m rag_assistant.cli --retrieval-only < some_error.log
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .answer import answer
from .ingest import load_corpus
from .store import HashingEmbedder, OpenAIEmbedder, VectorIndex

DEFAULT_KB = Path(__file__).resolve().parents[2] / "data" / "kb"


def build_index(kb_path: Path, offline: bool) -> VectorIndex:
    if offline:
        embedder = HashingEmbedder()
        client = None
    else:
        from openai import OpenAI  # imported lazily so offline mode needs no dependency

        client = OpenAI()
        embedder = OpenAIEmbedder(client)
    index = VectorIndex(embedder)
    index.add(load_corpus(kb_path))
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kb", type=Path, default=DEFAULT_KB, help="knowledge base directory")
    parser.add_argument("--k", type=int, default=4, help="passages to retrieve")
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="show the retrieved passages without calling the model",
    )
    args = parser.parse_args(argv)

    error_log = sys.stdin.read()
    if not error_log.strip():
        parser.error("no error log on stdin")

    offline = args.retrieval_only or not os.environ.get("OPENAI_API_KEY")
    if offline and not args.retrieval_only:
        print("OPENAI_API_KEY is not set — falling back to retrieval-only mode.\n", file=sys.stderr)

    index = build_index(args.kb, offline=offline)
    client = None
    if not offline:
        from openai import OpenAI

        client = OpenAI()

    result = answer(error_log, index, client=client, k=args.k)
    print(result.text)
    if result.sources:
        print("\nSources:")
        for chunk in result.sources:
            print(f"  [{chunk.citation}] {chunk.heading}")
    return 0 if result.grounded else 1


if __name__ == "__main__":
    raise SystemExit(main())
