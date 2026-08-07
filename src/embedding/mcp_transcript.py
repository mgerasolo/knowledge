"""MCP Gateway client for fetching YouTube transcripts."""
import json
import requests
from typing import Optional

MCP_GATEWAY_URL = "http://10.0.0.27:2780/mcp"
MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}


def _parse_sse_response(response_text: str) -> dict:
    """Parse SSE response to extract JSON data."""
    for line in response_text.strip().split('\n'):
        if line.startswith('data: '):
            return json.loads(line[6:])
    return {}


def _init_mcp_session() -> Optional[str]:
    """Initialize MCP Gateway session and return session ID."""
    try:
        response = requests.post(
            MCP_GATEWAY_URL,
            headers=MCP_HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "knowledge-embedding", "version": "1.0"}
                }
            },
            timeout=30
        )
        if response.ok:
            session_id = response.headers.get("Mcp-Session-Id")
            return session_id
    except Exception as e:
        print(f"MCP init error: {e}")
    return None


def fetch_transcript(video_id: str, timed: bool = True) -> Optional[dict]:
    """Fetch YouTube transcript via MCP Gateway.

    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        timed: If True, fetch with timestamps; if False, plain text

    Returns:
        Dict with 'transcript' (text), 'segments' (list), 'title' on success
        None on failure
    """
    # Initialize session
    session_id = _init_mcp_session()
    if not session_id:
        print("Failed to initialize MCP session")
        return None

    # Choose tool based on timed flag
    tool_name = "get_timed_transcript" if timed else "get_transcript"
    url = f"https://youtube.com/watch?v={video_id}"

    try:
        headers = {**MCP_HEADERS, "Mcp-Session-Id": session_id}
        response = requests.post(
            MCP_GATEWAY_URL,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {"url": url, "lang": "en"}
                }
            },
            timeout=60
        )

        if not response.ok:
            print(f"MCP tool call failed: {response.status_code}")
            return None

        # Parse SSE response
        data = _parse_sse_response(response.text)

        if "error" in data:
            print(f"MCP error: {data['error']}")
            return None

        # Extract content from result
        result = data.get("result", {})
        content = result.get("content", [])

        if not content:
            print("No content in MCP response")
            return None

        # Parse the JSON text content
        text_content = content[0].get("text", "{}")
        transcript_data = json.loads(text_content)

        # Handle timed transcript format
        if timed and "snippets" in transcript_data:
            segments = []
            full_text_parts = []

            for snippet in transcript_data["snippets"]:
                segments.append({
                    "start": snippet.get("start", 0),
                    "duration": snippet.get("duration", 0),
                    "text": snippet.get("text", "")
                })
                full_text_parts.append(snippet.get("text", ""))

            return {
                "title": transcript_data.get("title", ""),
                "transcript": " ".join(full_text_parts),
                "segments": segments
            }

        # Handle plain transcript format
        elif "transcript" in transcript_data:
            return {
                "title": transcript_data.get("title", ""),
                "transcript": transcript_data.get("transcript", ""),
                "segments": []
            }

        print(f"Unexpected transcript format: {list(transcript_data.keys())}")
        return None

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"Transcript fetch error: {e}")
        return None


def test_transcript():
    """Test function - fetch a known video transcript."""
    result = fetch_transcript("dQw4w9WgXcQ")
    if result:
        print(f"Title: {result['title']}")
        print(f"Transcript length: {len(result['transcript'])} chars")
        print(f"Segments: {len(result['segments'])}")
        print(f"First 200 chars: {result['transcript'][:200]}...")
        return True
    else:
        print("Failed to fetch transcript")
        return False


if __name__ == "__main__":
    test_transcript()
