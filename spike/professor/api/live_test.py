#!/usr/bin/env python3
"""Credentialed Professor Phase 1 integration test; Flask is not imported."""
import json
import sys

try:
    from .composition import Composer
    from .config import Config
    from .corpus import load_corpus
    from .retrieval import LiteLLMClient, Retriever
    from .service import ProfessorService
    from .surreal_client import SurrealClient
except ImportError:
    from composition import Composer
    from config import Config
    from corpus import load_corpus
    from retrieval import LiteLLMClient, Retriever
    from service import ProfessorService
    from surreal_client import SurrealClient


QUESTIONS = [
    "How do I handle price objections?",
    "What does the Bible say about wealth according to Myron?",
    "How do I make my offer irresistible?",
]


def _assert_citations(answer, corpus):
    if not answer["citations"]:
        raise AssertionError("answer has no grounded citation")
    videos = corpus.by_id
    for citation in answer["citations"].values():
        video = videos.get(citation["video_id"])
        if video is None:
            raise AssertionError(f"citation video is outside corpus: {citation['video_id']}")
        start = float(citation["start_time"])
        if start < 0:
            raise AssertionError("citation start_time is negative")
        if video.duration_seconds is None:
            raise AssertionError(f"citation video has no known duration: {citation['video_id']}")
        if start > video.duration_seconds:
            raise AssertionError(
                f"citation start {start} exceeds video duration {video.duration_seconds}"
            )


def main() -> int:
    corpus = load_corpus(Config.CORPUS_PATH)
    db = SurrealClient()
    llm = LiteLLMClient()
    service = ProfessorService(corpus, db, Retriever(db, llm), Composer(llm))
    request_ids = []
    for question in QUESTIONS:
        answer = service.ask(corpus.personality_id, question)
        _assert_citations(answer, corpus)
        if not answer["meta"].get("log_saved"):
            raise AssertionError("professor_log write was not confirmed")
        request_ids.append(answer["meta"]["request_id"])
        print(f"\nQUESTION: {question}")
        print("TIER A — What Myron has said:")
        print(json.dumps(answer["tiers"]["said"], indent=2, ensure_ascii=False))
        print("TIER B — What Myron might say:")
        print(answer["tiers"]["might_say"])
        print("TIER C — AI extension:")
        print(answer["tiers"]["extension"])
        print("CITATIONS:")
        print(json.dumps(answer["citations"], indent=2, ensure_ascii=False))
        print("META:")
        print(json.dumps(answer["meta"], indent=2, ensure_ascii=False))

    records = db.result(
        "SELECT request_id FROM professor_log WHERE request_id IN $ids;",
        {"ids": request_ids},
    )
    found = {row.get("request_id") for row in records if isinstance(row, dict)}
    if not set(request_ids).issubset(found):
        raise AssertionError("one or more professor_log records are not visible")
    print(f"\nPASS: 3 answers validated; {len(found)} professor_log records visible")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"LIVE TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
