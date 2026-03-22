#!/usr/bin/env python3
"""
Load existing transcripts into SurrealDB for the spike.
Enhanced v2: Preserves timestamps, smaller chunks, denormalized fields.
Supports both old format (plain text) and new format (timestamped JSON).
"""

import os
import re
import yaml
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

# Configuration
SURREAL_URL = "http://10.0.0.33:5040"
SURREAL_USER = "root"
SURREAL_PASS = "knowledgespike123"
SURREAL_NS = "knowledgespike"
SURREAL_DB = "transcripts"

LITELLM_URL = "http://10.0.0.27:2764/v1/embeddings"
LITELLM_API_KEY = "sk-nlf-litellm-65cf74289dcc9be237bf6143"
EMBEDDING_MODEL = "embeddings"

TRANSCRIPT_DIR = Path("/mnt/foundry_resources/transcripts")
CHUNK_SIZE = 500  # Smaller chunks for finer granularity
CHUNK_OVERLAP = 100

# Visual trigger phrases (lazy analysis pattern)
VISUAL_TRIGGERS = [
    "as you can see",
    "on screen",
    "on the screen",
    "look at this",
    "if you look at",
    "on my screen",
    "showing you",
    "let me show you",
    "you'll see here",
    "take a look",
]


def get_embedding(text: str) -> Optional[list]:
    """Get embedding from LiteLLM proxy."""
    try:
        response = requests.post(
            LITELLM_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LITELLM_API_KEY}"
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text[:8000]  # Limit input size
            },
            timeout=30
        )
        if response.ok:
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        print(f"  Embedding error: {e}")
    return None


def surreal_query(query: str, variables: dict = None):
    """Execute SurrealDB query."""
    try:
        response = requests.post(
            f"{SURREAL_URL}/sql",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
            },
            auth=(SURREAL_USER, SURREAL_PASS),
            data=query,
            timeout=30
        )
        if response.ok:
            return response.json()
        else:
            print(f"  SurrealDB error: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"  SurrealDB connection error: {e}")
    return None


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return frontmatter or {}, body
            except yaml.YAMLError:
                pass
    return {}, content


def extract_raw_segments(body: str) -> Optional[list[dict]]:
    """Extract raw segments JSON from new format transcripts."""
    # Look for <!-- RAW_SEGMENTS ... -->
    match = re.search(r'<!-- RAW_SEGMENTS\s*\n(.*?)\n-->', body, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def detect_visual_triggers(text: str) -> bool:
    """Check if text contains visual trigger phrases."""
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in VISUAL_TRIGGERS)


def extract_guests_from_title(title: str) -> list[str]:
    """Extract guest names from video title patterns."""
    guests = []

    # Common patterns: "X with Y", "X ft. Y", "X featuring Y", "X | Y"
    patterns = [
        r'(?:with|ft\.?|featuring|feat\.?|&|and)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'\|\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'(?:interview|conversation|chat|talk).*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, title, re.IGNORECASE)
        guests.extend(matches)

    return list(set(guests))


def extract_guests_from_description(description: str) -> list[str]:
    """Extract guest names from video description."""
    if not description:
        return []

    guests = []

    # Look for "Guest: X" or "Featuring: X" or "@handle" patterns
    guest_patterns = [
        r'(?:guest|featuring|with|special guest)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'@(\w+)',  # Social handles
    ]

    for pattern in guest_patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        guests.extend(matches)

    return list(set(guests))[:5]  # Limit to 5


def chunk_with_timestamps(segments: list[dict], chunk_size: int = CHUNK_SIZE) -> list[dict]:
    """
    Group consecutive segments into chunks while preserving timestamps.
    Each chunk gets the start_time of its first segment and end_time of its last.
    """
    if not segments:
        return []

    chunks = []
    current_chunk = {
        "texts": [],
        "start_time": segments[0]["start"],
        "end_time": segments[0]["start"] + segments[0].get("duration", 0),
    }
    current_length = 0

    for seg in segments:
        seg_text = seg["text"].strip()
        seg_len = len(seg_text)

        # If adding this segment exceeds chunk size, finalize current chunk
        if current_length + seg_len > chunk_size and current_chunk["texts"]:
            chunks.append({
                "text": " ".join(current_chunk["texts"]),
                "start_time": current_chunk["start_time"],
                "end_time": current_chunk["end_time"],
                "chunk_index": len(chunks),
            })
            # Start new chunk with overlap (include last segment)
            current_chunk = {
                "texts": [seg_text],
                "start_time": seg["start"],
                "end_time": seg["start"] + seg.get("duration", 0),
            }
            current_length = seg_len
        else:
            current_chunk["texts"].append(seg_text)
            current_chunk["end_time"] = seg["start"] + seg.get("duration", 0)
            current_length += seg_len + 1  # +1 for space

    # Don't forget the last chunk
    if current_chunk["texts"]:
        chunks.append({
            "text": " ".join(current_chunk["texts"]),
            "start_time": current_chunk["start_time"],
            "end_time": current_chunk["end_time"],
            "chunk_index": len(chunks),
        })

    return chunks


def chunk_text_legacy(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split text into overlapping chunks (legacy format without timestamps)."""
    chunks = []
    start = 0
    chunk_idx = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk_text.rfind(". ")
            if last_period > chunk_size // 2:
                end = start + last_period + 2
                chunk_text = text[start:end]

        chunks.append({
            "text": chunk_text.strip(),
            "char_start": start,
            "char_end": end,
            "chunk_index": chunk_idx,
            "start_time": None,  # Unknown
            "end_time": None,
        })

        start = end - overlap
        chunk_idx += 1

    return chunks


def create_safe_id(text: str) -> str:
    """Create a safe ID from text."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


def ensure_speaker(name: str, is_host: bool = False) -> str:
    """Create or get speaker, return ID."""
    normalized = name.lower().strip().replace(" ", "-")
    speaker_id = create_safe_id(normalized)

    escaped_name = name.replace("\\", "\\\\").replace("'", "\\'")

    query = f"""
    UPSERT speaker:{speaker_id} SET
        name = '{escaped_name}',
        normalized = '{normalized}',
        is_host = {str(is_host).lower()},
        created_at = time::now();
    """
    surreal_query(query)
    return f"speaker:{speaker_id}"


def process_transcript(filepath: Path):
    """Process a single transcript file."""
    print(f"\nProcessing: {filepath}")

    content = filepath.read_text()
    metadata, body = parse_frontmatter(content)

    if not metadata.get("video_id") and not metadata.get("url"):
        print("  Skipping: No video ID or URL")
        return

    # Extract video ID
    video_id = metadata.get("video_id")
    if not video_id and metadata.get("url"):
        match = re.search(r"v=([^&]+)", metadata["url"])
        if match:
            video_id = match.group(1)

    if not video_id:
        print("  Skipping: Could not extract video ID")
        return

    channel_name = metadata.get("channel", filepath.parent.parent.name)
    channel_handle = channel_name.lower().replace(" ", "-")
    domain = metadata.get("domain", "unknown")

    # Parse published date
    published_raw = metadata.get("published", "")
    if published_raw and published_raw not in ("unknown", "NA"):
        # Handle both YYYY-MM-DD and YYYYMMDD formats
        if "-" in published_raw:
            published_date = published_raw
        elif len(published_raw) == 8:
            published_date = f"{published_raw[:4]}-{published_raw[4:6]}-{published_raw[6:8]}"
        else:
            published_date = "2026-01-01"
    else:
        published_date = "2026-01-01"

    # Create/update channel
    escaped_channel_name = channel_name.replace("\\", "\\\\").replace("'", "\\'")
    channel_query = f"""
    UPSERT channel:{create_safe_id(channel_handle)} SET
        youtube_handle = '{channel_handle}',
        name = '{escaped_channel_name}',
        domain = '{domain}',
        lookback_months = 36,
        ingested_at = time::now();
    """
    surreal_query(channel_query)

    # Extract description if available
    description = metadata.get("description", "")
    escaped_description = ""
    if description:
        escaped_description = description[:2000].replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

    # Create/update video with denormalized fields
    escaped_title = metadata.get("title", "Unknown").replace("\\", "\\\\").replace("'", "\\'")
    duration = metadata.get("duration_seconds", 0)

    video_query = f"""
    UPSERT video:{create_safe_id(video_id)} SET
        youtube_id = '{video_id}',
        title = '{escaped_title}',
        description = '{escaped_description}',
        published_at = d'{published_date}',
        duration_seconds = {duration},
        url = '{metadata.get("url", "")}',
        fetched_at = time::now(),
        transcript_path = '{str(filepath)}',
        channel_handle = '{channel_handle}',
        domain = '{domain}';
    """
    surreal_query(video_query)

    # Create channel->video relationship
    rel_query = f"""
    RELATE channel:{create_safe_id(channel_handle)}->has_video->video:{create_safe_id(video_id)};
    """
    surreal_query(rel_query)

    # Extract guests from title and description
    guests = []
    title = metadata.get("title", "")
    guests.extend(extract_guests_from_title(title))
    if description:
        guests.extend(extract_guests_from_description(description))

    # Create speaker records for guests and link to video
    for guest in set(guests):
        if len(guest) > 2:  # Skip very short names
            speaker_id = ensure_speaker(guest, is_host=False)
            surreal_query(f"""
            RELATE {speaker_id}->appears_in->video:{create_safe_id(video_id)}
                SET role = 'guest';
            """)
            print(f"  Found guest: {guest}")

    # Try to extract timestamped segments (new format)
    raw_segments = extract_raw_segments(body)

    if raw_segments:
        print(f"  Using timestamped format ({len(raw_segments)} raw segments)")
        chunks = chunk_with_timestamps(raw_segments)
    else:
        # Fall back to legacy text chunking
        print("  Using legacy text format (no timestamps)")
        transcript_text = body
        if "## Transcript" in body:
            transcript_text = body.split("## Transcript", 1)[1].strip()
        # Remove the RAW_SEGMENTS comment if present but couldn't parse
        transcript_text = re.sub(r'<!-- RAW_SEGMENTS.*?-->', '', transcript_text, flags=re.DOTALL).strip()
        chunks = chunk_text_legacy(transcript_text)

    print(f"  Created {len(chunks)} chunks")

    # Update video with segment count
    surreal_query(f"""
    UPDATE video:{create_safe_id(video_id)} SET segment_count = {len(chunks)};
    """)

    # Process each chunk
    for i, chunk in enumerate(chunks):
        chunk_id = f"{video_id}_{i}"

        # Get embedding
        embedding = get_embedding(chunk["text"])
        embedding_str = json.dumps(embedding) if embedding else "NONE"

        # Detect visual triggers
        requires_visual = detect_visual_triggers(chunk["text"])

        # Create segment with timestamps and denormalized fields
        escaped_text = chunk["text"].replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

        start_time = chunk.get("start_time") or 0.0
        end_time = chunk.get("end_time") or 0.0
        duration = end_time - start_time if end_time > start_time else 0.0

        segment_query = f"""
        UPSERT segment:{create_safe_id(chunk_id)} SET
            text = '{escaped_text}',
            chunk_index = {chunk["chunk_index"]},
            start_time = {start_time},
            end_time = {end_time},
            duration = {duration},
            char_start = {chunk.get("char_start", 0)},
            char_end = {chunk.get("char_end", 0)},
            embedding = {embedding_str},
            requires_visual = {str(requires_visual).lower()},
            published_at = d'{published_date}',
            domain = '{domain}',
            video_youtube_id = '{video_id}',
            ingested_at = time::now();
        """
        surreal_query(segment_query)

        # Create video->segment relationship
        seg_rel_query = f"""
        RELATE video:{create_safe_id(video_id)}->has_segment->segment:{create_safe_id(chunk_id)}
            SET sequence = {i};
        """
        surreal_query(seg_rel_query)

        # If visual trigger detected, create visual_reference record
        if requires_visual:
            trigger = next((t for t in VISUAL_TRIGGERS if t in chunk["text"].lower()), "unknown")
            visual_query = f"""
            CREATE visual_reference SET
                segment = segment:{create_safe_id(chunk_id)},
                trigger_phrase = '{trigger}',
                frame_timestamp = {start_time},
                processed = false;
            """
            surreal_query(visual_query)

        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(chunks)} chunks")

    print(f"  Done: {len(chunks)} segments created")


def main():
    print("=" * 60)
    print("SurrealDB Transcript Loader v2")
    print("=" * 60)
    print(f"Transcript dir: {TRANSCRIPT_DIR}")
    print(f"SurrealDB: {SURREAL_URL}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Chunk size: {CHUNK_SIZE} chars")
    print()

    # Test SurrealDB connection
    result = surreal_query("INFO FOR DB;")
    if not result:
        print("ERROR: Cannot connect to SurrealDB")
        return

    print("Connected to SurrealDB")

    # Find all transcript files
    transcripts = list(TRANSCRIPT_DIR.glob("**/*.md"))
    print(f"Found {len(transcripts)} transcript files")

    for filepath in transcripts:
        try:
            process_transcript(filepath)
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Ingestion complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
