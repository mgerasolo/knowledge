"""Load and normalize personality corpus manifests."""
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CorpusError(ValueError):
    """The personality manifest is missing or malformed."""


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    published: str | None
    duration_seconds: float | None


@dataclass(frozen=True)
class PersonalityCorpus:
    personality_id: str
    display_name: str
    description: str
    videos: tuple[Video, ...]

    @property
    def video_ids(self) -> list[str]:
        return [video.video_id for video in self.videos]

    @property
    def by_id(self) -> dict[str, Video]:
        return {video.video_id: video for video in self.videos}


def _video(raw: Any) -> Video:
    if not isinstance(raw, dict):
        raise CorpusError("video entry must be an object")
    video_id = raw.get("video_id")
    title = raw.get("title")
    if not isinstance(video_id, str) or not video_id.strip():
        raise CorpusError("video entry has no video_id")
    if not isinstance(title, str) or not title.strip():
        raise CorpusError(f"video {video_id} has no title")
    duration = raw.get("duration_seconds")
    if duration is not None:
        try:
            duration = float(duration)
        except (TypeError, ValueError) as exc:
            raise CorpusError(f"video {video_id} has invalid duration") from exc
        if not math.isfinite(duration) or duration < 0:
            raise CorpusError(f"video {video_id} has invalid duration")
        if duration == 0:
            duration = None
    return Video(video_id.strip(), title.strip(), raw.get("published"), duration)


def load_corpus(path: str | Path) -> PersonalityCorpus:
    """Flatten source videos and guest appearances, rejecting duplicate IDs."""
    try:
        with Path(path).open(encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusError(f"could not load corpus: {Path(path).name}") from exc
    if not isinstance(raw, dict):
        raise CorpusError("corpus root must be an object")

    entries: list[Any] = []
    sources = raw.get("sources", [])
    if not isinstance(sources, list):
        raise CorpusError("sources must be a list")
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("videos"), list):
            raise CorpusError("each source must contain a videos list")
        entries.extend(source["videos"])
    guests = raw.get("guest_appearances", [])
    if not isinstance(guests, list):
        raise CorpusError("guest_appearances must be a list")
    entries.extend(guests)

    videos = tuple(_video(entry) for entry in entries)
    if not videos:
        raise CorpusError("corpus contains no videos")
    ids = [video.video_id for video in videos]
    if len(ids) != len(set(ids)):
        raise CorpusError("corpus contains duplicate video_ids")
    personality_id = raw.get("personality_id")
    display_name = raw.get("display_name")
    if not isinstance(personality_id, str) or not personality_id:
        raise CorpusError("corpus has no personality_id")
    if not isinstance(display_name, str) or not display_name:
        raise CorpusError("corpus has no display_name")
    return PersonalityCorpus(
        personality_id=personality_id,
        display_name=display_name,
        description=str(raw.get("description", "")),
        videos=videos,
    )
