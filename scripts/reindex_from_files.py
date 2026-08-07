#!/usr/bin/env python3
"""Rebuild the SurrealDB index from the transcript files on disk.

Why this exists
---------------
SurrealDB ran with the in-memory storage backend until 2026-08-05, so every
write it ever accepted was discarded and the `knowledge` namespace did not
exist. The transcript markdown files were never affected — they are the real
source of truth. This script replays them back into SurrealDB.

It is idempotent (UPSERT on a hash of the video id) and resumable: completed
video ids are appended to a state file, and a re-run skips them.

Embeddings are NOT generated. Semantic search is not implemented (`/api/search`
returns 501), so embedding ~360k chunks would cost real money and buy nothing
today. Run the embedding backfill separately once vector search actually ships.

Usage:
    python3 scripts/reindex_from_files.py            # index everything
    python3 scripts/reindex_from_files.py --limit 20 # smoke test
    python3 scripts/reindex_from_files.py --restart  # ignore prior progress
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

TRANSCRIPT_DIR = Path(os.getenv("TRANSCRIPT_DIR", "/mnt/foundry_resources/transcripts"))
SURREAL_URL = os.getenv("SURREAL_URL", "http://10.0.0.33:5040")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "changeme")
SURREAL_NS = os.getenv("SURREAL_NS", "knowledge")
SURREAL_DB = os.getenv("SURREAL_DB", "transcripts")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
STATEMENTS_PER_REQUEST = 200

STATE_FILE = Path(__file__).parent / ".reindex_progress.txt"
FAILURE_LOG = Path(__file__).parent / ".reindex_failures.log"

TIMESTAMP_RE = re.compile(r"^\[(\d+):(\d{2})(?::(\d{2}))?\]\s*(.*)$")

VISUAL_TRIGGERS = (
    "as you can see", "on screen", "on the screen", "look at this",
    "if you look at", "on my screen", "showing you", "let me show you",
    "you'll see here", "take a look",
)


# --------------------------------------------------------------------------
# SurrealDB
# --------------------------------------------------------------------------

def surreal(query: str):
    """POST a query. Returns (ok, error_message)."""
    try:
        r = requests.post(
            f"{SURREAL_URL}/sql",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
            },
            auth=(SURREAL_USER, SURREAL_PASS),
            data=query.encode("utf-8"),
            timeout=120,
        )
    except Exception as e:  # network-level
        return False, f"connection error: {e}"

    if not r.ok:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"

    try:
        payload = r.json()
    except Exception:
        return False, "response was not JSON"

    if not isinstance(payload, list):
        return False, "unexpected response shape"

    errors = [
        str(s.get("result", "unknown"))
        for s in payload
        if isinstance(s, dict) and s.get("status") == "ERR"
    ]
    if errors:
        # Same message repeats per statement; one copy is enough to diagnose.
        return False, errors[0]
    return True, None


def safe_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def esc(text: str) -> str:
    """Escape a string for embedding in a SurrealQL single-quoted literal."""
    if not text:
        return ""
    out = text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return "".join(c for c in out if ord(c) >= 32 or c in "\n\r\t")


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Split a transcript file into (frontmatter dict, body).

    Hand-rolled rather than using PyYAML: `description:` is a block scalar
    containing arbitrary user text (URLs, colons, quotes) and we want it kept
    verbatim rather than risk a parse error dropping the whole file.
    """
    if not raw.startswith("---"):
        return {}, raw

    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw

    header = raw[3:end]
    body = raw[end + 4:]

    meta: dict = {}
    key = None
    block_lines: list[str] = []
    in_block = False

    for line in header.splitlines():
        if in_block:
            # Block scalar continues while lines are indented (or blank).
            if line.startswith("  ") or not line.strip():
                block_lines.append(line[2:] if line.startswith("  ") else "")
                continue
            meta[key] = "\n".join(block_lines).strip()
            in_block, block_lines = False, []

        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$", line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()

        if value in ("|", ">", "|-", ">-"):
            in_block = True
            block_lines = []
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key] = value

    if in_block and key:
        meta[key] = "\n".join(block_lines).strip()

    return meta, body


def parse_segments(body: str) -> list[dict]:
    """Pull [M:SS] timestamped lines out of the transcript body."""
    marker = body.find("## Transcript")
    text = body[marker + len("## Transcript"):] if marker != -1 else body

    segments = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = TIMESTAMP_RE.match(line)
        if not m:
            continue
        mins, secs, maybe_secs, content = m.groups()
        if maybe_secs is not None:      # [H:MM:SS]
            start = int(mins) * 3600 + int(secs) * 60 + int(maybe_secs)
        else:                            # [M:SS]
            start = int(mins) * 60 + int(secs)
        if content:
            segments.append({"start": float(start), "text": content})

    # Derive each segment's end from the next one's start.
    for i, seg in enumerate(segments):
        seg["end"] = segments[i + 1]["start"] if i + 1 < len(segments) else seg["start"]
    return segments


def chunk_plain_text(body: str) -> list[dict]:
    """Chunk an untimed transcript by characters.

    ~200 of the older files store the transcript as plain prose with no [M:SS]
    markers. The text is complete, so they are indexed with zeroed times and the
    parent video flagged has_timestamps = false, rather than being dropped.
    """
    marker = body.find("## Transcript")
    text = body[marker + len("## Transcript"):] if marker != -1 else body
    text = " ".join(text.split())
    if not text:
        return []

    chunks: list[dict] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        piece = text[start:end]
        if end < len(text):
            cut = piece.rfind(". ")
            if cut > CHUNK_SIZE // 2:
                end = start + cut + 2
                piece = text[start:end]
        chunks.append({"text": piece.strip(), "start_time": 0.0,
                       "end_time": 0.0, "chunk_index": len(chunks)})
        start = end
    return chunks


def chunk(segments: list[dict]) -> list[dict]:
    """Group consecutive segments into ~CHUNK_SIZE character chunks."""
    if not segments:
        return []

    chunks: list[dict] = []
    texts: list[str] = []
    start = segments[0]["start"]
    end = segments[0]["end"]
    length = 0

    for seg in segments:
        if length + len(seg["text"]) > CHUNK_SIZE and texts:
            chunks.append({"text": " ".join(texts), "start_time": start,
                           "end_time": end, "chunk_index": len(chunks)})
            texts, start, length = [seg["text"]], seg["start"], len(seg["text"])
        else:
            texts.append(seg["text"])
            length += len(seg["text"]) + 1
        end = seg["end"]

    if texts:
        chunks.append({"text": " ".join(texts), "start_time": start,
                       "end_time": end, "chunk_index": len(chunks)})
    return chunks


def normalize_date(value: str) -> str:
    """Coerce a frontmatter `published` value into a SurrealDB date literal."""
    if not value or value == "unknown":
        return "1970-01-01"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    if re.fullmatch(r"\d{4}", value):
        return f"{value}-01-01"
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return f"{value}-01"
    return "1970-01-01"


# --------------------------------------------------------------------------
# Indexing
# --------------------------------------------------------------------------

def index_file(path: Path) -> tuple[bool, str | None, int]:
    """Index one transcript file. Returns (ok, error, segment_count)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(raw)

    video_id = meta.get("video_id", "").strip()
    if not video_id:
        return False, "no video_id in frontmatter", 0

    title = meta.get("title", path.stem)
    channel_name = meta.get("channel", "Unknown")
    # Directory name is the canonical handle; frontmatter `channel` is a display name.
    channel_handle = path.parent.parent.name
    domain = meta.get("domain", "general")
    published = normalize_date(meta.get("published", ""))
    url = meta.get("url", f"https://youtube.com/watch?v={video_id}")
    description = meta.get("description", "")
    try:
        duration = float(meta.get("duration_seconds", 0) or 0)
    except ValueError:
        duration = 0.0

    segments = parse_segments(body)
    has_timestamps = bool(segments)
    chunks = chunk(segments) if has_timestamps else chunk_plain_text(body)
    if not chunks:
        return False, "transcript body is empty", 0

    channel_id = safe_id(channel_handle.lower())
    video_db_id = safe_id(video_id)

    ok, err = surreal(f"""
    UPSERT channel:{channel_id} SET
        youtube_handle = '{esc(channel_handle)}',
        name = '{esc(channel_name)}',
        domain = '{esc(domain)}',
        ingested_at = time::now();
    """)
    if not ok:
        return False, f"channel write: {err}", 0

    ok, err = surreal(f"""
    UPSERT video:{video_db_id} SET
        youtube_id = '{esc(video_id)}',
        title = '{esc(title)}',
        description = '{esc(description)}',
        published_at = d'{published}',
        duration_seconds = {duration},
        url = '{esc(url)}',
        channel_handle = '{esc(channel_handle)}',
        channel_name = '{esc(channel_name)}',
        domain = '{esc(domain)}',
        transcript_path = '{esc(str(path))}',
        segment_count = {len(chunks)},
        has_timestamps = {str(has_timestamps).lower()},
        fetched_at = time::now(),
        ingested_at = time::now();
    RELATE channel:{channel_id}->has_video->video:{video_db_id};
    """)
    if not ok:
        return False, f"video write: {err}", 0

    # Segments, batched — one request per statement would mean ~360k round trips.
    statements: list[str] = []
    written = 0
    for c in chunks:
        seg_db_id = safe_id(f"{video_id}_{c['chunk_index']}")
        visual = any(t in c["text"].lower() for t in VISUAL_TRIGGERS)
        duration_s = max(0.0, c["end_time"] - c["start_time"])
        statements.append(f"""
        UPSERT segment:{seg_db_id} SET
            text = '{esc(c["text"])}',
            chunk_index = {c["chunk_index"]},
            start_time = {c["start_time"]},
            end_time = {c["end_time"]},
            duration = {duration_s},
            requires_visual = {str(visual).lower()},
            published_at = d'{published}',
            domain = '{esc(domain)}',
            video_youtube_id = '{esc(video_id)}',
            ingested_at = time::now();
        RELATE video:{video_db_id}->has_segment->segment:{seg_db_id}
            SET sequence = {c["chunk_index"]};
        """)

        if len(statements) >= STATEMENTS_PER_REQUEST:
            ok, err = surreal("\n".join(statements))
            if not ok:
                return False, f"segment batch: {err}", written
            written += len(statements)
            statements = []

    if statements:
        ok, err = surreal("\n".join(statements))
        if not ok:
            return False, f"segment batch: {err}", written
        written += len(statements)

    return True, None, len(chunks)


def load_done() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    return {l.strip() for l in STATE_FILE.read_text().splitlines() if l.strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only process N files")
    ap.add_argument("--restart", action="store_true", help="ignore prior progress")
    args = ap.parse_args()

    if args.restart:
        STATE_FILE.unlink(missing_ok=True)
        FAILURE_LOG.unlink(missing_ok=True)

    ok, err = surreal("INFO FOR DB;")
    if not ok:
        print(f"FATAL: cannot reach SurrealDB namespace '{SURREAL_NS}': {err}")
        return 1

    files = sorted(TRANSCRIPT_DIR.rglob("*.md"))
    done = load_done()
    todo = [f for f in files if str(f) not in done]
    if args.limit:
        todo = todo[: args.limit]

    print(f"transcripts on disk : {len(files)}")
    print(f"already indexed     : {len(done)}")
    print(f"to process this run : {len(todo)}")
    print(f"target              : {SURREAL_URL} ns={SURREAL_NS} db={SURREAL_DB}")
    print("-" * 64, flush=True)

    succeeded = failed = total_segments = 0
    started = time.time()

    with STATE_FILE.open("a") as state, FAILURE_LOG.open("a") as flog:
        for i, path in enumerate(todo, 1):
            try:
                good, error, seg_count = index_file(path)
            except Exception as e:
                good, error, seg_count = False, f"unhandled: {e}", 0

            if good:
                succeeded += 1
                total_segments += seg_count
                state.write(f"{path}\n")
                state.flush()
            else:
                failed += 1
                flog.write(f"{path}\t{error}\n")
                flog.flush()
                print(f"  FAIL {path.name}: {error}", flush=True)

            if i % 25 == 0 or i == len(todo):
                rate = i / max(1e-9, time.time() - started)
                remaining = (len(todo) - i) / rate if rate else 0
                print(
                    f"[{i}/{len(todo)}] ok={succeeded} fail={failed} "
                    f"segments={total_segments} {rate:.1f} files/s "
                    f"eta={remaining/60:.1f}m",
                    flush=True,
                )

    print("-" * 64)
    print(f"indexed  : {succeeded}")
    print(f"failed   : {failed}  (see {FAILURE_LOG})")
    print(f"segments : {total_segments}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
