import json
from pathlib import Path

import pytest

from corpus import CorpusError, load_corpus


def _write(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "personality.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_load_corpus_flattens_sources_and_guests(tmp_path):
    path = _write(
        tmp_path,
        {
            "personality_id": "teacher",
            "display_name": "Teacher",
            "description": "Test",
            "sources": [
                {"videos": [{"video_id": "a", "title": "A", "duration_seconds": 20}]},
                {"videos": [{"video_id": "b", "title": "B", "published": "2026-01-01"}]},
                {"videos": [{"video_id": "z", "title": "Z", "duration_seconds": 0}]},
            ],
            "guest_appearances": [{"video_id": "c", "title": "C", "duration_seconds": 30}],
        },
    )
    corpus = load_corpus(path)
    assert corpus.video_ids == ["a", "b", "z", "c"]
    assert corpus.by_id["a"].duration_seconds == 20.0
    # Zero is the unknown-duration sentinel and must normalize to None.
    assert corpus.by_id["z"].duration_seconds is None


def test_real_myron_manifest_has_298_unique_videos():
    path = Path(__file__).resolve().parents[2] / "personalities" / "myron-golden.json"
    corpus = load_corpus(path)
    assert corpus.personality_id == "myron-golden"
    assert len(corpus.videos) == 298
    assert len(set(corpus.video_ids)) == 298
    # All manifest durations were backfilled via yt-dlp (commit 30e2e6b); this
    # video previously carried the zero sentinel and now has its real duration.
    assert corpus.by_id["cB0AlCFzlFs"].duration_seconds == 3954.0
    assert all(
        video.duration_seconds is None or video.duration_seconds > 0
        for video in corpus.videos
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda doc: doc.update({"sources": "bad"}),
        lambda doc: doc["sources"][0]["videos"].append(
            {"video_id": "a", "title": "duplicate"}
        ),
        lambda doc: doc["sources"][0]["videos"].append(
            {"video_id": "b", "title": "", "duration_seconds": 1}
        ),
    ],
)
def test_load_corpus_rejects_malformed_manifests(tmp_path, mutation):
    document = {
        "personality_id": "teacher",
        "display_name": "Teacher",
        "sources": [{"videos": [{"video_id": "a", "title": "A"}]}],
    }
    mutation(document)
    with pytest.raises(CorpusError):
        load_corpus(_write(tmp_path, document))
