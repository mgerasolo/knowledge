from corpus import PersonalityCorpus, Video
from retrieval import Retriever


class FakeConfig:
    TOP_K = 2
    REC_BOOST = 0.15
    REC_HORIZON_DAYS = 730
    MIN_COSINE = 0.20


class FakeLLM:
    def embed(self, query):
        assert query == "price objection"
        return [0.1, 0.2]


class FakeDB:
    def __init__(self):
        self.calls = []

    def result(self, sql, variables):
        self.calls.append((sql, variables))
        if "GROUP ALL" in sql:
            return [{"count": 10, "embedded": 4}]
        return [
            {"id": "segment:old", "text": "old", "video_youtube_id": "v", "cosine": 0.9, "published_at": "2020-01-01"},
            {"id": "segment:new", "text": "new", "video_youtube_id": "v", "cosine": 0.85, "published_at": "2026-08-14"},
            {"id": "segment:third", "text": "third", "video_youtube_id": "v", "cosine": 0.5, "published_at": None},
        ]


def test_partial_coverage_is_reported_and_recency_reranks_candidates():
    corpus = PersonalityCorpus("p", "P", "", (Video("v", "V", None, 100),))
    db = FakeDB()
    result = Retriever(db, FakeLLM(), FakeConfig).retrieve("price objection", corpus)
    assert result.coverage_percent == 40.0
    assert result.chunks_searched == 3
    assert [chunk["id"] for chunk in result.chunks] == ["segment:new", "segment:old"]
    search_sql, search_vars = db.calls[1]
    assert "video_youtube_id IN $corpus" in search_sql
    assert "embedding IS NOT NONE" in search_sql
    assert search_vars["corpus"] == ["v"]


def test_zero_segment_corpus_reports_zero_coverage():
    db = FakeDB()
    original = db.result
    db.result = lambda sql, variables: [] if "GROUP ALL" in sql else original(sql, variables)
    corpus = PersonalityCorpus("p", "P", "", (Video("v", "V", None, 100),))
    assert Retriever(db, FakeLLM(), FakeConfig).retrieve("price objection", corpus).coverage_percent == 0.0


def test_irrelevant_and_nonfinite_similarities_are_not_returned():
    db = FakeDB()
    original = db.result
    db.result = lambda sql, variables: (
        original(sql, variables)
        if "GROUP ALL" in sql
        else [
            {"id": "low", "video_youtube_id": "v", "cosine": 0.19},
            {"id": "nan", "video_youtube_id": "v", "cosine": float("nan")},
        ]
    )
    corpus = PersonalityCorpus("p", "P", "", (Video("v", "V", None, 100),))
    assert Retriever(db, FakeLLM(), FakeConfig).retrieve("price objection", corpus).chunks == []
