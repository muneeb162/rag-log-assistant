from rag_assistant.answer import NO_CONTEXT_MESSAGE, answer, build_messages
from rag_assistant.ingest import Chunk
from rag_assistant.store import HashingEmbedder, VectorIndex


class FakeClient:
    """Records the prompt it was given and returns a fixed answer."""

    def __init__(self):
        self.captured = None
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, model, messages, temperature):
        self.captured = messages

        class _Msg:
            content = "Check the pool. [postgres-connection-pool#c01]"

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]

        return _Resp()


def _index(kb_path):
    from rag_assistant.ingest import load_corpus

    index = VectorIndex(HashingEmbedder())
    index.add(load_corpus(kb_path))
    return index


def test_declines_when_nothing_is_retrieved():
    empty = VectorIndex(HashingEmbedder())
    result = answer("anything at all", empty)
    assert result.grounded is False
    assert result.text == NO_CONTEXT_MESSAGE
    assert result.sources == []


def test_model_is_not_called_when_retrieval_is_empty():
    client = FakeClient()
    answer("anything at all", VectorIndex(HashingEmbedder()), client=client)
    assert client.captured is None, "the model must not be called without grounding"


def test_prompt_forbids_outside_knowledge_and_demands_citations(kb_path):
    client = FakeClient()
    answer("too many clients already", _index(kb_path), client=client)
    system = client.captured[0]["content"]
    assert "ONLY from the numbered context" in system
    assert "[doc#chunk]" in system


def test_context_passages_carry_their_citation_ids(kb_path):
    client = FakeClient()
    answer("too many clients already", _index(kb_path), client=client)
    user = client.captured[1]["content"]
    assert "[postgres-connection-pool#" in user


def test_sources_are_returned_to_the_caller(kb_path):
    result = answer("too many clients already", _index(kb_path), client=FakeClient())
    assert result.grounded is True
    assert result.sources
    assert all(isinstance(c, Chunk) for c in result.sources)


def test_retrieval_only_mode_needs_no_client(kb_path):
    result = answer("too many clients already", _index(kb_path), client=None)
    assert result.grounded is True
    assert "Retrieval-only mode" in result.text


def test_build_messages_has_system_then_user():
    chunk = Chunk(doc_id="d", chunk_id="c00", heading="H", text="body")
    messages = build_messages("log line", [(chunk, 0.9)])
    assert [m["role"] for m in messages] == ["system", "user"]
