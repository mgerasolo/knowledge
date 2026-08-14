"""Tests for single-video enrollment (#46).

The pipeline pieces (transcript fetch, yt-dlp, the embedding service) are
monkeypatched — these tests are about the ORCHESTRATION: which state gets
written, which HTTP verdicts come back for which failure, and that tags reach
both the file and the index exactly once. The failure cases matter most: a
mid-broadcast livestream recorded as "no captions" is blacklisted forever, and
that is the class of bug this module inherited its defenses against.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / 'src' / 'transcript-service')
)

import single_video  # noqa: E402
from single_video import (  # noqa: E402
    EnrollError,
    enroll_video,
    extract_video_id,
    normalize_tags,
)

SAMPLE_ID = "hiQW6FZkA9o"


class TestExtractVideoId:
    """Every URL shape people actually paste yields the same 11-char id."""

    @pytest.mark.parametrize("ref", [
        SAMPLE_ID,
        f"https://youtu.be/{SAMPLE_ID}?si=share-tracking-junk",
        f"https://www.youtube.com/watch?v={SAMPLE_ID}",
        f"https://www.youtube.com/watch?v={SAMPLE_ID}&t=120",
        f"https://www.youtube.com/shorts/{SAMPLE_ID}",
        f"https://www.youtube.com/live/{SAMPLE_ID}",
        f"https://www.youtube.com/embed/{SAMPLE_ID}",
        f"  https://youtu.be/{SAMPLE_ID}  ",
    ])
    def test_all_shapes_resolve(self, ref):
        assert extract_video_id(ref) == SAMPLE_ID

    @pytest.mark.parametrize("ref", [
        "", None, "not a url", "https://youtube.com/@MyronGolden",
        "hiQW6FZkA9",      # 10 chars — one short
        "hiQW6FZkA9oX",    # 12 chars — must not half-match
    ])
    def test_junk_is_rejected_not_guessed(self, ref):
        with pytest.raises(EnrollError):
            extract_video_id(ref)


class TestNormalizeTags:
    def test_lowercases_strips_and_dedupes(self):
        assert normalize_tags(
            [" Personality:Myron-Golden ", "personality:myron-golden"]
        ) == ["personality:myron-golden"]

    def test_none_and_empty_are_no_tags(self):
        assert normalize_tags(None) == []
        assert normalize_tags([]) == []
        assert normalize_tags(["", "  "]) == []

    @pytest.mark.parametrize("bad", [
        ["has space"], ["quote'"], ["semi;colon"], ["a" * 81], [":leading"],
    ])
    def test_rejects_whole_request_on_any_bad_tag(self, bad):
        # Half-applied tag lists are worse than rejected ones.
        with pytest.raises(EnrollError):
            normalize_tags(["fine-tag"] + bad)

    def test_non_list_rejected(self):
        with pytest.raises(EnrollError):
            normalize_tags("personality:myron-golden")


@pytest.fixture
def pipeline(monkeypatch, tmp_path):
    """Fake every external touchpoint; record what the orchestration did."""
    calls = {
        "state": {"fetched": [], "failed": [], "skipped": []},
        "video_list": {"videos": [], "total_videos": 0},
        "saved": [], "indexed": [], "tagged": [],
    }

    monkeypatch.setattr(single_video, "load_state", lambda: json.loads(json.dumps(calls["state"])))
    monkeypatch.setattr(single_video, "save_state", lambda s: calls.__setitem__("state", s))
    monkeypatch.setattr(single_video, "load_video_list", lambda: json.loads(json.dumps(calls["video_list"])))
    monkeypatch.setattr(single_video, "save_video_list", lambda v: calls.__setitem__("video_list", v))

    monkeypatch.setattr(single_video, "fetch_video_metadata", lambda vid: {
        "title": "Guest Interview", "uploader_id": "@SomeHostShow",
        "channel": "Some Host Show", "upload_date": "20260801",
        "duration": "3600", "view_count": "1000", "like_count": "50",
        "live_status": "was_live", "chapters": "", "description": "desc",
    })
    monkeypatch.setattr(single_video, "fetch_transcript",
                        lambda vid: [{"text": "hello", "start": 0.0, "duration": 2.0}])

    def fake_save(video, segments, description=None):
        calls["saved"].append(video)
        return "/data/transcripts/somehostshow/2026-08/guest-interview.md"
    monkeypatch.setattr(single_video, "save_transcript_file", fake_save)

    def fake_index(video, segments, description):
        calls["indexed"].append(video["id"])
        return True, None
    monkeypatch.setattr(single_video, "_index_video", fake_index)

    def fake_push(video_id, tags):
        calls["tagged"].append((video_id, tags))
        return True, None
    monkeypatch.setattr(single_video, "push_tags", fake_push)

    return calls


class TestEnrollOrchestration:
    def test_fresh_video_runs_full_pipeline(self, pipeline):
        result, status = enroll_video(
            f"https://youtu.be/{SAMPLE_ID}?si=junk",
            tags=["personality:myron-golden"], domain="business",
        )
        assert status == 200 and result["success"]
        # State, master list, file, index and tags all updated exactly once.
        assert SAMPLE_ID in pipeline["state"]["fetched"]
        assert pipeline["video_list"]["videos"][0]["id"] == SAMPLE_ID
        assert pipeline["saved"][0]["tags"] == ["personality:myron-golden"]
        assert pipeline["saved"][0]["channel_handle"] == "somehostshow"
        assert pipeline["indexed"] == [SAMPLE_ID]
        assert pipeline["tagged"] == [(SAMPLE_ID, ["personality:myron-golden"])]

    def test_already_fetched_tags_only_no_refetch(self, pipeline, monkeypatch):
        pipeline["state"]["fetched"].append(SAMPLE_ID)

        def boom(vid):
            raise AssertionError("must not re-fetch a held video")
        monkeypatch.setattr(single_video, "fetch_transcript", boom)

        result, status = enroll_video(SAMPLE_ID, tags=["personality:myron-golden"])
        assert status == 200 and result["already_fetched"]
        assert pipeline["tagged"] == [(SAMPLE_ID, ["personality:myron-golden"])]
        assert pipeline["saved"] == []

    def test_unfinished_stream_is_deferred_not_blacklisted(self, pipeline, monkeypatch):
        monkeypatch.setattr(single_video, "fetch_video_metadata", lambda vid: {
            "title": "Live now", "uploader_id": "@x", "channel": "X",
            "upload_date": "", "duration": "", "view_count": "",
            "like_count": "", "live_status": "is_live", "chapters": "",
            "description": "",
        })
        result, status = enroll_video(SAMPLE_ID)
        assert status == 409 and result["deferred"]
        assert SAMPLE_ID not in pipeline["state"]["failed"]

    def test_no_captions_recorded_as_failed(self, pipeline, monkeypatch):
        monkeypatch.setattr(single_video, "fetch_transcript", lambda vid: None)
        result, status = enroll_video(SAMPLE_ID)
        assert status == 422 and not result["success"]
        assert SAMPLE_ID in pipeline["state"]["failed"]

    def test_rate_limited_is_retryable_and_leaves_no_state(self, pipeline, monkeypatch):
        def blocked(vid):
            raise single_video.TranscriptBlocked("429")
        monkeypatch.setattr(single_video, "fetch_transcript", blocked)
        result, status = enroll_video(SAMPLE_ID)
        assert status == 429 and result["blocked"]
        assert SAMPLE_ID not in pipeline["state"]["failed"]
        assert SAMPLE_ID not in pipeline["state"]["fetched"]

    def test_unreadable_video_404(self, pipeline, monkeypatch):
        monkeypatch.setattr(
            single_video, "fetch_video_metadata",
            lambda vid: {f: "" for f in (
                "title", "uploader_id", "channel", "upload_date", "duration",
                "view_count", "like_count", "live_status", "chapters",
                "description")},
        )
        result, status = enroll_video(SAMPLE_ID)
        assert status == 404 and not result["success"]

    def test_bad_tags_rejected_before_any_network_call(self, pipeline, monkeypatch):
        def boom(vid):
            raise AssertionError("metadata must not be fetched for a bad request")
        monkeypatch.setattr(single_video, "fetch_video_metadata", boom)
        with pytest.raises(EnrollError):
            enroll_video(SAMPLE_ID, tags=["not a valid tag!"])
