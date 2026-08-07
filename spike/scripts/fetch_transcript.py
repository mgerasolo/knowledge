#!/usr/bin/env python3
"""Fetch YouTube transcript via youtube-transcript-api.

Called from Node.js via execFile. Outputs JSON to stdout.
Usage: python3 fetch_transcript.py <video_id> [language]

Output format:
  [{"text": "...", "start": 18.64, "duration": 3.24}, ...]

start/duration are in seconds (float).
"""
import json
import sys

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: fetch_transcript.py <video_id> [language]"}))
        sys.exit(1)

    video_id = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "en"

    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=[language, "en"])
        segments = [
            {
                "text": entry.text.strip(),
                "start": entry.start,
                "duration": entry.duration,
            }
            for entry in transcript
            if entry.text.strip()
        ]
        json.dump(segments, sys.stdout)
    except TranscriptsDisabled:
        print(json.dumps({"error": "transcripts_disabled", "video_id": video_id}))
        sys.exit(2)
    except NoTranscriptFound:
        print(json.dumps({"error": "no_transcript_found", "video_id": video_id}))
        sys.exit(3)
    except VideoUnavailable:
        print(json.dumps({"error": "video_unavailable", "video_id": video_id}))
        sys.exit(4)
    except Exception as e:
        print(json.dumps({"error": str(e), "video_id": video_id}))
        sys.exit(1)


if __name__ == "__main__":
    main()
