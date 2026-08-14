import pytest

from composition import CompositionResult, DISCLAIMER
from corpus import PersonalityCorpus, Video
from retrieval import RetrievalError, RetrievalResult
from service import AskValidationError, LoggingError, ProfessorService, validate_history


CORPUS = PersonalityCorpus(
    "myron-golden", "Myron Golden", "", (Video("vid", "The Video", None, 120.0),)
)


class FakeConfig:
    CHAT_MODEL = "main"
    INPUT_COST_PER_MILLION = 1.0
    OUTPUT_COST_PER_MILLION = 2.0


class FakeDB:
    def __init__(self):
        self.records = []
        self.available = True

    def write(self, sql, variables):
        self.records.append(variables["record"])


class FakeRetriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.query = None

    def retrieve(self, query, corpus):
        self.query = query
        return RetrievalResult(self.chunks, len(self.chunks), 37.5, 4, 5)


class FakeComposer:
    def __init__(self, tiers, rewrite_error=False):
        self.tiers = tiers
        self.rewrite_error = rewrite_error

    def rewrite(self, question, history):
        if self.rewrite_error:
            raise RetrievalError("upstream failed")
        return "standalone query", {"prompt_tokens": 10, "completion_tokens": 2}

    def compose(self, question, chunks, corpus):
        return CompositionResult(self.tiers, {"prompt_tokens": 20, "completion_tokens": 4}, ["main"])


def _service(chunks, tiers, composer=None):
    db = FakeDB()
    retriever = FakeRetriever(chunks)
    service = ProfessorService(
        CORPUS, db, retriever, composer or FakeComposer(tiers), FakeConfig
    )
    return service, db, retriever


def test_grounded_answer_builds_valid_citation_and_writes_full_log():
    chunks = [{"id": "segment:1", "text": "Value exceeds price.", "video_youtube_id": "vid", "start_time": 12.4, "end_time": 20, "cosine": 0.8, "final_score": 0.9}]
    tiers = {"said": [{"text": "I increase value.", "citations": [1]}], "might_say": "Inference: add certainty.", "extension": "He hasn't directly addressed this case."}
    service, db, _ = _service(chunks, tiers)
    answer = service.ask("myron-golden", "How?", [])
    assert answer["disclaimer"] == DISCLAIMER
    assert answer["citations"]["1"]["video_id"] == "vid"
    assert answer["citations"]["1"]["url"].endswith("&t=12s")
    assert answer["meta"]["coverage_percent"] == 37.5
    assert answer["meta"]["log_saved"] is True
    assert db.records[0]["answer"] is answer
    assert db.records[0]["retrieved_chunks"][0]["final_score"] == 0.9
    assert db.records[0]["retrieved_chunks"][0]["id"] == "segment:1"
    assert db.records[0]["retrieved_chunks"][0]["cosine"] == 0.8
    assert db.records[0]["latency_ms"]["embedding"] == 4
    assert db.records[0]["latency_ms"]["database"] == 5


def test_silent_corpus_returns_tier_c_only_contract_and_logs():
    tiers = {"said": [], "might_say": "Inference: the corpus is silent.", "extension": "He hasn't directly addressed this; here is general guidance."}
    service, db, _ = _service([], tiers)
    answer = service.ask("myron-golden", "Novel topic")
    assert answer["tiers"]["said"] == []
    assert answer["citations"] == {}
    assert len(db.records) == 1


def test_history_rewrite_and_failure_fallback_both_retrieve():
    tiers = {"said": [], "might_say": "Inference", "extension": "He hasn't directly addressed it."}
    service, _, retriever = _service([], tiers)
    service.ask("myron-golden", "What about that?", [{"role": "user", "content": "Offers"}])
    assert retriever.query == "standalone query"

    failing = FakeComposer(tiers, rewrite_error=True)
    service, db, retriever = _service([], tiers, failing)
    service.ask("myron-golden", "Original", [{"role": "assistant", "content": "Context"}])
    assert retriever.query == "Original"
    assert len(db.records) == 1
    assert "RetrievalError" in db.records[0]["rewrite_error"]


def test_composition_failure_is_logged_before_propagating():
    class Broken(FakeComposer):
        def compose(self, *args):
            raise RuntimeError("bad model")

    tiers = {"said": [], "might_say": "", "extension": ""}
    service, db, _ = _service([], tiers, Broken(tiers))
    with pytest.raises(RuntimeError):
        service.ask("myron-golden", "Question")
    assert len(db.records) == 1
    assert db.records[0]["answer"] is None
    assert "RuntimeError" in db.records[0]["error"]


@pytest.mark.parametrize(
    "personality,question,history",
    [
        ("unknown", "Question", None),
        ("myron-golden", "", None),
        ("myron-golden", "Question", "bad"),
        ("myron-golden", "Question", [{"role": "system", "content": "bad"}]),
    ],
)
def test_invalid_requests_are_rejected(personality, question, history):
    tiers = {"said": [], "might_say": "", "extension": ""}
    service, db, _ = _service([], tiers)
    with pytest.raises(AskValidationError):
        service.ask(personality, question, history)
    assert len(db.records) == 1
    assert "AskValidationError" in db.records[0]["error"]


def test_invalid_citation_timestamp_is_rejected_and_logged():
    chunks = [{"id": "segment:1", "text": "x", "video_youtube_id": "vid", "start_time": float("nan"), "end_time": 20, "cosine": 0.8, "final_score": 0.8}]
    tiers = {"said": [{"text": "x", "citations": [1]}], "might_say": "Inference", "extension": "He hasn't directly addressed it."}
    service, db, _ = _service(chunks, tiers)
    with pytest.raises(ValueError):
        service.ask("myron-golden", "Question")
    assert len(db.records) == 1


def test_success_is_not_returned_when_mandatory_log_write_fails():
    tiers = {"said": [], "might_say": "", "extension": "He hasn't directly addressed it."}
    service, db, _ = _service([], tiers)

    def fail(*args, **kwargs):
        from surreal_client import SurrealError
        raise SurrealError("down")

    db.write = fail
    with pytest.raises(LoggingError):
        service.ask("myron-golden", "Question")
