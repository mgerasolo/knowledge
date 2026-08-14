"""YouTube per-channel RSS feed: the cheap way to ask "what's new?".

Every channel publishes a static Atom feed at

    https://www.youtube.com/feeds/videos.xml?channel_id=UC...

It needs no API key, no login and no scraping, it is a few kilobytes, and it
carries view and like counts that otherwise cost a separate metadata request.
That makes it a far better standing-discovery mechanism than a yt-dlp
`--flat-playlist` listing, which pulls a rendered channel page through exactly
the anti-bot surface that IP-blocked this whole network on 2026-08-13.

Two limits shape how this is used, and both matter:

1. **~15 entries, and they are ALL of a channel's uploads.** The feed is one
   short chronological window, not an archive and not a per-tab view. It is the
   right tool for the standing sweep and the wrong tool for a backfill.

   It DOES include completed livestreams — measured, not assumed: on 2026-08-14
   six of eight feed entries for @PastorChrisDurkin appeared only under yt-dlp's
   /streams tab and not under /videos. Anyone reasoning that "the feed is the
   /videos tab" will get this backwards.

   It is still not a substitute for the /streams pass, for a duller reason: the
   window is shallow. Fourteen of that channel's twenty most recent streams sat
   outside it.

2. **It is unreliable.** Sampling three monitored channels twelve times on
   2026-08-14 got three answers; the rest were HTTP 404 or 500, and two of the
   three channels never answered once. This is a known, widely reported state of
   the endpoint rather than anything about our address — it fails identically
   from a residential proxy and from off-network — and YouTube's robots.txt now
   carries "Disallow: /feeds/videos.xml".

   So the feed is treated as an opportunistic fast path, never as the thing the
   corpus depends on. Every caller must have a working fallback, and the
   /streams yt-dlp pass runs regardless of how well the feed did: a channel
   whose feed is one of the dead ones would otherwise lose its livestreams
   entirely, which is exactly the blind spot fixed on 2026-08-13 and which looks
   from the outside like "that channel stopped posting".

The channel ID is the one thing the feed needs and the one thing we do not
store: the channel list is keyed by @handle. Resolving handle -> UC... requires
one page fetch, so it is cached on disk and treated as a slow-changing fact
rather than per-sweep work.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

import requests

from config import Config

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

# A channel ID is always "UC" plus 22 characters of base64url.
CHANNEL_ID_RE = re.compile(r"UC[\w-]{22}")

# The canonical link is authoritative. Bare "channelId" occurrences elsewhere in
# the page data can belong to a recommended or featured channel, so matching
# those first would happily cache someone else's channel under our handle.
_CANONICAL_RE = re.compile(
    r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"'
)
_CHANNEL_ID_FIELD_RE = re.compile(r'"channelId":"(UC[\w-]{22})"')

_ATOM = "{http://www.w3.org/2005/Atom}"
_YT = "{http://www.youtube.com/xml/schemas/2015}"
_MEDIA = "{http://search.yahoo.com/mrss/}"

# YouTube serves its "prove you're not a bot" interstitial as a SUCCESS response
# with the challenge in the body, not as an error status. Matching only on 429
# therefore misses it entirely — and a missed block reads as "this channel has
# nothing new", which is the most expensive way to be wrong here.
BLOCK_PHRASES = (
    "confirm you're not a bot",
    "confirm you are not a bot",
    "unusual traffic",
    "automated queries",
    "sorry...",
)

# Anything vastly larger than a real feed (a few tens of KB) or a channel page
# (a couple of MB) is not something we should be parsing. This is also the
# entity-expansion guard's partner: ElementTree will happily chew through a
# hostile document, so cap what reaches it.
_MAX_FEED_BYTES = 4 * 1024 * 1024
_MAX_PAGE_BYTES = 8 * 1024 * 1024

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class FeedUnavailable(Exception):
    """The feed could not be read. The caller falls back to yt-dlp.

    Carries `blocked` so a rate-limit or bot challenge is distinguishable from
    an ordinary 404 or a parse failure — same distinction TranscriptBlocked
    draws for captions, and for the same reason: a block is a statement about
    our IP address, never about the channel.
    """

    def __init__(self, message: str, blocked: bool = False):
        super().__init__(message)
        self.blocked = blocked


def looks_blocked(text: str) -> bool:
    """True when a response body is YouTube's anti-bot interstitial."""
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in BLOCK_PHRASES)


# ---- Channel ID cache ----
#
# Deliberately its own file rather than a field on Config.CHANNELS: the channel
# list is hand-edited, and a resolved ID is machine-derived state with a
# different lifecycle. Keeping them apart means neither one's edits threaten the
# other.

def cache_path() -> Path:
    """Where the handle -> channel ID map lives."""
    override = os.getenv("CHANNEL_ID_CACHE", "").strip()
    if override:
        return Path(override)
    return Path(Config.STATE_DIR) / "channel_ids.json"


def load_channel_ids() -> dict:
    """Read the cache. A corrupt or missing file is simply an empty cache."""
    path = cache_path()
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Only keep well-formed entries, so one bad hand-edit cannot send a request
    # to a nonsense feed URL forever.
    return {
        handle: value
        for handle, value in data.items()
        if isinstance(value, str) and CHANNEL_ID_RE.fullmatch(value)
    }


def save_channel_ids(mapping: dict) -> None:
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping, indent=2, sort_keys=True))


def resolve_channel_id(handle: str, timeout: int = 20) -> str:
    """Fetch the channel page once and read its canonical channel ID.

    Raises FeedUnavailable on anything that is not a clean resolution, so the
    caller falls back rather than guessing an ID.
    """
    url = f"https://www.youtube.com/@{handle}"
    try:
        response = requests.get(
            url, headers=_HEADERS, timeout=timeout, allow_redirects=True
        )
    except requests.RequestException as e:
        raise FeedUnavailable(f"channel page unreachable: {type(e).__name__}") from e

    if response.status_code == 429:
        raise FeedUnavailable("channel page HTTP 429", blocked=True)
    if not response.ok:
        raise FeedUnavailable(f"channel page HTTP {response.status_code}")

    html = response.text[:_MAX_PAGE_BYTES]
    if looks_blocked(html[:20000]):
        raise FeedUnavailable("channel page returned a bot challenge", blocked=True)

    match = _CANONICAL_RE.search(html) or _CHANNEL_ID_FIELD_RE.search(html)
    if not match:
        raise FeedUnavailable("no channel ID on page")
    return match.group(1)


def channel_id_for(handle: str, resolver=resolve_channel_id) -> str:
    """Cached handle -> channel ID, resolving lazily on a miss.

    Failures are NOT cached. A handle that cannot be resolved today costs one
    page fetch per sweep and falls back to yt-dlp meanwhile; caching the failure
    would strand that channel on the fallback path even after YouTube recovers.
    """
    cached = load_channel_ids()
    if handle in cached:
        return cached[handle]

    channel_id = resolver(handle)
    cached[handle] = channel_id
    save_channel_ids(cached)
    return channel_id


# ---- Feed fetching ----

def _text(node, tag: str) -> str:
    found = node.find(tag)
    return (found.text or "") if found is not None else ""


def _int_attr(node, attr: str) -> Optional[int]:
    if node is None:
        return None
    raw = node.get(attr)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def parse_feed(xml_text: str) -> dict:
    """Parse an Atom channel feed into plain dicts.

    Kept separate from the fetch so it can be tested against a captured feed
    without touching the network.
    """
    # Refuse any document carrying a DTD before parsing it. Both attacks the
    # stdlib parser is criticised for — external entities (XXE) and entity
    # expansion ("billion laughs") — require an entity declaration, so rejecting
    # the declaration outright closes them without adding a dependency the
    # container image does not have. A real YouTube feed never has one.
    if "<!DOCTYPE" in xml_text or "<!ENTITY" in xml_text:
        raise FeedUnavailable("feed declared a DTD")

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as e:
        raise FeedUnavailable(f"feed is not valid XML: {e}") from e

    channel_id = _text(root, f"{_YT}channelId").strip()
    channel_title = _text(root, f"{_ATOM}title").strip()

    videos = []
    for entry in root.findall(f"{_ATOM}entry"):
        video_id = _text(entry, f"{_YT}videoId").strip()
        if not video_id:
            continue

        published = _text(entry, f"{_ATOM}published").strip()
        group = entry.find(f"{_MEDIA}group")
        community = (
            group.find(f"{_MEDIA}community") if group is not None else None
        )
        statistics = (
            community.find(f"{_MEDIA}statistics") if community is not None else None
        )
        rating = (
            community.find(f"{_MEDIA}starRating") if community is not None else None
        )

        videos.append(
            {
                "id": video_id,
                "title": _text(entry, f"{_ATOM}title").strip(),
                "upload_date": _upload_date(published),
                "published": published,
                "description": (
                    _text(group, f"{_MEDIA}description") if group is not None else ""
                ),
                "view_count": _int_attr(statistics, "views"),
                "like_count": _int_attr(rating, "count"),
                "channel_id": channel_id,
                "channel_title": channel_title,
                # Atom's canonical entry link is always /watch, including for
                # Shorts and completed lives. It cannot classify content type;
                # discovery documents and handles that best-effort limitation.
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        )

    return {
        "channel_id": channel_id,
        "channel_title": channel_title,
        "videos": videos,
    }


def _upload_date(published: str) -> str:
    """ISO 8601 publish time -> the YYYYMMDD the rest of the pipeline expects.

    "NA" mirrors what yt-dlp prints when it has no date, so downstream code that
    already handles the dateless case keeps working unchanged.
    """
    if not published:
        return "NA"
    try:
        parsed = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError:
        return "NA"
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y%m%d")


def fetch_channel_feed(channel_id: str, timeout: int = 20) -> dict:
    """Fetch and parse one channel's feed. Raises FeedUnavailable on failure."""
    if not CHANNEL_ID_RE.fullmatch(channel_id or ""):
        raise FeedUnavailable(f"not a channel ID: {channel_id!r}")

    url = FEED_URL.format(channel_id=channel_id)
    try:
        response = requests.get(url, headers=_HEADERS, timeout=timeout)
    except requests.RequestException as e:
        raise FeedUnavailable(f"feed unreachable: {type(e).__name__}") from e

    if response.status_code == 429:
        raise FeedUnavailable("feed HTTP 429", blocked=True)
    if not response.ok:
        raise FeedUnavailable(f"feed HTTP {response.status_code}")

    body = response.text[:_MAX_FEED_BYTES]
    if looks_blocked(body[:20000]):
        raise FeedUnavailable("feed returned a bot challenge", blocked=True)

    parsed = parse_feed(body)
    # The feed's own <yt:channelId> drops the "UC" prefix — a real captured feed
    # reports "_x5XG1OV2P6uZZ5FSM9Ttw" for channel UC_x5XG1OV2P6uZZ5FSM9Ttw — so
    # feeding it back into a feed URL would 404. The ID we asked for is the
    # authoritative one; keep the feed's copy alongside it, not instead of it.
    parsed["feed_channel_id"] = parsed["channel_id"]
    parsed["channel_id"] = channel_id
    if not parsed["videos"]:
        # An empty feed is indistinguishable from a channel that has never
        # uploaded, and we cannot tell which from here. Treat it as a failure so
        # the caller falls back and finds out for certain, rather than recording
        # "nothing new" on a channel that may have plenty.
        raise FeedUnavailable("feed contained no entries")
    return parsed


def feed_videos_for_handle(handle: str, limit: Optional[int] = None) -> dict:
    """Everything the discovery loop needs for one channel, in one call.

    Returns the parsed feed with its entries capped at `limit`. Raises
    FeedUnavailable if the handle cannot be resolved or the feed cannot be read;
    both are fallback conditions, not errors to surface upward.
    """
    channel_id = channel_id_for(handle)
    feed = fetch_channel_feed(channel_id)
    if limit is not None and limit >= 0:
        feed["videos"] = feed["videos"][:limit]
    return feed


def pace(delay: float, last_request_at: Optional[float]) -> float:
    """Sleep so consecutive outbound YouTube calls stay `delay` apart.

    The project rule is a minimum 2s gap once a batch exceeds five external
    calls, and a sweep makes one or more per channel across fifty-two of them.
    Returns the timestamp to pass in next time.
    """
    if last_request_at is not None:
        elapsed = time.monotonic() - last_request_at
        if elapsed < delay:
            time.sleep(delay - elapsed)
    return time.monotonic()
