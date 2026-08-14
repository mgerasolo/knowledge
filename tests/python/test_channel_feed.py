"""Tests for the YouTube channel RSS feed reader.

The fixture at fixtures/youtube_channel_feed.xml is a REAL feed, not a
hand-written one: the Internet Archive's capture of

    https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw

(Google for Developers) taken 2024-12-25. It is used rather than something
invented because a fake would have been wrong in a way that mattered — the real
feed reports <yt:channelId> WITHOUT the "UC" prefix that the same document's
links carry, and feeding that value back into a feed URL 404s. Nobody writing a
fixture from the schema would have reproduced that.

Capturing a fresh feed was not possible: as of 2026-08-14 the endpoint returns
404/500 for every channel tried, from four independent networks.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / 'src' / 'transcript-service')
)

import channel_feed  # noqa: E402
from channel_feed import (  # noqa: E402
    FeedUnavailable,
    channel_id_for,
    fetch_channel_feed,
    load_channel_ids,
    looks_blocked,
    parse_feed,
    save_channel_ids,
)

FIXTURE = Path(__file__).parent / "fixtures" / "youtube_channel_feed.xml"
REAL_FEED = FIXTURE.read_text()

# The channel the captured feed belongs to.
REAL_CHANNEL_ID = "UC_x5XG1OV2P6uZZ5FSM9Ttw"


class _Response:
    """Minimal stand-in for a requests Response."""

    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code
        self.content = text.encode()

    @property
    def ok(self):
        return 200 <= self.status_code < 300


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Never touch the real /data/state cache from a test."""
    monkeypatch.setenv("CHANNEL_ID_CACHE", str(tmp_path / "channel_ids.json"))


class TestParseRealFeed:
    """Parsing is checked against the captured feed, field by field."""

    def test_reads_every_entry(self):
        # A feed carries a fixed recent-uploads window, not an archive. Fifteen
        # is what this one holds, and it is why the feed cannot drive backfill.
        assert len(parse_feed(REAL_FEED)["videos"]) == 15

    def test_channel_title(self):
        assert parse_feed(REAL_FEED)["channel_title"] == "Google for Developers"

    def test_video_ids_are_youtube_ids(self):
        for video in parse_feed(REAL_FEED)["videos"]:
            assert len(video["id"]) == 11

    def test_published_becomes_the_yyyymmdd_the_pipeline_expects(self):
        # The rest of the pipeline files transcripts by upload_date, and yt-dlp
        # hands it that format. The feed's ISO timestamp has to match it or
        # every RSS-discovered video lands in <channel>/unknown/.
        first = parse_feed(REAL_FEED)["videos"][0]
        assert first["upload_date"] == "20241223"
        assert first["published"].startswith("2024-12-23T")

    def test_view_and_like_counts_come_along_free(self):
        # The reason the feed is worth using at all beyond block-avoidance:
        # these otherwise cost a separate metadata request per video.
        first = parse_feed(REAL_FEED)["videos"][0]
        assert first["view_count"] == 3406
        assert first["like_count"] == 70

    def test_description_is_carried(self):
        assert len(parse_feed(REAL_FEED)["videos"][0]["description"]) > 100

    def test_feed_channel_id_really_does_lack_the_uc_prefix(self):
        # Documents the quirk the override exists for. If a future YouTube
        # change starts including "UC", this test failing is the signal.
        assert parse_feed(REAL_FEED)["channel_id"] == REAL_CHANNEL_ID[2:]


class TestFetchChannelFeed:
    def test_requested_channel_id_wins_over_the_feeds_own(self, monkeypatch):
        monkeypatch.setattr(
            channel_feed.requests, "get", lambda *a, **k: _Response(REAL_FEED)
        )
        feed = fetch_channel_feed(REAL_CHANNEL_ID)
        assert feed["channel_id"] == REAL_CHANNEL_ID
        assert feed["feed_channel_id"] == REAL_CHANNEL_ID[2:]

    def test_requests_the_documented_url(self, monkeypatch):
        seen = {}

        def fake_get(url, **kwargs):
            seen["url"] = url
            return _Response(REAL_FEED)

        monkeypatch.setattr(channel_feed.requests, "get", fake_get)
        fetch_channel_feed(REAL_CHANNEL_ID)
        assert seen["url"] == (
            "https://www.youtube.com/feeds/videos.xml"
            f"?channel_id={REAL_CHANNEL_ID}"
        )

    def test_rejects_a_value_that_is_not_a_channel_id(self):
        # Guards against a handle being passed where an ID belongs.
        with pytest.raises(FeedUnavailable):
            fetch_channel_feed("@hubermanlab")

    def test_429_is_flagged_as_blocked(self, monkeypatch):
        monkeypatch.setattr(
            channel_feed.requests, "get", lambda *a, **k: _Response("", 429)
        )
        with pytest.raises(FeedUnavailable) as caught:
            fetch_channel_feed(REAL_CHANNEL_ID)
        assert caught.value.blocked is True

    def test_404_is_a_plain_failure_not_a_block(self, monkeypatch):
        # This is what the live endpoint returns today. It must read as "fall
        # back", never as "our IP is in trouble".
        monkeypatch.setattr(
            channel_feed.requests, "get", lambda *a, **k: _Response("", 404)
        )
        with pytest.raises(FeedUnavailable) as caught:
            fetch_channel_feed(REAL_CHANNEL_ID)
        assert caught.value.blocked is False

    def test_bot_challenge_served_as_http_200_is_caught(self, monkeypatch):
        # YouTube returns its interstitial with a success status. Parsing that
        # as "no entries" would report the channel as quiet.
        monkeypatch.setattr(
            channel_feed.requests,
            "get",
            lambda *a, **k: _Response("<html>Sorry... unusual traffic</html>", 200),
        )
        with pytest.raises(FeedUnavailable) as caught:
            fetch_channel_feed(REAL_CHANNEL_ID)
        assert caught.value.blocked is True

    def test_an_empty_feed_is_a_failure_not_an_empty_answer(self, monkeypatch):
        # "No entries" and "we could not read it" are indistinguishable from
        # here, and guessing wrong means silently skipping a live channel.
        empty = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            '<title>Quiet</title></feed>'
        )
        monkeypatch.setattr(
            channel_feed.requests, "get", lambda *a, **k: _Response(empty)
        )
        with pytest.raises(FeedUnavailable):
            fetch_channel_feed(REAL_CHANNEL_ID)


class TestHostileInput:
    def test_a_dtd_is_refused_before_parsing(self):
        # Closes XXE and billion-laughs without a new dependency.
        bomb = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE feed [<!ENTITY a "aaaaaaaaaa">]>'
            '<feed xmlns="http://www.w3.org/2005/Atom"><title>&a;</title></feed>'
        )
        with pytest.raises(FeedUnavailable, match="DTD"):
            parse_feed(bomb)

    def test_malformed_xml_raises_feed_unavailable(self):
        with pytest.raises(FeedUnavailable):
            parse_feed("<feed><entry>")


class TestChannelIdCache:
    def test_round_trips(self):
        save_channel_ids({"hubermanlab": "UC2D2CMWXMOVWx7giW1n3LIg"})
        assert load_channel_ids() == {"hubermanlab": "UC2D2CMWXMOVWx7giW1n3LIg"}

    def test_missing_file_is_an_empty_cache(self):
        assert load_channel_ids() == {}

    def test_corrupt_file_is_an_empty_cache(self):
        channel_feed.cache_path().parent.mkdir(parents=True, exist_ok=True)
        channel_feed.cache_path().write_text("{not json")
        assert load_channel_ids() == {}

    def test_entries_that_are_not_channel_ids_are_dropped(self):
        channel_feed.cache_path().parent.mkdir(parents=True, exist_ok=True)
        channel_feed.cache_path().write_text(
            json.dumps({"good": "UC2D2CMWXMOVWx7giW1n3LIg", "bad": "@notanid"})
        )
        assert list(load_channel_ids()) == ["good"]

    def test_resolves_lazily_on_a_miss_and_caches_the_result(self):
        calls = []

        def resolver(handle):
            calls.append(handle)
            return "UC2D2CMWXMOVWx7giW1n3LIg"

        assert channel_id_for("hubermanlab", resolver=resolver) == (
            "UC2D2CMWXMOVWx7giW1n3LIg"
        )
        assert channel_id_for("hubermanlab", resolver=resolver) == (
            "UC2D2CMWXMOVWx7giW1n3LIg"
        )
        # Resolution is a page fetch. Doing it once per sweep would be exactly
        # the scraping this change exists to remove.
        assert calls == ["hubermanlab"]

    def test_a_failed_resolution_is_not_cached(self):
        def resolver(handle):
            raise FeedUnavailable("channel page HTTP 500")

        with pytest.raises(FeedUnavailable):
            channel_id_for("hubermanlab", resolver=resolver)
        # Caching the failure would strand the channel on the fallback path
        # even after YouTube recovered.
        assert load_channel_ids() == {}


class TestResolveChannelId:
    def test_prefers_the_canonical_link(self, monkeypatch):
        # A channel page mentions other channels' IDs in its recommendations;
        # only the canonical link describes the channel we asked for.
        html = (
            '<html><head>'
            '<link rel="canonical" href="https://www.youtube.com/channel/'
            'UC2D2CMWXMOVWx7giW1n3LIg">'
            '</head><body>{"channelId":"UCbaQv8_DS1n8puOnJRzLPzw"}</body></html>'
        )
        monkeypatch.setattr(
            channel_feed.requests, "get", lambda *a, **k: _Response(html)
        )
        assert channel_feed.resolve_channel_id("x") == "UC2D2CMWXMOVWx7giW1n3LIg"

    def test_falls_back_to_the_channel_id_field(self, monkeypatch):
        html = '<html>{"channelId":"UCbaQv8_DS1n8puOnJRzLPzw"}</html>'
        monkeypatch.setattr(
            channel_feed.requests, "get", lambda *a, **k: _Response(html)
        )
        assert channel_feed.resolve_channel_id("x") == "UCbaQv8_DS1n8puOnJRzLPzw"

    def test_no_id_on_page_raises(self, monkeypatch):
        monkeypatch.setattr(
            channel_feed.requests, "get", lambda *a, **k: _Response("<html></html>")
        )
        with pytest.raises(FeedUnavailable):
            channel_feed.resolve_channel_id("x")


class TestBlockDetection:
    @pytest.mark.parametrize(
        "body",
        [
            "Sorry... we have detected something",
            "Our systems have detected unusual traffic",
            "please confirm you're not a bot",
        ],
    )
    def test_recognises_the_interstitial(self, body):
        assert looks_blocked(body) is True

    def test_a_real_feed_is_not_a_block(self):
        assert looks_blocked(REAL_FEED) is False
