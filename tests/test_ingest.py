from rag_assistant.ingest import Chunk, load_corpus, split_markdown

DOC = """# Title

Intro paragraph.

## Symptoms
Something is on fire.

## Resolution
Put it out.
"""


def test_splits_on_headings():
    chunks = split_markdown(DOC, doc_id="demo")
    headings = [c.heading for c in chunks]
    assert "Symptoms" in headings
    assert "Resolution" in headings


def test_chunk_ids_are_unique_and_stable():
    chunks = split_markdown(DOC, doc_id="demo")
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert split_markdown(DOC, doc_id="demo") == chunks


def test_citation_format():
    chunk = Chunk(doc_id="demo", chunk_id="c01", heading="Symptoms", text="x")
    assert chunk.citation == "demo#c01"


def test_heading_is_embedded_with_the_body():
    chunk = Chunk(doc_id="d", chunk_id="c00", heading="Symptoms", text="body")
    assert chunk.for_embedding().startswith("Symptoms")


def test_empty_sections_are_dropped():
    chunks = split_markdown("# Only a heading\n\n", doc_id="demo")
    assert chunks == []


def test_oversized_section_is_split():
    long_body = "# H\n\n" + "\n\n".join(["paragraph " * 40] * 6)
    chunks = split_markdown(long_body, doc_id="demo", max_chars=400)
    assert len(chunks) > 1
    assert all(len(c.text) <= 900 for c in chunks)


def test_load_corpus_reads_the_knowledge_base(kb_path):
    chunks = load_corpus(kb_path)
    assert len(chunks) > 10
    assert {c.doc_id for c in chunks} >= {"postgres-connection-pool", "tls-certificate-expiry"}
