# RAG Log Assistant

An engineer pastes an unstructured error log; the assistant returns an answer
drawn only from a knowledge base of runbooks and incident notes, with a citation
against every claim.

## What this repository is, and is not

I built a system of this design in production at TPS Pakistan, where it was used
by the engineering team on live incidents. **That code belongs to my employer and
is not published here.** This repository is a clean reimplementation I wrote from
scratch, against a small synthetic knowledge base of my own, so that the design
decisions are inspectable without exposing anything proprietary.

So: the architecture and the reasoning are the real thing. The knowledge base is
invented, and the scale is a demonstration rather than a production load.

## The design decision that matters

**An answer without a source is a failure, not a degraded success.**

An engineer reading an uncited answer in the middle of an incident has no way to
check it, which makes it actively worse than no answer at all. Three things in
this codebase follow from that:

1. The retrieval floor is enforced *before* the model is called. If nothing in
   the knowledge base clears the similarity threshold, the assistant says so and
   the model is never invoked. See `answer.py` and the test
   `test_model_is_not_called_when_retrieval_is_empty`.
2. The system prompt forbids outside knowledge and requires inline `[doc#chunk]`
   citations using the exact identifiers attached to each passage.
3. `Answer` carries the source chunks back to the caller, so the interface can
   render them rather than trusting the model to have cited honestly.

## Other decisions worth explaining

**Chunking is heading-aware before it is size-aware.** Runbooks are written under
headings, and the heading is usually the single most useful signal for deciding
whether a passage answers a question. Splitting purely on character count cut
across that structure and hurt retrieval precision. Headings are the primary
boundary; the size limit only applies within a section. The heading is also
prepended to the text before embedding, so it contributes to the vector rather
than only to the display.

**The embedder is injected, not imported.** `VectorIndex` takes anything matching
the `Embedder` protocol. That means the retrieval logic and the prompt
construction are tested with a deterministic offline embedder — no API key, no
network, no cost, and the test suite runs in CI for free. Swapping embedding
models is a one-line change.

**Search is flat cosine similarity, deliberately.** The knowledge base this was
built for was a few thousand chunks. An approximate index would have added an
operational dependency to save single-digit milliseconds.

## Layout

```
src/rag_assistant/
    ingest.py   heading-aware chunking
    store.py    embedders + flat cosine index
    answer.py   retrieve-then-generate, citation enforced
    cli.py      stdin -> cited answer
data/kb/        synthetic runbooks (invented, not from any employer)
tests/          19 tests, all offline
```

## Running it

```bash
pip install -r requirements-dev.txt
pytest -q                                    # no API key needed

# retrieval only — see what would be sent to the model
PYTHONPATH=src python -m rag_assistant.cli --retrieval-only < examples/sample.log

# full answer
export OPENAI_API_KEY=sk-...
PYTHONPATH=src python -m rag_assistant.cli < examples/sample.log
```

Without `OPENAI_API_KEY` the CLI falls back to retrieval-only mode rather than
failing, because inspecting retrieval is the useful half when you are debugging
why an answer came out wrong.

## What I would do next

Evaluation is the honest gap. My production version was evaluated case by case
by the engineers using it, not against a held-out set, and this repository
inherits that limitation. The next thing worth building is a small labelled set
of log-to-document pairs and a recall@k measurement, so chunk size, overlap and
the similarity floor can be tuned against a number rather than an impression.

## Licence

MIT.
