"""Which discovery path each channel takes, and what still falls back.

The behaviour these lock down is the part that is expensive to get wrong and
invisible when you do: a channel whose livestreams stop being discovered looks
exactly like a channel that stopped posting. That already happened once, on
2026-08-13, and cost roughly 430 sermons on one channel alone.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / 'src' / 'transcript-service')
)

import fetcher  # noqa: E402
from channel_feed import FeedUnavailable  # noqa: E402

VIDEOS_ONLY = {
    "handle": "hubermanlab",
    "name": "Huberman Lab",
    "domain": "health",
}
WITH_STREAMS = {
    "handle": "PastorChrisDurkin",
    "name": "Pastor Chris Durkin",
    "domain": "faith",
    "tabs": ["videos", "streams"],
}


def _feed(*ids, views=None, likes=None):
    return {
        "channel_id": "UC2D2CMWXMOVWx7giW1n3LIg",
        "channel_title": "Test",
        "videos": [
            {
                "id": vid,
                "title": f"title {vid}",
                "upload_date": "20260810",
                "published": "2026-08-10T00:00:00+00:00",
                "description": "",
                "view_count": views,
                "like_count": likes,
            }
            for vid in ids
        ],
    }


class _Completed:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """Isolate state, silence sleeps, and record every outbound attempt."""
    monkeypatch.setattr(fetcher.Config, "STATE_DIR", str(tmp_path))
    monkeypatch.setenv("DISCOVERY_DELAY_SECONDS", "3")
    monkeypatch.delenv("DISCOVERY_USE_RSS", raising=False)
    monkeypatch.delenv("DISCOVERY_RSS_MAX_FAILURES", raising=False)
    monkeypatch.delenv("DISCOVERY_MAX_NEW", raising=False)
    monkeypatch.delenv("DISCOVERY_PLAYLIST_END", raising=False)

    record = {"feeds": [], "ytdlp": [], "sleeps": []}
    monkeypatch.setattr(fetcher.time, "sleep", lambda s: record["sleeps"].append(s))

    def ytdlp(cmd, **kwargs):
        url = cmd[-1]
        record["ytdlp"].append({"url": url, "cmd": cmd})
        tab = url.rsplit("/", 1)[-1]
        return _Completed(f"ytdlp-{tab}|A {tab} upload|20260811")

    monkeypatch.setattr(fetcher.subprocess, "run", ytdlp)

    def set_feed(behaviour):
        def feed_for(handle, limit=None):
            record["feeds"].append(handle)
            result = behaviour(handle)
            if isinstance(result, Exception):
                raise result
            if limit is not None:
                result["videos"] = result["videos"][:limit]
            return result

        monkeypatch.setattr(fetcher, "feed_videos_for_handle", feed_for)

    def set_channels(channels):
        monkeypatch.setattr(fetcher.Config, "CHANNELS", channels)

    record["set_feed"] = set_feed
    record["set_channels"] = set_channels
    return record


class TestRssIsPrimary:
    def test_a_videos_only_channel_never_touches_ytdlp(self, harness):
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: _feed("aaaaaaaaaaa"))

        result = fetcher.discover_new_videos()

        assert harness["ytdlp"] == []
        assert result["channel_stats"][0]["path"] == "rss"
        assert [v["id"] for v in result["new_videos"]] == ["aaaaaaaaaaa"]

    def test_view_and_like_counts_ride_along_from_the_feed(self, harness):
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: _feed("aaaaaaaaaaa", views=1234, likes=56))

        result = fetcher.discover_new_videos()

        assert result["new_videos"][0]["extra_metadata"] == {
            "view_count": 1234,
            "like_count": 56,
        }

    def test_absent_counts_are_omitted_rather_than_written_as_null(self, harness):
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: _feed("aaaaaaaaaaa"))

        result = fetcher.discover_new_videos()

        assert "extra_metadata" not in result["new_videos"][0]

    def test_the_feed_can_be_forced_off(self, harness, monkeypatch):
        monkeypatch.setenv("DISCOVERY_USE_RSS", "false")
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: _feed("aaaaaaaaaaa"))

        result = fetcher.discover_new_videos()

        assert harness["feeds"] == []
        assert result["channel_stats"][0]["path"] == "yt-dlp:videos"


class TestStreamsAlwaysUseYtdlp:
    """The blind spot this must not re-create.

    Measured on 2026-08-14, the feed DOES return livestreams — six of eight
    entries for @PastorChrisDurkin appeared only under yt-dlp's /streams tab.
    The pass is kept anyway because the feed holds only ~15 items of any kind
    and answered 3 of 12 sampled requests; letting sermon discovery depend on
    that is how a channel goes quiet without anyone noticing.
    """

    def test_a_stream_channel_still_gets_its_ytdlp_streams_pass(self, harness):
        harness["set_channels"]([WITH_STREAMS])
        harness["set_feed"](lambda h: _feed("aaaaaaaaaaa"))

        result = fetcher.discover_new_videos()

        # A working feed must never be allowed to retire the streams pass.
        assert len(harness["ytdlp"]) == 1
        assert harness["ytdlp"][0]["url"].endswith("/streams")
        assert result["channel_stats"][0]["path"] == "rss+yt-dlp:streams"

    def test_stream_videos_actually_reach_the_queue(self, harness):
        harness["set_channels"]([WITH_STREAMS])
        harness["set_feed"](lambda h: _feed("aaaaaaaaaaa"))

        result = fetcher.discover_new_videos()

        assert "ytdlp-streams" in [v["id"] for v in result["new_videos"]]

    def test_when_the_feed_fails_both_tabs_go_through_ytdlp(self, harness):
        harness["set_channels"]([WITH_STREAMS])
        harness["set_feed"](lambda h: FeedUnavailable("feed HTTP 404"))

        result = fetcher.discover_new_videos()

        assert [c["url"].rsplit("/", 1)[-1] for c in harness["ytdlp"]] == [
            "videos",
            "streams",
        ]
        assert result["channel_stats"][0]["path"] == "yt-dlp:videos+yt-dlp:streams"


class TestFallbackTriggers:
    @pytest.mark.parametrize(
        "failure",
        [
            FeedUnavailable("feed HTTP 404"),
            FeedUnavailable("channel page HTTP 500"),   # unresolvable handle
            FeedUnavailable("feed contained no entries"),
            FeedUnavailable("feed HTTP 429", blocked=True),
        ],
        ids=["feed-404", "cannot-resolve-handle", "empty-feed", "blocked"],
    )
    def test_every_feed_failure_falls_back_to_ytdlp(self, harness, failure):
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: failure)

        result = fetcher.discover_new_videos()

        stat = result["channel_stats"][0]
        assert stat["path"] == "yt-dlp:videos"
        assert "rss:" in stat["error"]
        assert [v["id"] for v in result["new_videos"]] == ["ytdlp-videos"]

    def test_a_block_is_flagged_distinctly_from_an_ordinary_failure(self, harness):
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](
            lambda h: FeedUnavailable("feed HTTP 429", blocked=True)
        )

        stat = fetcher.discover_new_videos()["channel_stats"][0]

        assert stat["blocked"] is True

    def test_an_unexpected_error_does_not_kill_the_sweep(self, harness):
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: ValueError("something new broke"))

        result = fetcher.discover_new_videos()

        assert result["channel_stats"][0]["path"] == "yt-dlp:videos"


class TestSweepCircuitBreaker:
    def test_stops_probing_a_dead_endpoint_after_the_budget(
        self, harness, monkeypatch
    ):
        monkeypatch.setenv("DISCOVERY_RSS_MAX_FAILURES", "2")
        harness["set_channels"](
            [dict(VIDEOS_ONLY, handle=f"ch{i}") for i in range(5)]
        )
        harness["set_feed"](lambda h: FeedUnavailable("feed HTTP 404"))

        result = fetcher.discover_new_videos()

        # Two doomed requests, not five — the live endpoint has been 404ing for
        # every channel, and paying that per channel per sweep is pure waste.
        assert harness["feeds"] == ["ch0", "ch1"]
        assert len(harness["ytdlp"]) == 5
        assert result["channel_stats"][-1]["path"] == "yt-dlp:videos"

    def test_a_success_resets_the_budget(self, harness, monkeypatch):
        monkeypatch.setenv("DISCOVERY_RSS_MAX_FAILURES", "2")
        harness["set_channels"](
            [dict(VIDEOS_ONLY, handle=f"ch{i}") for i in range(4)]
        )

        def behaviour(handle):
            if handle == "ch1":
                return _feed("aaaaaaaaaaa")
            return FeedUnavailable("feed HTTP 404")

        harness["set_feed"](behaviour)
        fetcher.discover_new_videos()

        # ch0 fails, ch1 succeeds and clears the count, ch2+ch3 fail and trip it
        assert harness["feeds"] == ["ch0", "ch1", "ch2", "ch3"]


class TestExistingSafetyPropertiesSurvive:
    def test_the_absurd_delta_circuit_breaker_still_refuses(
        self, harness, monkeypatch
    ):
        # A broken filter once queued 40,072 videos. The valve is what stopped
        # that becoming months of fetching, and RSS must not route around it.
        monkeypatch.setenv("DISCOVERY_MAX_NEW", "2")
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: _feed("aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"))

        result = fetcher.discover_new_videos()

        assert result["aborted"] is True
        assert result["would_have_added"] == 3
        assert result["new_videos"] == []

    def test_the_ytdlp_listing_cap_is_still_applied(self, harness, monkeypatch):
        monkeypatch.setenv("DISCOVERY_PLAYLIST_END", "7")
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: FeedUnavailable("feed HTTP 404"))

        fetcher.discover_new_videos()

        cmd = harness["ytdlp"][0]["cmd"]
        assert cmd[cmd.index("--playlist-end") + 1] == "7"

    def test_the_same_cap_bounds_the_feed(self, harness, monkeypatch):
        monkeypatch.setenv("DISCOVERY_PLAYLIST_END", "2")
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](
            lambda h: _feed("aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc")
        )

        result = fetcher.discover_new_videos()

        assert len(result["new_videos"]) == 2

    def test_every_outbound_call_after_the_first_is_spaced(self, harness):
        # Three channels, one with two tabs = four outbound calls, so three
        # gaps. Swapping a yt-dlp call for a feed call must not raise the rate.
        harness["set_channels"]([VIDEOS_ONLY, WITH_STREAMS, dict(VIDEOS_ONLY, handle="c3")])
        harness["set_feed"](lambda h: _feed("aaaaaaaaaaa"))

        fetcher.discover_new_videos()

        assert harness["sleeps"] == [3.0, 3.0, 3.0]

    def test_a_pipe_in_the_title_does_not_eat_the_upload_date(
        self, harness, monkeypatch
    ):
        # yt-dlp prints "id|title|date" and titles routinely contain a pipe.
        # Splitting left-to-right handed the tail to upload_date, which then
        # failed the 8-digit check and filed the transcript under
        # <channel>/unknown/ with no date. Observed on ten of ten Huberman
        # uploads listed 2026-08-14.
        real_line = (
            "wbuPQPu-03Y|Essentials: How to Optimize Female Hormone Health "
            "| Dr. Sara Gottfried|20260810"
        )
        monkeypatch.setattr(
            fetcher.subprocess, "run", lambda cmd, **kw: _Completed(real_line)
        )
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: FeedUnavailable("feed HTTP 404"))

        video = fetcher.discover_new_videos()["new_videos"][0]

        assert video["upload_date"] == "20260810"
        assert video["title"].endswith("Dr. Sara Gottfried")

    def test_already_known_videos_are_not_requeued(self, harness):
        harness["set_channels"]([VIDEOS_ONLY])
        harness["set_feed"](lambda h: _feed("aaaaaaaaaaa"))
        fetcher.save_state({"fetched": ["aaaaaaaaaaa"], "failed": [], "skipped": []})

        result = fetcher.discover_new_videos()

        assert result["new_videos"] == []
        assert result["channel_stats"][0]["recent_videos"] == 1

    def test_the_feed_and_the_streams_tab_can_overlap_without_duplicating(
        self, harness
    ):
        harness["set_channels"]([WITH_STREAMS])
        harness["set_feed"](lambda h: _feed("ytdlp-streams"))

        result = fetcher.discover_new_videos()

        assert [v["id"] for v in result["new_videos"]] == ["ytdlp-streams"]
