"""Backfill video metadata from YouTube via MCP Gateway.

Fetches full video info (description, chapters, hashtags, uploader)
for all videos that don't have metadata_fetched_at set.
"""
import json
import re
import requests
import time
import os
from mcp_transcript import _init_mcp_session, _parse_sse_response, MCP_GATEWAY_URL, MCP_HEADERS

SURREAL_URL = os.getenv('SURREAL_URL', 'http://10.0.0.33:5040')
SURREAL_USER = os.getenv('SURREAL_USER', 'root')
SURREAL_PASS = os.getenv('SURREAL_PASS', 'changeme')
SURREAL_NS = os.getenv('SURREAL_NS', 'knowledge')
SURREAL_DB = os.getenv('SURREAL_DB', 'transcripts')


def surreal_query(query):
    try:
        resp = requests.post(f'{SURREAL_URL}/sql', auth=(SURREAL_USER, SURREAL_PASS),
            headers={'Accept': 'application/json', 'surreal-ns': SURREAL_NS, 'surreal-db': SURREAL_DB},
            data=query, timeout=30)
        return resp.json() if resp.ok else []
    except Exception as e:
        print(f'SurrealDB error: {e}')
        return []


def escape_surreal(text):
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def fetch_video_info(video_id):
    """Fetch video info via MCP Gateway."""
    session_id = _init_mcp_session()
    if not session_id:
        return None

    try:
        headers = {**MCP_HEADERS, "Mcp-Session-Id": session_id}
        resp = requests.post(MCP_GATEWAY_URL, headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "get_video_info", "arguments": {"url": f"https://youtube.com/watch?v={video_id}"}}
        }, timeout=30)

        if not resp.ok:
            return None

        data = _parse_sse_response(resp.text)
        if "error" in data:
            return None

        result = data.get("result", {})
        content = result.get("content", [])
        if not content:
            return None

        text = content[0].get("text", "{}")
        return json.loads(text)
    except Exception as e:
        print(f'  MCP error: {e}')
        return None


def parse_chapters(description):
    """Extract chapters/timestamps from description text."""
    if not description:
        return []

    chapters = []
    # Match patterns like "0:00 — Title" or "12:34 - Title" or "1:23:45 Title"
    pattern = r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[—\-–:]\s*(.+?)(?:\n|$)'
    matches = re.findall(pattern, description)

    for timestamp, title in matches:
        parts = timestamp.split(':')
        if len(parts) == 3:
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            seconds = int(parts[0]) * 60 + int(parts[1])
        chapters.append({'time': seconds, 'title': title.strip()})

    return chapters


def parse_hashtags(description):
    """Extract hashtags from description."""
    if not description:
        return []
    return re.findall(r'#(\w+)', description)


def backfill_video(video_id, surreal_id):
    """Fetch and store metadata for a single video."""
    info = fetch_video_info(video_id)
    if not info:
        return False

    description = info.get('description', '')
    chapters = parse_chapters(description)
    hashtags = parse_hashtags(description)
    uploader = info.get('uploader', '')
    upload_date = info.get('upload_date', '')
    duration = info.get('duration', '')

    chapters_json = json.dumps(chapters)
    hashtags_json = json.dumps(hashtags)

    surreal_query(f"""
        UPDATE {surreal_id} SET
            description = '{escape_surreal(description)}',
            chapters = {chapters_json},
            hashtags = {hashtags_json},
            uploader = '{escape_surreal(uploader)}',
            metadata_fetched_at = time::now();
    """)

    return True


def backfill_all(limit=None):
    """Backfill metadata for all videos without it."""
    results = surreal_query(
        "SELECT id, youtube_id, title FROM video WHERE metadata_fetched_at = NONE;"
    )
    if not results or not results[0].get('result'):
        print('No videos need backfill')
        return

    videos = results[0]['result']
    if limit:
        videos = videos[:limit]

    print(f'Backfilling {len(videos)} videos...\n')
    success = 0
    failed = 0

    for i, v in enumerate(videos):
        yt_id = v.get('youtube_id', '')
        title = v.get('title', '?')[:60]
        vid = str(v['id'])

        ok = backfill_video(yt_id, vid)
        if ok:
            success += 1
            print(f'  [{i+1}/{len(videos)}] ✓ {title}')
        else:
            failed += 1
            print(f'  [{i+1}/{len(videos)}] ✗ {title}')

        time.sleep(3)  # Rate limit MCP calls — conservative to avoid YouTube rate limiting

    print(f'\nDone: {success} success, {failed} failed')


if __name__ == '__main__':
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    backfill_all(limit=limit)
