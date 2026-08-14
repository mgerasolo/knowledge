"""Embedding and chunking logic for transcripts."""
import json
import requests
from typing import Optional
from config import Config
from surreal_client import surreal_query, surreal_write, create_safe_id, escape_string


# Visual trigger phrases (lazy analysis pattern)
VISUAL_TRIGGERS = [
    "as you can see", "on screen", "on the screen", "look at this",
    "if you look at", "on my screen", "showing you", "let me show you",
    "you'll see here", "take a look",
]


EMBED_BATCH_SIZE = 64


def _prefixed(text: str, kind: str) -> str:
    """Apply the model's task prefix. Truncate the text first so the prefix
    always survives the 8000-char cap."""
    prefix = (Config.EMBEDDING_QUERY_PREFIX if kind == "query"
              else Config.EMBEDDING_DOC_PREFIX)
    return prefix + text[:8000]


def get_embedding(text: str, kind: str = "document") -> Optional[list]:
    """Get one embedding from the LiteLLM proxy."""
    if not Config.LITELLM_API_KEY:
        return None

    try:
        response = requests.post(
            Config.LITELLM_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Config.LITELLM_API_KEY}"
            },
            json={
                "model": Config.EMBEDDING_MODEL,
                "input": _prefixed(text, kind)
            },
            timeout=30
        )
        if response.ok:
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        print(f"Embedding error: {e}")
    return None


def get_embeddings(texts: list[str], kind: str = "document") -> list[Optional[list]]:
    """Batch embeddings, order-preserving. A failed batch yields None per
    text rather than raising — callers count the Nones and report them."""
    if not Config.LITELLM_API_KEY:
        return [None] * len(texts)

    out: list[Optional[list]] = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = [_prefixed(t, kind) for t in texts[i:i + EMBED_BATCH_SIZE]]
        try:
            response = requests.post(
                Config.LITELLM_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {Config.LITELLM_API_KEY}"
                },
                json={"model": Config.EMBEDDING_MODEL, "input": batch},
                timeout=120
            )
            if response.ok:
                data = sorted(response.json()["data"], key=lambda d: d["index"])
                # Indices must be exactly 0..n-1 — anything else risks pairing
                # a vector with the wrong text, which is silent corruption.
                if [d["index"] for d in data] == list(range(len(batch))):
                    out.extend(d["embedding"] for d in data)
                    continue
                print("Embedding batch error: malformed indices")
            else:
                print("Embedding batch error: HTTP not ok")
        except Exception as e:
            print(f"Embedding batch error: {e}")
        out.extend([None] * len(batch))
    return out


def detect_visual_triggers(text: str) -> bool:
    """Check if text contains visual trigger phrases."""
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in VISUAL_TRIGGERS)


def chunk_with_timestamps(segments: list[dict], chunk_size: int = None) -> list[dict]:
    """Group consecutive segments into chunks while preserving timestamps."""
    chunk_size = chunk_size or Config.CHUNK_SIZE

    if not segments:
        return []

    chunks = []
    current_chunk = {
        "texts": [],
        "start_time": segments[0].get("start", 0),
        "end_time": segments[0].get("start", 0) + segments[0].get("duration", 0),
    }
    current_length = 0

    for seg in segments:
        seg_text = seg.get("text", "").strip()
        seg_len = len(seg_text)

        if current_length + seg_len > chunk_size and current_chunk["texts"]:
            chunks.append({
                "text": " ".join(current_chunk["texts"]),
                "start_time": current_chunk["start_time"],
                "end_time": current_chunk["end_time"],
                "chunk_index": len(chunks),
            })
            current_chunk = {
                "texts": [seg_text],
                "start_time": seg.get("start", 0),
                "end_time": seg.get("start", 0) + seg.get("duration", 0),
            }
            current_length = seg_len
        else:
            current_chunk["texts"].append(seg_text)
            current_chunk["end_time"] = seg.get("start", 0) + seg.get("duration", 0)
            current_length += seg_len + 1

    if current_chunk["texts"]:
        chunks.append({
            "text": " ".join(current_chunk["texts"]),
            "start_time": current_chunk["start_time"],
            "end_time": current_chunk["end_time"],
            "chunk_index": len(chunks),
        })

    return chunks


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[dict]:
    """Split text into overlapping chunks."""
    chunk_size = chunk_size or Config.CHUNK_SIZE
    overlap = overlap or Config.CHUNK_OVERLAP

    chunks = []
    start = 0
    chunk_idx = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

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
            "start_time": None,
            "end_time": None,
        })

        start = end - overlap
        chunk_idx += 1

    return chunks


def embed_video(video_data: dict, skip_embeddings: bool = False) -> dict:
    """Embed a video's transcript into SurrealDB.

    Args:
        video_data: Dict with video_id, title, url, channel info, and transcript
        skip_embeddings: Skip embedding generation for faster import

    Returns:
        Dict with result status and segment count
    """
    video_id = video_data.get("video_id") or video_data.get("youtube_id")
    if not video_id:
        return {"error": "Missing video_id", "success": False}

    title = video_data.get("title", "Unknown")
    url = video_data.get("url", "")
    channel_handle = video_data.get("channel_handle", "unknown")
    channel_name = video_data.get("channel_name", channel_handle)
    domain = video_data.get("domain", "general")
    # The epoch, not a plausible recent date. This defaulted to 2026-01-01 until
    # 2026-08-14, so a caller that forgot to send a date got a video that looked
    # genuinely published this January — 1,425 of them, silently wrong in every
    # date-sorted query. A caller that forgets now produces something obviously
    # unset instead. Callers should send the real date (see #17).
    published_at = video_data.get("published_at") or "1970-01-01"
    duration_seconds = video_data.get("duration_seconds", 0)
    transcript = video_data.get("transcript", "")
    segments = video_data.get("segments", [])

    # Full YouTube metadata
    description = video_data.get("description", "")
    chapters = video_data.get("chapters", [])
    hashtags = video_data.get("hashtags", [])
    youtube_tags = video_data.get("youtube_tags", [])
    category = video_data.get("category", "")
    view_count = video_data.get("view_count", 0)
    like_count = video_data.get("like_count", 0)
    comment_count = video_data.get("comment_count", 0)
    thumbnail_url = video_data.get("thumbnail_url", "")
    uploader = video_data.get("uploader", "")
    # "was_live", "is_live", "is_upcoming", "not_live" — what separates a
    # three-hour livestream recording from a three-hour uploaded episode.
    live_status = video_data.get("live_status", "")

    # Create/update channel
    channel_id = create_safe_id(channel_handle.lower())
    channel_query = f"""
    UPSERT channel:{channel_id} SET
        youtube_handle = '{escape_string(channel_handle)}',
        name = '{escape_string(channel_name)}',
        domain = '{escape_string(domain)}',
        ingested_at = time::now();
    """
    ok, err = surreal_write(channel_query)
    if not ok:
        return {"success": False, "video_id": video_id,
                "error": f"channel write failed: {err}", "stage": "channel"}

    # Create/update video
    video_db_id = create_safe_id(video_id)
    # Build metadata JSON for chapters, hashtags, tags
    import json as _json
    chapters_json = _json.dumps(chapters) if chapters else '[]'
    hashtags_json = _json.dumps(hashtags) if hashtags else '[]'
    tags_json = _json.dumps(youtube_tags) if youtube_tags else '[]'

    video_query = f"""
    UPSERT video:{video_db_id} SET
        youtube_id = '{video_id}',
        title = '{escape_string(title)}',
        published_at = d'{published_at}',
        duration_seconds = {duration_seconds or 0},
        url = '{escape_string(url)}',
        channel_handle = '{escape_string(channel_handle)}',
        channel_name = '{escape_string(channel_name)}',
        domain = '{escape_string(domain)}',
        description = '{escape_string(description)}',
        chapters = {chapters_json},
        hashtags = {hashtags_json},
        youtube_tags = {tags_json},
        category = '{escape_string(category)}',
        view_count = {view_count or 0},
        like_count = {like_count or 0},
        comment_count = {comment_count or 0},
        thumbnail_url = '{escape_string(thumbnail_url)}',
        uploader = '{escape_string(uploader)}',
        live_status = '{escape_string(live_status)}',
        metadata_fetched_at = time::now(),
        fetched_at = time::now(),
        ingested_at = time::now();
    """
    ok, err = surreal_write(video_query)
    if not ok:
        return {"success": False, "video_id": video_id,
                "error": f"video write failed: {err}", "stage": "video"}

    # Create channel->video relationship
    surreal_write(f"""
    RELATE channel:{channel_id}->has_video->video:{video_db_id};
    """)

    # Chunk transcript
    if segments:
        chunks = chunk_with_timestamps(segments)
    else:
        chunks = chunk_text(transcript)

    # Process each chunk
    segment_errors = []
    segments_written = 0
    embeddings_failed = 0
    for chunk in chunks:
        chunk_id = f"{video_id}_{chunk['chunk_index']}"
        chunk_db_id = create_safe_id(chunk_id)

        # Get embedding
        if skip_embeddings:
            embedding_str = "NONE"
        else:
            embedding = get_embedding(chunk["text"], kind="document")
            if embedding is None:
                # Segment is still written (text search must not lose data),
                # but the failure is COUNTED and reported — never hidden.
                embeddings_failed += 1
            embedding_str = json.dumps(embedding) if embedding else "NONE"

        # Detect visual triggers
        requires_visual = detect_visual_triggers(chunk["text"])

        start_time = chunk.get("start_time") or 0.0
        end_time = chunk.get("end_time") or 0.0
        duration = end_time - start_time if end_time > start_time else 0.0

        # Create segment
        segment_query = f"""
        UPSERT segment:{chunk_db_id} SET
            text = '{escape_string(chunk["text"])}',
            chunk_index = {chunk["chunk_index"]},
            start_time = {start_time},
            end_time = {end_time},
            duration = {duration},
            embedding = {embedding_str},
            requires_visual = {str(requires_visual).lower()},
            published_at = d'{published_at}',
            domain = '{escape_string(domain)}',
            video_youtube_id = '{video_id}',
            ingested_at = time::now();
        """
        ok, err = surreal_write(segment_query)
        if not ok:
            # Keep the first few messages only — a schema mismatch repeats per chunk.
            if len(segment_errors) < 3:
                segment_errors.append(f"chunk {chunk['chunk_index']}: {err}")
            continue
        segments_written += 1

        # Create video->segment relationship
        surreal_write(f"""
        RELATE video:{video_db_id}->has_segment->segment:{chunk_db_id}
            SET sequence = {chunk['chunk_index']};
        """)

    if segment_errors:
        return {"success": False, "video_id": video_id, "stage": "segments",
                "error": f"{len(chunks) - segments_written}/{len(chunks)} segment writes failed: "
                         + "; ".join(segment_errors),
                "segments_written": segments_written}

    # Update video with segment count
    surreal_write(f"""
    UPDATE video:{video_db_id} SET segment_count = {segments_written};
    """)

    return {
        "success": True,
        "video_id": video_id,
        "surreal_id": f"video:{video_db_id}",
        "segment_count": segments_written,
        # True only when embedding was attempted AND every chunk got a vector.
        # The old `not skip_embeddings` claimed success even when the gateway
        # was unreachable and every chunk silently got NONE.
        "embeddings_generated": (not skip_embeddings
                                 and embeddings_failed == 0
                                 and segments_written > 0),
        "embeddings_failed": embeddings_failed,
    }
