"""
Transcript fetching and discovery logic.

Extracted and adapted from spike/surreal-rag/scripts/batch_transcript_fetcher.py
for use as a service rather than CLI tool.
"""

import ast
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

try:  # present in current versions; guarded so an older lib still imports
    from youtube_transcript_api._errors import IpBlocked, RequestBlocked
    _BLOCKED_ERRORS = (IpBlocked, RequestBlocked)
except ImportError:  # pragma: no cover
    _BLOCKED_ERRORS = ()

from config import Config
from channel_feed import (
    BLOCK_PHRASES,
    FeedUnavailable,
    feed_videos_for_handle,
)


class TranscriptBlocked(Exception):
    """YouTube refused the caption request from this IP (HTTP 429 / "Sorry...").

    This is a temporary network-level block, NOT a statement about the video.
    It must never be recorded as a permanent failure: on 2026-08-14 the caption
    endpoint 429'd our whole WAN address while videos that definitely have
    English auto-captions came back looking transcript-less. Marking those
    "failed" would have blacklisted them from every future run.
    """


# ---- State Management ----

def _state_path() -> Path:
    return Path(Config.STATE_DIR) / "fetch_state.json"


def _video_list_path() -> Path:
    return Path(Config.STATE_DIR) / "video_list.json"


def load_state() -> dict:
    """Load fetch state from file."""
    path = _state_path()
    if path.exists():
        return json.loads(path.read_text())
    return {"fetched": [], "failed": [], "skipped": []}


def save_state(state: dict):
    """Save fetch state to file."""
    Path(Config.STATE_DIR).mkdir(parents=True, exist_ok=True)
    _state_path().write_text(json.dumps(state, indent=2))


def load_video_list() -> dict:
    """Load the full video list."""
    path = _video_list_path()
    if path.exists():
        return json.loads(path.read_text())
    return {"discovered_at": None, "total_videos": 0, "videos": []}


def save_video_list(data: dict):
    """Save the video list."""
    Path(Config.STATE_DIR).mkdir(parents=True, exist_ok=True)
    _video_list_path().write_text(json.dumps(data, indent=2))


def get_status() -> dict:
    """Get overall ingestion status."""
    state = load_state()
    video_list = load_video_list()

    fetched = len(state.get("fetched", []))
    failed = len(state.get("failed", []))
    skipped = len(state.get("skipped", []))
    total = video_list.get("total_videos", 0)
    pending = total - fetched - failed - skipped

    return {
        "total_videos": total,
        "fetched": fetched,
        "failed": failed,
        "skipped": skipped,
        "pending": max(0, pending),
        "discovered_at": video_list.get("discovered_at"),
        "channels": len(Config.CHANNELS),
    }


def get_pending(limit: int = 8) -> list[dict]:
    """Get the next N pending videos for backfill."""
    state = load_state()
    video_list = load_video_list()

    processed_ids = set(
        state.get("fetched", [])
        + state.get("failed", [])
        + state.get("skipped", [])
    )

    pending = [
        v for v in video_list.get("videos", []) if v["id"] not in processed_ids
    ]

    return pending[:limit]


# ---- Video Discovery ----

def discover_channel(handle: str, lookback_months: int) -> list[dict]:
    """Discover videos from a single channel using yt-dlp."""
    url = f"https://www.youtube.com/@{handle}/videos"

    cmd = ytdlp_base_cmd() + [
        "--flat-playlist",
        "--print",
        "%(id)s|%(title)s|%(upload_date)s",
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return []

        videos = []
        cutoff_date = datetime.now() - timedelta(days=lookback_months * 30)

        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue

            parts = line.split("|", 2)
            if len(parts) >= 3:
                video_id, title, upload_date = parts[0], parts[1], parts[2]

                try:
                    if upload_date and upload_date != "NA":
                        vid_date = datetime.strptime(upload_date, "%Y%m%d")
                        if vid_date < cutoff_date:
                            continue
                except ValueError:
                    pass

                videos.append(
                    {"id": video_id, "title": title, "upload_date": upload_date}
                )

        return videos

    except (subprocess.TimeoutExpired, Exception):
        return []


def _ytdlp_tab_listing(handle: str, tab: str, listing_cap: int, date_after: str) -> list[dict]:
    """List one channel tab with yt-dlp. Raises on failure; caller records it.

    This is the fallback path now — the RSS feed is tried first — but it stays
    the only DEPENDABLE way to see /streams. The feed does carry livestreams,
    but only the newest handful of a channel's uploads of any kind, and it
    answers barely a quarter of the time.
    """
    url = f"https://www.youtube.com/@{handle}/{tab}"
    cmd = ytdlp_base_cmd() + [
        "--flat-playlist",
        "--playlist-end",
        str(listing_cap),
        "--dateafter",
        date_after,   # inert in flat mode; kept only for when that changes
        "--print",
        "%(id)s|%(title)s|%(upload_date)s",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(
            (result.stderr or "yt-dlp exited non-zero").strip().splitlines()[-1][:200]
        )

    entries = []
    for line in result.stdout.strip().split("\n"):
        if not line or "|" not in line:
            continue
        # Split from BOTH ends, not left-to-right. A pipe is a normal character
        # in a YouTube title ("Optimize Female Hormone Health | Dr. Sara
        # Gottfried") and a plain split("|", 2) hands that tail to upload_date,
        # which then fails the 8-digit check in save_transcript_file and files
        # the transcript under <channel>/unknown/ with no date at all. Ten of
        # the first ten Huberman uploads listed on 2026-08-14 hit this. The ID
        # never contains a pipe and neither does the date, so anchoring on the
        # first and last separators is exact.
        video_id, _, rest = line.partition("|")
        title, _, upload_date = rest.rpartition("|")
        if not title:
            continue
        entries.append(
            {
                "id": video_id,
                "title": title,
                "upload_date": upload_date.strip(),
            }
        )
    return entries


def discover_new_videos(lookback_days: int = 7, on_progress=None) -> dict:
    """Check all channels for new videos not yet in our state.

    Returns dict with new_videos list and per-channel stats.

    DISCOVERY PATHS — the feed first, the scraper wherever the feed can't be
    trusted:

    Each channel's recent uploads are read from its static RSS feed, which costs
    one small XML request and no scraping. yt-dlp is the fallback, used when the
    handle cannot be resolved to a channel ID, when the feed request fails or
    comes back empty, or for any tab beyond the feed's shallow window.

    /streams is always one of those tabs. Every channel configured with it —
    roughly a third of the list — gets its yt-dlp pass no matter how well the
    feed worked. Not because the feed omits livestreams; it includes them. It is
    that the feed holds only ~15 items of any kind and answers a minority of the
    time, so making livestream discovery depend on it would re-create the blind
    spot fixed on 2026-08-13, where a channel with hundreds of missing sermons
    looked exactly like a channel that had nothing new.

    Every channel records which path it took, so "is RSS actually working?" is a
    question the logs answer rather than one you infer from video counts.

    `on_progress(index, total, handle)` is called before each channel so a
    long-running discovery can keep a liveness heartbeat fresh — a full sweep of
    50 channels takes several minutes, which otherwise looks like a hung worker.

    IMPORTANT — why this looks at only the newest N uploads per channel:
    `--dateafter` does NOT work with `--flat-playlist`, because flat mode never
    populates upload_date (yt-dlp prints "NA"). The date filter is therefore
    silently inert, and a sweep returns each channel's ENTIRE back catalogue.
    On 2026-08-07 that queued 40,072 videos in one run — months of fetching and
    an unreasonable scraping load — instead of the intended two weeks of new
    uploads. Channels list newest-first, so capping the listing with
    `--playlist-end` is what actually bounds this.
    """
    state = load_state()
    video_list = load_video_list()

    processed_ids = set(
        state.get("fetched", [])
        + state.get("failed", [])
        + state.get("skipped", [])
    )
    known_ids = {v["id"] for v in video_list.get("videos", [])}

    new_videos = []
    channel_stats = []

    # Discovery hits YouTube once per channel (50 of them). The project rule is a
    # minimum 2s gap when making more than 5 external calls in a batch; without
    # it this loop fires ~50 requests back to back and risks throttling.
    discovery_delay = float(os.getenv("DISCOVERY_DELAY_SECONDS", "3"))

    # How many of each channel's most recent uploads to consider. This — not
    # --dateafter — is what keeps a sweep bounded. Anything already known is
    # skipped, so this only needs to exceed a channel's upload rate between
    # runs, with generous headroom.
    listing_cap = int(os.getenv("DISCOVERY_PLAYLIST_END", "25"))

    # RSS is the primary path. It can be forced off, and it switches itself off
    # for the rest of a sweep after a run of failures: when YouTube stops
    # serving feeds at all — which it does, see the module docstring in
    # channel_feed.py — there is no point paying a doomed request on every one
    # of fifty-two channels before falling back each time. The counter resets
    # every sweep, so a recovered endpoint is picked up within one cycle with no
    # deploy and no human noticing.
    rss_enabled = os.getenv("DISCOVERY_USE_RSS", "true").lower() not in (
        "false", "0", "no"
    )
    rss_failure_budget = int(os.getenv("DISCOVERY_RSS_MAX_FAILURES", "3"))
    consecutive_feed_failures = 0

    # One shared pacer across BOTH paths. Every outbound YouTube call in a sweep
    # — feed, channel-page resolution, yt-dlp listing — is spaced by it, so
    # swapping a yt-dlp call for a feed call cannot quietly raise our request
    # rate. Nothing sleeps before the very first call of the sweep.
    requested_any = False

    def _space_request():
        nonlocal requested_any
        if requested_any:
            time.sleep(discovery_delay)
        requested_any = True

    total_channels = len(Config.CHANNELS)
    for index, channel in enumerate(Config.CHANNELS):
        handle = channel["handle"]
        if on_progress:
            on_progress(index + 1, total_channels, handle)
        date_after = (
            datetime.now() - timedelta(days=lookback_days)
        ).strftime("%Y%m%d")

        # Most channels publish to /videos. Some publish to /streams instead —
        # a church that livestreams every sermon has an almost-empty /videos tab
        # and hundreds of streams. Per-channel opt-in so the common case still
        # costs exactly one request.
        tabs = channel.get("tabs") or ["videos"]

        candidates = []      # {id, title, upload_date, extra_metadata?}
        paths = []           # which mechanism actually produced the listing
        errors = []
        blocked = False
        # Tabs yt-dlp still has to cover. The feed can only ever retire
        # "videos"; "streams" stays on this list unconditionally.
        pending_tabs = list(tabs)

        if (
            rss_enabled
            and "videos" in tabs
            and consecutive_feed_failures < rss_failure_budget
        ):
            _space_request()
            try:
                feed = feed_videos_for_handle(handle, limit=listing_cap)
            except FeedUnavailable as e:
                consecutive_feed_failures += 1
                errors.append(f"rss: {e}")
                blocked = blocked or e.blocked
                if consecutive_feed_failures == rss_failure_budget:
                    print(
                        f"[discovery] RSS disabled for the rest of this sweep "
                        f"after {rss_failure_budget} consecutive feed failures "
                        f"(last: {handle} — {e}). Falling back to yt-dlp.",
                        flush=True,
                    )
            except Exception as e:  # never let discovery die on the new path
                consecutive_feed_failures += 1
                errors.append(f"rss: unexpected {type(e).__name__}: {e}")
            else:
                consecutive_feed_failures = 0
                pending_tabs.remove("videos")
                paths.append("rss")
                for entry in feed["videos"]:
                    # View and like counts ride along free — the feed already
                    # carries them, so they cost no extra request.
                    extra = {
                        key: value
                        for key, value in (
                            ("view_count", entry.get("view_count")),
                            ("like_count", entry.get("like_count")),
                        )
                        if value is not None
                    }
                    candidates.append(
                        {
                            "id": entry["id"],
                            "title": entry["title"],
                            "upload_date": entry["upload_date"],
                            "extra_metadata": extra or None,
                        }
                    )

        for tab in pending_tabs:
            _space_request()
            try:
                candidates.extend(
                    _ytdlp_tab_listing(handle, tab, listing_cap, date_after)
                )
                paths.append(f"yt-dlp:{tab}")
            except (subprocess.TimeoutExpired, Exception) as e:
                errors.append(f"{tab}: {e}")

        found = 0
        new_count = 0
        for entry in candidates:
            found += 1
            video_id = entry["id"]
            if video_id in processed_ids or video_id in known_ids:
                continue
            video = {
                "id": video_id,
                "title": entry["title"],
                "upload_date": entry["upload_date"],
                "channel_handle": handle,
                "channel_name": channel["name"],
                "domain": channel["domain"],
            }
            if entry.get("extra_metadata"):
                video["extra_metadata"] = entry["extra_metadata"]
            new_videos.append(video)
            known_ids.add(video_id)  # tabs and the feed overlap
            new_count += 1

        stat = {
            "handle": handle,
            "name": channel["name"],
            "recent_videos": found,
            "new_videos": new_count,
            # "rss", "rss+yt-dlp:streams", "yt-dlp:videos" — the answer to
            # "did RSS actually work?" without inferring it from counts.
            "path": "+".join(paths) if paths else "none",
        }
        if errors:
            stat["error"] = "; ".join(errors)
        if blocked:
            stat["blocked"] = True
        channel_stats.append(stat)

    # Safety valve. A single sweep should surface tens of new uploads, not
    # thousands; anything larger means a filter broke (as --dateafter silently
    # did on 2026-08-07, queueing 40,072). Refuse the run rather than commit a
    # queue that would take months to drain and hammer YouTube doing it.
    max_new = int(os.getenv("DISCOVERY_MAX_NEW", "500"))
    if len(new_videos) > max_new:
        print(
            f"[discovery] ABORTED: {len(new_videos)} new videos exceeds the "
            f"{max_new} limit — this indicates a broken filter, not a real "
            f"backlog. Nothing was added. Raise DISCOVERY_MAX_NEW deliberately "
            f"if a bulk import is actually intended.",
            flush=True,
        )
        return {
            "new_videos": [],
            "channels_checked": len(channel_stats),
            "channel_stats": channel_stats,
            "aborted": True,
            "would_have_added": len(new_videos),
        }

    # Add new videos to the master list
    if new_videos:
        existing_videos = video_list.get("videos", [])
        existing_videos.extend(new_videos)
        video_list["videos"] = existing_videos
        video_list["total_videos"] = len(existing_videos)
        video_list["last_discovery"] = datetime.now().isoformat()
        save_video_list(video_list)

    return {
        "new_videos": new_videos,
        "new_count": len(new_videos),
        "channel_stats": channel_stats,
        "checked_at": datetime.now().isoformat(),
    }


# ---- Transcript Fetching ----

def _format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _proxy_config():
    """Return the configured proxy config object, or None to go direct.

    Webshare credentials win over a raw URL: the vendor class knows to use the
    rotating endpoint and to rotate to a fresh IP on a blocked request, which a
    hand-built URL does not do.
    """
    try:
        from youtube_transcript_api.proxies import (
            GenericProxyConfig,
            WebshareProxyConfig,
        )
    except ImportError:  # pragma: no cover — very old lib
        if Config.WEBSHARE_PROXY_USERNAME or Config.YOUTUBE_PROXY_URL:
            print("[fetcher] proxy configured but this youtube-transcript-api "
                  "has no proxy support; going direct", flush=True)
        return None

    if Config.WEBSHARE_PROXY_USERNAME and Config.WEBSHARE_PROXY_PASSWORD:
        locations = [
            code.strip().upper()
            for code in Config.WEBSHARE_PROXY_LOCATIONS.split(",")
            if code.strip()
        ]
        return WebshareProxyConfig(
            proxy_username=Config.WEBSHARE_PROXY_USERNAME,
            proxy_password=Config.WEBSHARE_PROXY_PASSWORD,
            filter_ip_locations=locations or None,
        )

    if Config.YOUTUBE_PROXY_URL:
        return GenericProxyConfig(
            http_url=Config.YOUTUBE_PROXY_URL,
            https_url=Config.YOUTUBE_PROXY_URL,
        )

    return None


def proxy_status() -> dict:
    """Describe the proxy setup without ever revealing the credential."""
    if Config.WEBSHARE_PROXY_USERNAME and Config.WEBSHARE_PROXY_PASSWORD:
        mode = "webshare"
    elif Config.YOUTUBE_PROXY_URL:
        mode = "generic"
    else:
        mode = "direct"
    return {
        "mode": mode,
        "scope": Config.YOUTUBE_PROXY_SCOPE if mode != "direct" else None,
        "locations": Config.WEBSHARE_PROXY_LOCATIONS if mode == "webshare" else None,
    }


def _transcript_api() -> YouTubeTranscriptApi:
    """Build the API client, routed through the proxy when one is configured."""
    config = _proxy_config()
    return YouTubeTranscriptApi(proxy_config=config) if config else YouTubeTranscriptApi()


# Flags every SINGLE-VIDEO yt-dlp call needs on this host.
#
# Without them, yt-dlp falls back to a client that answers "This video is not
# available", and since the callers treat a failed metadata call as "no
# metadata", videos silently land with no publish date and no description —
# dateless files pile up in <channel>/unknown/ and the descriptions (which for
# many creators carry links and resources never spoken aloud) are lost.
#
#   --ignore-no-formats-error : we only ever want metadata; yt-dlp otherwise
#       aborts the whole extraction when no downloadable format is available,
#       which is every video here since there is no JS runtime to solve the
#       format challenge.
#   player_client=web         : the default client chain needs that JS runtime.
#       The web client returns full metadata without one.
#
# Not applied to --flat-playlist listing calls, which work fine as-is and are
# hit far more often.
YTDLP_SINGLE_VIDEO_ARGS = [
    "--ignore-no-formats-error",
    "--extractor-args", "youtube:player_client=web",
]


def ytdlp_base_cmd() -> list[str]:
    """yt-dlp invocation prefix, carrying the proxy only when scope says so.

    Every yt-dlp call goes through this, so the proxy decision is made in one
    place rather than being applied to the transcript fetch and silently missed
    on the listing and description calls.

    Default scope is 'transcript', which means yt-dlp goes DIRECT: only the
    caption endpoint is rate-limited, and metadata pages are orders of magnitude
    larger than transcripts on a per-gigabyte bill.
    """
    cmd = ["yt-dlp"]
    if Config.YOUTUBE_PROXY_SCOPE != "all":
        return cmd
    config = _proxy_config()
    if config is not None:
        cmd += ["--proxy", config.url if hasattr(config, "url") else Config.YOUTUBE_PROXY_URL]
    return cmd


def fetch_transcript(video_id: str) -> Optional[list[dict]]:
    """Fetch transcript segments for a single video.

    Returns None when the video genuinely has no usable transcript.
    Raises TranscriptBlocked when YouTube is refusing US, so the caller can
    back off and retry instead of condemning the video.
    """
    try:
        api = _transcript_api()
        transcript = api.fetch(video_id)

        segments = []
        for entry in transcript:
            segments.append(
                {
                    "text": entry.text,
                    "start": entry.start,
                    "duration": entry.duration,
                }
            )
        return segments

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except _BLOCKED_ERRORS as e:
        raise TranscriptBlocked(str(e)[:200]) from e
    except Exception as e:
        # Anything that is about the CONNECTION rather than the VIDEO is
        # retryable and must not be written to the permanent failed list.
        # Proxy faults are the dangerous case: a wrong password, an exhausted
        # bandwidth quota or a dead upstream would otherwise quietly convert
        # every video in the queue into "this one has no captions".
        text = str(e)
        lowered = text.lower()
        # YouTube serves its "prove you're not a bot" interstitial as a SUCCESS
        # response with the challenge in the body, not as an error status. Only
        # matching on 429 therefore misses it entirely, and the video would be
        # written to the permanent failed list — the exact outcome
        # TranscriptBlocked exists to prevent.
        bot_challenge = any(phrase in lowered for phrase in BLOCK_PHRASES)
        retryable = (
            bot_challenge
            or "429" in text
            or "Too Many Requests" in text
            or "407" in text
            or "ProxyError" in type(e).__name__
            or "Tunnel connection failed" in text
            or "Proxy Authentication Required" in text
            or isinstance(e, (requests.exceptions.ProxyError,
                              requests.exceptions.ConnectionError,
                              requests.exceptions.Timeout))
        )
        if retryable:
            raise TranscriptBlocked(f"{type(e).__name__}: {text[:180]}") from e
        return None


def fetch_description(video_id: str) -> Optional[str]:
    """Fetch video description using yt-dlp."""
    try:
        cmd = ytdlp_base_cmd() + YTDLP_SINGLE_VIDEO_ARGS + [
            "--skip-download",
            "--print",
            "%(description)s",
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


# The publication date written when YouTube did not tell us when a video went
# out. Deliberately the epoch rather than anything plausible: the indexer used
# to substitute 2026-01-01 for a missing date, which reads as a real January
# publication and quietly corrupted every date-sorted query instead of
# announcing itself. An unknown date should look unknown. Same sentinel
# scripts/reindex_from_files.py already uses, so a replay agrees with a fetch.
UNKNOWN_PUBLISHED = "1970-01-01"


def published_date(upload_date) -> str:
    """The YYYYMMDD yt-dlp and the RSS feed report -> the date the index wants."""
    text = str(upload_date or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return UNKNOWN_PUBLISHED


def transcript_duration(segments: list[dict]) -> float:
    """How long the captions run, in seconds."""
    if not segments:
        return 0.0
    last = segments[-1]
    return last["start"] + last.get("duration", 0)


def _as_number(value, cast):
    """Coerce a metadata value, tolerating however its collector spelled it.

    The RSS feed hands over real numbers, yt-dlp hands over strings, and both
    use "NA" and "" for absent. Returns None when there is genuinely no value,
    which is not the same as zero and must not be stored as zero.
    """
    if value in (None, "", "NA"):
        return None
    try:
        return cast(float(value))
    except (TypeError, ValueError):
        return None


def parse_chapters(value) -> list:
    """Chapter markers, however the collecting path happened to store them.

    yt-dlp is asked for chapters as JSON (`%(chapters)j`), so the priority
    ingest path holds them as a string; anything reading them back off a
    transcript file may find the older single-quoted form that predates this
    being written as JSON. Both parse; anything else yields no chapters rather
    than a half-read one.
    """
    if not value:
        return []
    if isinstance(value, list):
        return value
    for load in (json.loads, ast.literal_eval):
        try:
            parsed = load(value)
        except (TypeError, ValueError, SyntaxError):
            continue
        if isinstance(parsed, list):
            return parsed
    return []


def index_metadata(video: dict, segments: list[dict]) -> dict:
    """The metadata half of the indexer payload.

    Every field here was already being collected and written to the transcript
    file, and none of it was being sent. The indexer therefore applied its own
    defaults and stored a zero view count, no chapters and a made-up
    publication date for every video that came through here (#17).

    Normalising happens once, here, because the two ingest paths disagree about
    spelling: the feed supplies counts as numbers, yt-dlp supplies everything as
    strings and calls the video's length `duration`.
    """
    extra = video.get("extra_metadata") or {}

    # yt-dlp's duration is the video's true length. The last caption timestamp
    # is only a floor on it — captions routinely stop before the video does —
    # so it is the fallback, not the preference.
    duration = _as_number(extra.get("duration"), float)
    if duration is None:
        duration = transcript_duration(segments)

    meta = {
        "published_at": published_date(video.get("upload_date")),
        "duration_seconds": duration,
        "chapters": parse_chapters(extra.get("chapters")),
    }
    for key in ("view_count", "like_count"):
        count = _as_number(extra.get(key), int)
        if count is not None:
            meta[key] = count

    live_status = str(extra.get("live_status") or "").strip()
    if live_status and live_status != "NA":
        meta["live_status"] = live_status

    return meta


def save_transcript_file(video: dict, segments: list[dict], description: Optional[str] = None) -> str:
    """Save transcript as markdown file. Returns the file path."""
    transcript_dir = Path(Config.TRANSCRIPT_DIR)
    channel_handle = video.get("channel_handle", "unknown").lower()
    channel_dir = transcript_dir / channel_handle

    # Parse upload date for directory structure
    upload_date = video.get("upload_date", "unknown")
    if upload_date and upload_date != "NA" and len(upload_date) == 8:
        year_month = f"{upload_date[:4]}-{upload_date[4:6]}"
        date_dir = channel_dir / year_month
        published_str = (
            f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        )
    else:
        date_dir = channel_dir / "unknown"
        published_str = "unknown"

    date_dir.mkdir(parents=True, exist_ok=True)

    # Create safe filename
    title = video.get("title", "untitled")
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "" for c in title
    )
    safe_title = safe_title[:80].strip().replace(" ", "-").lower()
    filename = f"{safe_title}.md"
    filepath = date_dir / filename

    # Format transcript with timestamps
    transcript_lines = []
    for seg in segments:
        ts = _format_timestamp(seg["start"])
        transcript_lines.append(f"[{ts}] {seg['text']}")
    transcript_body = "\n".join(transcript_lines)

    # Raw segments JSON for machine parsing
    segments_json = json.dumps(segments)

    # Build description YAML block
    desc_yaml = ""
    if description:
        desc_escaped = description.replace("\\", "\\\\")
        desc_yaml = (
            "\ndescription: |\n  "
            + desc_escaped.replace("\n", "\n  ")
        )

    # Channel name
    channel_name = video.get("channel_name", channel_handle)

    # Duration
    duration = transcript_duration(segments)

    escaped_title = title.replace('"', "'")

    # Extras (duration, view/like counts, live status, chapters) come free with
    # the metadata call we already make. They go into the file AND into the
    # index — see index_metadata().
    #
    # Chapters are written as the JSON they arrive as. Putting them through the
    # quote-swap below instead turned '{"title": "x"}' into "{'title': 'x'}",
    # which is unreadable the moment a chapter title contains an apostrophe,
    # and this file is the only copy if the index ever has to be replayed.
    extra_yaml = ""
    for key, value in (video.get("extra_metadata") or {}).items():
        if value in ("", None):
            continue
        text = str(value)
        if key != "chapters" and not text.isdigit():
            text = '"' + text.replace('"', "'") + '"'
        extra_yaml += f"\n{key}: {text}"

    content = f"""---
title: "{escaped_title}"
channel: "{channel_name}"
video_id: "{video['id']}"
published: "{published_str}"
url: "https://youtube.com/watch?v={video['id']}"
fetched: "{datetime.now().strftime('%Y-%m-%d')}"
domain: "{video.get('domain', 'unknown')}"
segment_count: {len(segments)}
duration_seconds: {duration:.1f}{extra_yaml}
tags: []{desc_yaml}
---

## Transcript

{transcript_body}

<!-- RAW_SEGMENTS
{segments_json}
-->
"""

    filepath.write_text(content)
    return str(filepath)


def fetch_and_save(video: dict) -> dict:
    """Fetch transcript for a video and save to disk. Updates state.

    Args:
        video: dict with at minimum 'id'. Optional: title, channel_handle,
               channel_name, domain, upload_date.

    Returns:
        dict with success, video_id, file_path, segment_count, error.
    """
    video_id = video["id"]
    state = load_state()

    # Check if already fetched
    if video_id in state.get("fetched", []):
        return {
            "success": True,
            "video_id": video_id,
            "already_fetched": True,
            "message": "Already fetched",
        }

    # Fetch transcript. A block is reported as a distinct, retryable outcome —
    # state is left untouched so the video comes back around on a later pass.
    try:
        segments = fetch_transcript(video_id)
    except TranscriptBlocked as e:
        return {
            "success": False,
            "video_id": video_id,
            "blocked": True,
            "error": f"YouTube is rate-limiting caption requests: {e}",
        }

    if not segments:
        state.setdefault("failed", []).append(video_id)
        save_state(state)
        return {
            "success": False,
            "video_id": video_id,
            "error": "No transcript available",
        }

    # Fetch description
    description = fetch_description(video_id)

    # Enrich video data if needed
    if not video.get("channel_handle"):
        video["channel_handle"] = "unknown"
    if not video.get("channel_name"):
        video["channel_name"] = video["channel_handle"]

    # Save to file
    filepath = save_transcript_file(video, segments, description)

    # Update state
    state.setdefault("fetched", []).append(video_id)
    # Remove from failed if it was there (retry succeeded)
    if video_id in state.get("failed", []):
        state["failed"].remove(video_id)
    save_state(state)

    # Push into the search index. Without this the file archive grows while the
    # searchable corpus does not — EMBEDDING_SERVICE_URL was configured in three
    # places and called from none, so everything this worker fetched was
    # invisible to every consumer of the API (found 2026-08-07).
    indexed, index_error = _index_video(video, segments, description)

    return {
        "success": True,
        "video_id": video_id,
        "file_path": filepath,
        "segment_count": len(segments),
        "has_description": description is not None,
        "indexed": indexed,
        "index_error": index_error,
    }


def _index_video(video: dict, segments: list, description) -> tuple:
    """Send a freshly fetched transcript to the embedding service.

    Returns (indexed, error). The transcript file is already safely on disk by
    this point, so an indexing failure is reported but not raised — the file can
    always be replayed later with scripts/reindex_from_files.py.
    """
    payload = {
        "video_id": video["id"],
        "title": video.get("title", ""),
        "url": f"https://youtube.com/watch?v={video['id']}",
        "channel_handle": video.get("channel_handle", "unknown"),
        "channel_name": video.get("channel_name", ""),
        "domain": video.get("domain", "general"),
        "description": description or "",
        "segments": segments,
        "skip_embeddings": True,   # no semantic search consumes embeddings yet
        # Length, view/like counts, chapters, live status and the real
        # publication date. Omitting these is what made the indexer fall back
        # to its own defaults and store zeros against every video (#17).
        **index_metadata(video, segments),
    }

    try:
        r = requests.post(
            f"{Config.EMBEDDING_SERVICE_URL}/api/embed",
            json=payload,
            timeout=120,
        )
    except Exception as e:
        return False, f"embedding service unreachable: {e}"

    if not r.ok:
        return False, f"embedding service returned HTTP {r.status_code}"

    try:
        body = r.json()
    except ValueError:
        return False, "embedding service response was not JSON"

    # embed_video() reports real write failures now, so trust its verdict
    # rather than the status code alone.
    if not body.get("success"):
        return False, str(body.get("error", "indexing reported failure"))
    return True, None
