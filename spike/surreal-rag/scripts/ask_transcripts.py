#!/usr/bin/env python3
"""
Quick RAG script for conversational queries on transcript content.
Supports keyword search and semantic (vector) search + LiteLLM for answers.

Usage:
    python ask_transcripts.py "Your question"              # Keyword search
    python ask_transcripts.py --semantic "Your question"   # Vector search
    python ask_transcripts.py --hybrid "Your question"     # Both combined
"""

import sys
import re
import json
import argparse
import requests
from typing import Optional

# Configuration
SURREAL_URL = "http://10.0.0.33:5040"
SURREAL_USER = "root"
SURREAL_PASS = "changeme"
SURREAL_NS = "knowledgespike"
SURREAL_DB = "transcripts"

# LLM for answers
LITELLM_CHAT_URL = "http://10.0.0.27:2764/v1/chat/completions"
LITELLM_API_KEY = "sk-nlf-litellm-65cf74289dcc9be237bf6143"
LLM_MODEL = "claude-sonnet"  # Via LiteLLM proxy

# Embeddings for semantic search
LITELLM_EMBED_URL = "http://10.0.0.27:2764/v1/embeddings"
EMBEDDING_MODEL = "embeddings"


def surreal_query(query: str) -> Optional[list]:
    """Execute SurrealDB query and return results."""
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
            data = response.json()
            # SurrealDB returns array of results, one per statement
            # Get the last successful result (for multi-statement queries like LET + SELECT)
            if data:
                for result in reversed(data):
                    if result.get("status") == "OK" and "result" in result:
                        return result["result"]
        else:
            print(f"SurrealDB error: {response.status_code}")
    except Exception as e:
        print(f"Connection error: {e}")
    return None


def get_embedding(text: str) -> Optional[list]:
    """Get embedding vector for text via LiteLLM proxy."""
    try:
        response = requests.post(
            LITELLM_EMBED_URL,
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
        else:
            print(f"Embedding error: {response.status_code}")
    except Exception as e:
        print(f"Embedding connection error: {e}")
    return None


def search_segments_semantic(query_text: str, speaker: str = None, limit: int = 20) -> list[dict]:
    """
    Search segments using vector similarity (semantic search).
    Requires embeddings to be populated in the database.
    """
    # Get embedding for the query
    query_embedding = get_embedding(query_text)
    if not query_embedding:
        print("⚠️  Could not generate query embedding, falling back to keyword search")
        return []

    embedding_json = json.dumps(query_embedding)

    if speaker:
        escaped_speaker = speaker.replace("'", "\\'").lower()
        hyphenated = escaped_speaker.replace(" ", "-")

        query = f"""
        LET $speaker_videos = (
            SELECT youtube_id FROM video
            WHERE channel_handle IS NOT NONE
            AND (channel_handle CONTAINS '{hyphenated}' OR channel_handle CONTAINS '{escaped_speaker}')
        );
        SELECT
            id,
            text,
            start_time,
            end_time,
            video_youtube_id,
            domain,
            published_at,
            vector::similarity::cosine(embedding, {embedding_json}) AS score
        FROM segment
        WHERE embedding IS NOT NONE
            AND video_youtube_id IN $speaker_videos.youtube_id
        ORDER BY score DESC
        LIMIT {limit};
        """
    else:
        query = f"""
        SELECT
            id,
            text,
            start_time,
            end_time,
            video_youtube_id,
            domain,
            published_at,
            vector::similarity::cosine(embedding, {embedding_json}) AS score
        FROM segment
        WHERE embedding IS NOT NONE
        ORDER BY score DESC
        LIMIT {limit};
        """

    return surreal_query(query) or []


def search_segments(keywords: list[str], speaker: str = None, limit: int = 20) -> list[dict]:
    """
    Search segments by keywords (OR matching).
    Optionally filter by speaker/channel via video join.
    """
    # Build WHERE clause with keyword conditions
    conditions = []
    for kw in keywords:
        # Case-insensitive contains
        escaped = kw.replace("'", "\\'").lower()
        conditions.append(f"string::lowercase(text) CONTAINS '{escaped}'")

    keyword_clause = " OR ".join(conditions)

    if speaker:
        # Use subquery to get video IDs for this speaker/channel
        escaped_speaker = speaker.replace("'", "\\'").lower()
        hyphenated = escaped_speaker.replace(" ", "-")

        query = f"""
        LET $speaker_videos = (
            SELECT youtube_id FROM video
            WHERE channel_handle IS NOT NONE
            AND (channel_handle CONTAINS '{hyphenated}' OR channel_handle CONTAINS '{escaped_speaker}')
        );
        SELECT
            id,
            text,
            start_time,
            end_time,
            video_youtube_id,
            domain,
            published_at
        FROM segment
        WHERE ({keyword_clause})
            AND video_youtube_id IN $speaker_videos.youtube_id
        ORDER BY published_at DESC
        LIMIT {limit};
        """
    else:
        query = f"""
        SELECT
            id,
            text,
            start_time,
            end_time,
            video_youtube_id,
            domain,
            published_at
        FROM segment
        WHERE ({keyword_clause})
        ORDER BY published_at DESC
        LIMIT {limit};
        """

    return surreal_query(query) or []


def get_video_context(video_id: str) -> Optional[dict]:
    """Get video metadata for context."""
    query = f"""
    SELECT title, url, channel_handle, published_at
    FROM video
    WHERE youtube_id = '{video_id}'
    LIMIT 1;
    """
    results = surreal_query(query)
    return results[0] if results else None


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    if seconds is None or seconds == 0:
        return "0:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def build_youtube_link(video_id: str, start_time: float) -> str:
    """Build YouTube link with timestamp."""
    t = int(start_time) if start_time else 0
    return f"https://youtube.com/watch?v={video_id}&t={t}"


def ask_llm(question: str, context: str) -> str:
    """Send question + context to LLM and get answer."""
    system_prompt = """You are a research assistant helping analyze YouTube transcript content.
Answer questions based ONLY on the transcript excerpts provided.
Always cite your sources with video titles and timestamps when possible.
If the context doesn't contain enough information to answer, say so clearly.
Be specific and quote relevant phrases when they support your answer."""

    user_prompt = f"""Based on the following transcript excerpts, please answer this question:

QUESTION: {question}

TRANSCRIPT EXCERPTS:
{context}

Please provide a clear answer with specific citations from the transcripts above."""

    try:
        response = requests.post(
            LITELLM_CHAT_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LITELLM_API_KEY}"
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.3
            },
            timeout=60
        )
        if response.ok:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            return f"LLM error: {response.status_code} - {response.text[:200]}"
    except Exception as e:
        return f"LLM connection error: {e}"


def extract_keywords(question: str) -> list[str]:
    """Extract meaningful keywords from question."""
    # Common words to skip
    stopwords = {
        "what", "which", "who", "where", "when", "why", "how", "does", "do",
        "is", "are", "was", "were", "the", "a", "an", "in", "on", "at", "to",
        "for", "of", "with", "about", "that", "this", "say", "says", "said",
        "think", "thinks", "best", "worst", "good", "bad", "make", "makes"
    }

    # Extract words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', question.lower())
    keywords = [w for w in words if w not in stopwords]

    # Also look for quoted phrases
    quoted = re.findall(r'"([^"]+)"', question)
    keywords.extend(quoted)

    return keywords if keywords else words[:5]


def detect_speaker_filter(question: str) -> Optional[str]:
    """Detect if question is about a specific speaker."""
    # Common patterns
    patterns = [
        r"(?:does|what does|what did)\s+(\w+(?:\s+\w+)?)\s+(?:say|think|recommend|suggest)",
        r"(?:according to)\s+(\w+(?:\s+\w+)?)",
        r"(\w+(?:\s+\w+)?)'s?\s+(?:opinion|view|take|thoughts)",
        r"(\w+\s+\w+)\s+(?:talks about|discusses|mentions)",
    ]

    # Common question words and false positives to skip
    skip_words = {
        "the", "what", "which", "who", "how", "why", "when", "where",
        "this", "that", "these", "those", "are", "is", "do", "does",
        "can", "could", "would", "should", "will", "best", "good"
    }

    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            name = match.group(1).lower()
            if name not in skip_words:
                return name

    # Check for capitalized names (but filter out question starters)
    names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', question)
    for name in names:
        if name.lower() not in skip_words:
            return name.lower()

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Query transcript content with RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ask_transcripts.py "Which Bible version does Myron Golden recommend?"
  python ask_transcripts.py --semantic "How should I structure my business?"
  python ask_transcripts.py --hybrid "Best practices for OpenClaw deployment"
        """
    )
    parser.add_argument("question", nargs="+", help="Your question")
    parser.add_argument("--semantic", "-s", action="store_true",
                        help="Use semantic (vector) search instead of keyword search")
    parser.add_argument("--hybrid", "-H", action="store_true",
                        help="Use both keyword and semantic search, combine results")
    parser.add_argument("--limit", "-l", type=int, default=25,
                        help="Max segments to retrieve (default: 25)")

    args = parser.parse_args()
    question = " ".join(args.question)

    search_mode = "hybrid" if args.hybrid else ("semantic" if args.semantic else "keyword")
    print(f"\n📝 Question: {question}")
    print(f"🔎 Search mode: {search_mode}\n")

    # Extract keywords and speaker filter
    keywords = extract_keywords(question)
    speaker = detect_speaker_filter(question)

    if speaker:
        print(f"👤 Filtering by speaker/channel: {speaker}")

    # Search based on mode
    segments = []

    if search_mode == "keyword":
        print(f"🔍 Keywords: {', '.join(keywords)}")
        segments = search_segments(keywords, speaker=speaker, limit=args.limit)

    elif search_mode == "semantic":
        print("🧠 Using semantic search...")
        segments = search_segments_semantic(question, speaker=speaker, limit=args.limit)
        if not segments:
            print("⚠️  No embeddings found, falling back to keyword search")
            segments = search_segments(keywords, speaker=speaker, limit=args.limit)

    elif search_mode == "hybrid":
        print(f"🔍 Keywords: {', '.join(keywords)}")
        print("🧠 Also using semantic search...")

        # Get both result sets
        keyword_results = search_segments(keywords, speaker=speaker, limit=args.limit // 2)
        semantic_results = search_segments_semantic(question, speaker=speaker, limit=args.limit // 2)

        # Combine and deduplicate by segment ID
        seen_ids = set()
        for seg in keyword_results + semantic_results:
            seg_id = seg.get("id", str(seg.get("text", "")[:50]))
            if seg_id not in seen_ids:
                seen_ids.add(seg_id)
                segments.append(seg)

        # Limit total
        segments = segments[:args.limit]

    if not segments:
        print("\n❌ No matching segments found. Try different keywords.")
        sys.exit(0)

    print(f"📚 Found {len(segments)} relevant segments\n")

    # Build context with video metadata
    context_parts = []
    seen_videos = {}

    for seg in segments:
        video_id = seg.get("video_youtube_id", "unknown")

        # Get video title if we haven't already
        if video_id not in seen_videos:
            video_meta = get_video_context(video_id)
            seen_videos[video_id] = video_meta.get("title", video_id) if video_meta else video_id

        video_title = seen_videos[video_id]
        timestamp = format_timestamp(seg.get("start_time", 0))
        link = build_youtube_link(video_id, seg.get("start_time", 0))

        context_parts.append(f"""
---
VIDEO: {video_title}
TIMESTAMP: {timestamp}
LINK: {link}
TEXT: {seg['text']}
---""")

    context = "\n".join(context_parts)

    # Ask LLM
    print("🤖 Asking AI...\n")
    answer = ask_llm(question, context)

    print("=" * 60)
    print("ANSWER:")
    print("=" * 60)
    print(answer)
    print("=" * 60)

    # Show source videos
    print(f"\n📹 Sources ({len(seen_videos)} videos):")
    for video_id, title in list(seen_videos.items())[:5]:
        print(f"  • {title}")
        print(f"    https://youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
