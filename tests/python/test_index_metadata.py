"""What the ingest paths hand the indexer, and what a replay reads back.

The bug these lock down was invisible from either side. The indexer read
`chapters`, `view_count`, `like_count`, `duration_seconds` and `published_at`
off its payload and wrote all five to a datastore that had declared all five;
the fetcher simply never put them in the payload. Both halves looked correct in
isolation, so 4,483 videos were stored with a zero view count and 1,425 of them
with a publication date of 2026-01-01 that nothing had ever published on (#17).

So the assertions here are about the SEAM: that a value collected on one side
arrives on the other, in the type the datastore wants, however the collecting
path happened to spell it.
"""
import json
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / 'src' / 'transcript-service')
)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))

import fetcher  # noqa: E402
import reindex_from_files as reindex  # noqa: E402

# Two segments, so the transcript's own length is 90 + 10 = 100s.
SEGMENTS = [
    {"text": "one", "start": 0.0, "duration": 5.0},
    {"text": "two", "start": 90.0, "duration": 10.0},
]

# What scripts/priority_ingest_channel.py builds: everything a string, because
# it all came back from one yt-dlp --print call, and chapters as JSON.
YTDLP_VIDEO = {
    "id": "lM96QDW-sww",
    "title": "A sermon",
    "upload_date": "20240603",
    "extra_metadata": {
        "duration": "5400",
        "view_count": "124",
        "like_count": "3",
        "live_status": "was_live",
        "chapters": '[{"start_time": 0, "end_time": 762, "title": "Intro"}]',
    },
}

# What discovery builds off the RSS feed: real numbers, no chapters, no length.
RSS_VIDEO = {
    "id": "abc12345678",
    "title": "An episode",
    "upload_date": "20260807",
    "extra_metadata": {"view_count": 4210, "like_count": 88},
}


class TestIndexMetadata:
    def test_ytdlp_path_sends_everything_it_collected(self):
        meta = fetcher.index_metadata(YTDLP_VIDEO, SEGMENTS)
        assert meta["published_at"] == "2024-06-03"
        assert meta["view_count"] == 124
        assert meta["like_count"] == 3
        assert meta["live_status"] == "was_live"
        assert meta["chapters"] == [
            {"start_time": 0, "end_time": 762, "title": "Intro"}
        ]

    def test_rss_path_sends_what_the_feed_carries(self):
        meta = fetcher.index_metadata(RSS_VIDEO, SEGMENTS)
        assert meta["published_at"] == "2026-08-07"
        assert meta["view_count"] == 4210
        assert meta["chapters"] == []
        assert "live_status" not in meta

    def test_real_video_length_beats_where_the_captions_stop(self):
        """Captions routinely end before the video does."""
        assert fetcher.index_metadata(YTDLP_VIDEO, SEGMENTS)["duration_seconds"] == 5400.0

    def test_transcript_length_is_the_fallback_not_a_zero(self):
        assert fetcher.index_metadata(RSS_VIDEO, SEGMENTS)["duration_seconds"] == 100.0

    def test_absent_count_is_omitted_rather_than_sent_as_zero(self):
        """No recorded view count and zero views are different facts."""
        video = {"id": "x", "upload_date": "20260101",
                 "extra_metadata": {"view_count": "NA", "like_count": ""}}
        meta = fetcher.index_metadata(video, SEGMENTS)
        assert "view_count" not in meta and "like_count" not in meta

    def test_a_real_zero_still_travels(self):
        video = {"id": "x", "upload_date": "20260101",
                 "extra_metadata": {"view_count": 0}}
        assert fetcher.index_metadata(video, SEGMENTS)["view_count"] == 0

    def test_unknown_date_is_the_epoch_not_something_plausible(self):
        """The whole point of #17: a wrong date that looks real is the worst
        outcome, because nothing downstream can tell it from a right one."""
        for absent in ("NA", "", None, "unknown", "2024"):
            meta = fetcher.index_metadata({"id": "x", "upload_date": absent}, [])
            assert meta["published_at"] == "1970-01-01"

    def test_unparseable_chapters_yield_none_not_a_half_read_one(self):
        video = {"id": "x", "upload_date": "20260101",
                 "extra_metadata": {"chapters": "{not json at all"}}
        assert fetcher.index_metadata(video, SEGMENTS)["chapters"] == []


class TestChaptersSurviveTheTranscriptFile:
    """The file on disk is the only copy if the index has to be replayed."""

    def test_round_trip_through_the_frontmatter(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fetcher.Config, "TRANSCRIPT_DIR", str(tmp_path))
        video = dict(YTDLP_VIDEO, channel_handle="pastorchrisdurkin",
                     channel_name="Pastor Chris Durkin", domain="faith")
        # An apostrophe in a chapter title is what broke the old quote-swap.
        chapters = [{"start_time": 0, "title": "Don't stop", "end_time": 762}]
        video["extra_metadata"] = dict(video["extra_metadata"],
                                       chapters=json.dumps(chapters))

        path = Path(fetcher.save_transcript_file(video, SEGMENTS))
        meta, _ = reindex.parse_frontmatter(path.read_text(encoding="utf-8"))

        assert reindex.parse_chapters(meta["chapters"]) == chapters
        assert reindex.as_number(meta["view_count"], int) == 124
        assert reindex.as_number(meta["duration"], float) == 5400.0
        assert meta["live_status"] == "was_live"
        assert reindex.normalize_date(meta["published"]) == "2024-06-03"

    def test_the_older_single_quoted_form_still_reads(self):
        """13 files were written before chapters were stored as JSON."""
        legacy = "[{'start_time': 0, 'end_time': 762, 'title': 'Intro'}]"
        assert reindex.parse_chapters(legacy) == [
            {"start_time": 0, "end_time": 762, "title": "Intro"}
        ]

    def test_a_missing_count_is_not_read_as_zero(self):
        assert reindex.as_number("", int) is None
        assert reindex.as_number("unknown", float) is None
        assert reindex.as_number("0", int) == 0
