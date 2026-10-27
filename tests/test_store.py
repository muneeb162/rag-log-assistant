import numpy as np

from rag_assistant.ingest import load_corpus
from rag_assistant.store import HashingEmbedder, VectorIndex


def test_embeddings_are_normalised():
    vectors = HashingEmbedder().embed(["connection pool exhausted", "certificate expired"])
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)


def test_empty_index_returns_nothing():
    assert VectorIndex(HashingEmbedder()).search("anything") == []


def test_retrieval_finds_the_right_document(kb_path):
    index = VectorIndex(HashingEmbedder())
    index.add(load_corpus(kb_path))
    hits = index.search("FATAL: sorry, too many clients already", k=3)
    assert hits
    assert hits[0][0].doc_id == "postgres-connection-pool"


def test_results_are_ordered_by_score(kb_path):
    index = VectorIndex(HashingEmbedder())
    index.add(load_corpus(kb_path))
    scores = [s for _, s in index.search("certificate verify failed x509", k=4)]
    assert scores == sorted(scores, reverse=True)


def test_min_score_filters_weak_matches(kb_path):
    index = VectorIndex(HashingEmbedder())
    index.add(load_corpus(kb_path))
    assert index.search("zzzz unrelated gibberish qqqq", k=4, min_score=0.99) == []
