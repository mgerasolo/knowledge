"""Single-video enrollment — ingest one video without enrolling its channel (#46).

The channel pipeline exists for creators we follow wholesale. A personality
corpus needs more than that: Myron Golden interviewed on someone else's show is
corpus material, but the host's channel is not. This module runs exactly one
video through the same per-item pipeline the channel path uses — transcript →
file on disk → search index → state — and stamps it with the corpus tags
(e.g. ``personality:myron-golden``) that make it findable independent of its
channel.

Deliberately reuses fetcher.py's pieces rather than duplicating them: the file
layout, the state files, the blocked-request handling and the index payload are
all the same code, so a single-enrolled video is indistinguishable from a
channel-discovered one everywhere downstream except for its tags.
"""
import re
import subprocess
from datetime import datetime, timezone

import requests

from config import Config
from fetcher import (
    TranscriptBlocked,
    YTDLP_SINGLE_VIDEO_ARGS,
    _index_video,
    fetch_transcript,
    load_state,
    load_video_list,
    save_state,
    save_transcript_file,
    save_video_list,
    ytdlp_base_cmd,
)

# A YouTube video ID is exactly 11 characters from this alphabet. Anchored so
# that a 12-character string cannot half-match.
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# The URL shapes people actually paste: share links (youtu.be, with ?si=
# tracking junk), watch pages, shorts, live pages, and embeds.
_URL_PATTERNS = [
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
    re.compile(r"[?&]v=([A-Za-z0-9_-]{11})"),
    re.compile(r"/shorts/([A-Za-z0-9_-]{11})"),
    re.compile(r"/live/([A-Za-z0-9_-]{11})"),
    re.compile(r"/embed/([A-Za-z0-9_-]{11})"),
]

# Corpus tags are lowercase namespaced slugs: "personality:myron-golden",
# "topic:sales". The alphabet is restricted because tags flow into SurrealQL
# statements and YAML frontmatter; a tag that needs escaping is a tag that
# will eventually be escaped wrong somewhere.
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9:._-]{0,79}$")

# Streams that have not finished have no captions YET. Enrolling one must say
# "come back later", never "this video has no transcript" — the second gets
# written to the permanent failed list and blacklists the video forever.
UNFINISHED_STREAM = ("is_live", "is_upcoming", "post_live")


class EnrollError(ValueError):
    """Bad input to an enrollment request — the caller's fault, HTTP 400."""


def extract_video_id(text: str) -> str:
    """The 11-character video ID out of whatever the caller pasted.

    Accepts a bare ID or any of the URL shapes above. Raises EnrollError on
    anything else rather than guessing — an 11-character substring of a wrong
    URL silently enrolls the wrong video.
    """
    candidate = (text or "").strip()
    if not candidate:
        raise EnrollError("missing video_id or url")
    if _VIDEO_ID_RE.match(candidate):
        return candidate
    for pattern in _URL_PATTERNS:
        match = pattern.search(candidate)
        if match:
            return match.group(1)
    raise EnrollError(f"could not find a YouTube video id in: {candidate[:120]}")


def normalize_tags(tags) -> list[str]:
    """Validate and canonicalize the caller's tag list.

    Lowercases and strips, then rejects the whole request if any tag survives
    outside the allowed shape — a half-applied tag list is worse than a
    rejected one, because nobody re-checks a request that returned 200.
    """
    if tags is None:
        return []
    if not isinstance(tags, list):
        raise EnrollError("tags must be a list of strings")
    cleaned, bad = [], []
    for tag in tags:
        text = str(tag).strip().lower()
        if not text:
            continue
        if TAG_RE.match(text):
            if text not in cleaned:
                cleaned.append(text)
        else:
            bad.append(str(tag)[:80])
    if bad:
        raise EnrollError(
            "invalid tags (want lowercase slugs like personality:myron-golden): "
            + ", ".join(bad)
        )
    return cleaned


def fetch_video_metadata(video_id: str) -> dict:
    """One yt-dlp call → everything the pipeline wants to know about the video.

    Unlike the channel path, a single enrollment has no channel config to lean
    on — title, channel handle and channel name all have to come from the video
    itself. Same call also brings the fields the channel path collects
    (duration, counts, live status, chapters, description), so an enrolled
    guest appearance carries the same metadata as a discovered upload.
    """
    fields = [
        "title", "uploader_id", "channel", "upload_date", "duration",
        "view_count", "like_count", "live_status", "chapters", "description",
    ]
    cmd = ytdlp_base_cmd() + YTDLP_SINGLE_VIDEO_ARGS + [
        "--skip-download",
        # Description last and on its own --print: it is multi-line free text,
        # so anything printed after it could not be told apart from its body.
        *sum(([("--print"), f"%({f})j" if f == "chapters" else f"%({f})s"]
              for f in fields), []),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    empty = {f: "" for f in fields}
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return empty
    if res.returncode != 0:
        return empty

    lines = res.stdout.split("\n")
    out = dict(empty)
    for i, field in enumerate(fields[:-1]):
        value = lines[i].strip() if i < len(lines) else ""
        out[field] = "" if value in ("NA", "None", "null") else value
    out["description"] = "\n".join(lines[len(fields) - 1:]).strip()
    return out


def _channel_handle(metadata: dict) -> str:
    """yt-dlp's uploader_id ("@MyronGolden") → our handle form ("myrongolden")."""
    handle = (metadata.get("uploader_id") or "").strip().lstrip("@")
    return handle.lower() if handle else "unknown"


def _register_in_video_list(video: dict) -> None:
    """Add the video to the master list so status math stays honest.

    get_status() computes pending as total - fetched - failed - skipped; a
    fetched video the list has never heard of makes those numbers drift apart.
    """
    video_list = load_video_list()
    known = {v["id"] for v in video_list.get("videos", [])}
    if video["id"] in known:
        return
    entry = {
        key: video[key]
        for key in ("id", "title", "upload_date", "channel_handle",
                    "channel_name", "domain")
    }
    entry["enrolled"] = "single-video"
    video_list.setdefault("videos", []).append(entry)
    video_list["total_videos"] = len(video_list["videos"])
    video_list["last_single_enroll"] = datetime.now(timezone.utc).isoformat()
    save_video_list(video_list)


def push_tags(video_id: str, tags: list[str]) -> tuple[bool, str | None]:
    """Merge corpus tags onto the video's search-index record.

    The embedding service owns every SurrealDB write, so tags go through it
    too — one write path, one place to get the merge right.
    """
    try:
        r = requests.post(
            f"{Config.EMBEDDING_SERVICE_URL}/api/video/{video_id}/tags",
            json={"tags": tags},
            timeout=30,
        )
    except Exception as e:
        return False, f"embedding service unreachable: {e}"
    if not r.ok:
        try:
            detail = r.json().get("error", "")
        except ValueError:
            detail = ""
        return False, f"tag write returned HTTP {r.status_code}: {detail}"
    return True, None


def enroll_video(video_ref: str, tags=None, domain: str = None) -> tuple[dict, int]:
    """Run one video through the normal per-item pipeline, with corpus tags.

    Returns (result, http_status). Raises EnrollError for bad input.

    Outcomes a caller must be able to tell apart:
      200 — ingested (or already held; tags still applied)
      404 — yt-dlp could not read the video at all (bad id, private, deleted)
      409 — a stream that has not finished; retry after it ends
      422 — readable video, but no captions exist
      429 — YouTube is rate-limiting caption requests; retry later
    """
    video_id = extract_video_id(video_ref)
    tags = normalize_tags(tags)
    domain = (domain or "general").strip() or "general"

    # Already in the library: don't re-fetch (caption requests are the
    # rate-limited resource), just make sure the tags land.
    state = load_state()
    if video_id in state.get("fetched", []):
        result = {
            "success": True,
            "video_id": video_id,
            "already_fetched": True,
            "message": "Already in the library — tags applied to the index",
        }
        if tags:
            applied, err = push_tags(video_id, tags)
            result["tags_applied"] = applied
            if err:
                result["tags_error"] = err
        return result, 200

    metadata = fetch_video_metadata(video_id)
    if not metadata.get("title"):
        return {
            "success": False,
            "video_id": video_id,
            "error": "yt-dlp could not read this video (bad id, private, or removed)",
        }, 404

    live_status = metadata.get("live_status", "")
    if live_status in UNFINISHED_STREAM:
        return {
            "success": False,
            "video_id": video_id,
            "deferred": True,
            "error": f"stream has not finished ({live_status}) — captions do not "
                     "exist yet; enroll it again after it ends",
        }, 409

    try:
        segments = fetch_transcript(video_id)
    except TranscriptBlocked as e:
        return {
            "success": False,
            "video_id": video_id,
            "blocked": True,
            "error": f"YouTube is rate-limiting caption requests: {e}",
        }, 429

    if not segments:
        # Readable, finished video with no captions: record it so nothing
        # retries forever, exactly as the channel path would.
        state = load_state()
        if video_id not in state.setdefault("failed", []):
            state["failed"].append(video_id)
        save_state(state)
        return {
            "success": False,
            "video_id": video_id,
            "error": "No transcript available",
        }, 422

    video = {
        "id": video_id,
        "title": metadata["title"],
        "channel_handle": _channel_handle(metadata),
        "channel_name": metadata.get("channel") or _channel_handle(metadata),
        "domain": domain,
        "upload_date": metadata.get("upload_date") or "NA",
        "tags": tags,
        # Keys read by fetcher.index_metadata() and written to frontmatter —
        # load-bearing names, same as the channel path uses.
        "extra_metadata": {
            k: metadata.get(k, "") for k in
            ("duration", "view_count", "like_count", "live_status", "chapters")
            if metadata.get(k)
        },
    }

    filepath = save_transcript_file(video, segments, metadata.get("description") or None)

    # Re-read state immediately before writing — the backfill worker writes the
    # same file, and a stale copy would drop its work.
    state = load_state()
    if video_id not in state.setdefault("fetched", []):
        state["fetched"].append(video_id)
    if video_id in state.get("failed", []):
        state["failed"].remove(video_id)
    save_state(state)

    _register_in_video_list(video)

    indexed, index_error = _index_video(
        video, segments, metadata.get("description") or None
    )

    result = {
        "success": True,
        "video_id": video_id,
        "title": video["title"],
        "channel_handle": video["channel_handle"],
        "file_path": filepath,
        "segment_count": len(segments),
        "indexed": indexed,
        "index_error": index_error,
        "tags": tags,
    }
    if tags:
        applied, err = push_tags(video_id, tags)
        result["tags_applied"] = applied
        if err:
            result["tags_error"] = err
    return result, 200
