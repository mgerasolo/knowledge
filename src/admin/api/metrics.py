"""Daily ingestion counts and freshness, read from the real library.

WHY THIS MODULE EXISTS
----------------------
Every page in this admin site reported library contents from `pipeline_items`, a
Postgres work queue the real ingestion path stopped writing to. On 2026-08-09 the
queue said 1,150 videos and nothing finished in 55 hours; the library held 3,493
and had taken one in 12 minutes earlier. The queue is not broken — it is a queue,
and it was being read as an inventory.

So: the queue answers "what is in flight". This module answers "what do we hold,
and is it still arriving". They are different questions with different sources.

THE THREE SOURCES, AND THE DEFECT IN EACH
-----------------------------------------
1. SurrealDB `video.ingested_at` — authoritative, but only from 2026-08-07. The
   2026-08-05 rebuild stamped `time::now()` on 3,057 re-filed records, so that one
   day holds a fake spike ~60x the real daily rate.
2. Transcript file mtimes — real history back to March, untouched by the rebuild,
   but they only cover the file-writing path. The n8n path writes straight to
   SurrealDB and leaves no file.
3. Postgres `channels` — the curated domain per channel, but only 50 records exist
   for 72 channels present in the corpus.

Each defect is handled explicitly below rather than averaged away.

THE RULE THAT MATTERS MOST
--------------------------
A zero must never be indistinguishable from a failure to read. This project already
survived a two-week outage in which every health check said healthy while the corpus
was empty. Every function here reports *why* it has no data.
"""
import os
import threading
import time as _time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

import requests

from api.categories import (
    OTHER,
    TOP_LEVEL_ORDER,
    canonical_category,
    resolve_category,
    split_known_unknown,
)
from config import Config
from db import get_db_cursor

# --- Constants with reasons -------------------------------------------------

# Both Banner and Friday run Eastern. Bucketing days in UTC would push an evening's
# ingestion onto tomorrow's bar — at 01:00 EDT, "today" in UTC is already 5 hours
# old. Matt reads this page against his own calendar day, so we bucket in his.
DISPLAY_TZ = ZoneInfo(os.getenv('DASHBOARD_TZ', 'America/New_York'))

# The corpus was rebuilt from disk on this date and every record written that day
# carries it as `ingested_at`. Rendering it as a bar would show a fake
# record-breaking day and permanently wreck the chart's Y-axis scale.
REBUILD_DAY = date(2026, 8, 5)
REBUILD_NOTE = "corpus rebuilt from disk — records re-filed, not newly ingested"

# Before this date, `ingested_at` is the rebuild timestamp rather than the real
# ingestion time, so history comes from the transcript files instead.
CORPUS_TRUTH_FROM = date(2026, 8, 7)

TRANSCRIPT_DIR = Path(os.getenv('TRANSCRIPT_DIR', '/mnt/foundry_resources/transcripts'))

# Walking ~3,500 files on a NAS mount is too slow to do per request, and a browser
# auto-refresh would hammer the mount. Single-tenant admin page, so a plain TTL is
# enough; there is nothing to key the cache by.
CACHE_TTL_SECONDS = int(os.getenv('METRICS_CACHE_TTL', '60'))

# Freshness bands. Defaults align with STALE_INGEST_HOURS in status.py so this page
# and the machine-pollable status endpoint cannot disagree about what "stale" means.
FRESH_HOURS = int(os.getenv('FRESH_WITHIN_HOURS', '48'))
STALLED_HOURS = int(os.getenv('STALE_INGEST_HOURS', '72')) * 2  # 7d at the default

# A channel that posts monthly is not stalled at 8 days. Where a channel has enough
# history to know its own rhythm, judge it against that instead of a fixed number —
# otherwise low-frequency channels sit permanently red and train the reader to
# ignore the colour entirely.
#
# We frequently CANNOT know the rhythm: `published_at` is epoch-zero across the
# corpus, and `ingested_at` only became trustworthy on 2026-08-07, so most channels
# have too little real history. Those are reported as 'quiet' — the honest verdict,
# meaning "nothing new in N days, and we don't know whether that is normal for this
# channel". Only a channel whose own rhythm we know, and which has exceeded it, is
# called 'stalled'. Asserting a problem we cannot substantiate is how a dashboard
# stops being believed.
RHYTHM_MULTIPLIER = 3
MIN_VIDEOS_FOR_RHYTHM = 5


# --- Small TTL cache --------------------------------------------------------

class _Cached:
    """One value, refreshed on read after it expires. Errors are cached too, so a
    dead NAS mount does not mean a retry storm on every page load."""

    def __init__(self, loader):
        self._loader = loader
        self._value = None
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            if self._value is None or (_time.monotonic() - self._loaded_at) > CACHE_TTL_SECONDS:
                self._value = self._loader()
                self._loaded_at = _time.monotonic()
            return self._value

    def invalidate(self):
        with self._lock:
            self._value = None


# --- Source loading ---------------------------------------------------------

@dataclass
class SourceResult:
    """Rows plus an explicit reason when there are none.

    `problem` is the whole point: an empty list with problem=None means "we read
    the source and it genuinely holds nothing". An empty list with a problem means
    "we could not read it". The page renders those two states differently.
    """

    rows: list = field(default_factory=list)
    problem: str | None = None

    @property
    def ok(self) -> bool:
        return self.problem is None


def _surreal(query: str):
    """Run a SurrealQL query. Returns (rows, error)."""
    try:
        response = requests.post(
            f"{Config.SURREAL_URL}/sql",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "surreal-ns": Config.SURREAL_NS,
                "surreal-db": Config.SURREAL_DB,
            },
            auth=(Config.SURREAL_USER, Config.SURREAL_PASS),
            data=query.encode('utf-8'),
            timeout=30,
        )
    except Exception as exc:
        return None, f"unreachable: {exc}"

    if not response.ok:
        return None, f"HTTP {response.status_code}"
    try:
        payload = response.json()
    except ValueError:
        return None, "response was not JSON"
    if not isinstance(payload, list) or not payload:
        return None, "unexpected response shape"

    statement = payload[0]
    if not isinstance(statement, dict) or statement.get('status') != 'OK':
        return None, str(statement.get('result', 'unknown error'))

    rows = statement.get('result')
    return (rows if isinstance(rows, list) else []), None


def _parse_ts(value) -> datetime | None:
    """SurrealDB returns RFC3339 with nanosecond precision, which fromisoformat
    rejects on older Pythons. Truncate to microseconds rather than lose the row."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace('Z', '+00:00')
    if '.' in text:
        head, _, tail = text.partition('.')
        digits = ''.join(c for c in tail if c.isdigit())[:6]
        offset = tail[len(''.join(c for c in tail if c.isdigit())):]
        text = f"{head}.{digits.ljust(6, '0')}{offset}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _load_corpus() -> SourceResult:
    """Every video's ingestion time, channel and domain.

    Pulled as rows rather than pre-aggregated by SurrealDB because the day bucket
    depends on the display timezone, and grouping server-side would fix it to UTC.
    ~3,500 small rows; cheap enough behind the TTL cache.
    """
    rows, error = _surreal(
        "SELECT ingested_at, domain, channel_handle, channel_name "
        "FROM video ORDER BY ingested_at DESC;"
    )
    if error:
        return SourceResult(problem=f"search library unreadable ({error})")

    parsed = []
    for row in rows:
        timestamp = _parse_ts(row.get('ingested_at'))
        if timestamp is None:
            continue
        parsed.append({
            'at': timestamp,
            'domain': row.get('domain'),
            'handle': (row.get('channel_handle') or '').strip(),
            'name': row.get('channel_name') or row.get('channel_handle') or 'Unknown',
        })
    return SourceResult(rows=parsed)


def _load_files() -> SourceResult:
    """Transcript file timestamps — the only real history before 2026-08-07.

    The channel is taken from the first path segment under the transcript root,
    which is the channel handle lowercased.
    """
    try:
        if not TRANSCRIPT_DIR.is_dir():
            return SourceResult(problem=f"transcript archive not mounted at {TRANSCRIPT_DIR}")
        rows = []
        for path in TRANSCRIPT_DIR.rglob('*.md'):
            try:
                relative = path.relative_to(TRANSCRIPT_DIR)
                handle = relative.parts[0] if relative.parts else ''
                rows.append({
                    'at': datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
                    'handle': handle,
                })
            except (OSError, ValueError):
                continue
    except Exception as exc:
        return SourceResult(problem=f"transcript archive unreadable ({exc})")

    if not rows:
        return SourceResult(problem=f"no transcript files found under {TRANSCRIPT_DIR}")
    return SourceResult(rows=rows)


def _load_channels() -> SourceResult:
    """Curated channel records — handle (lowercased) -> name and domain.

    Only 50 exist for 72 channels in the corpus, so this is an enrichment layer,
    never a filter. A channel missing here still appears in every chart.
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT youtube_handle, name, domain, is_active FROM channels"
            )
            records = cursor.fetchall()
    except Exception as exc:
        # Not fatal. Without it, categories fall back to the video's own domain
        # and every count is still correct — only the curation is missing.
        return SourceResult(problem=f"channel list unreadable ({exc})")

    mapping = {}
    for record in records:
        handle = (record['youtube_handle'] or '').strip().lstrip('@').lower()
        if handle:
            mapping[handle] = {
                'name': record['name'],
                'domain': record['domain'],
                'is_active': record['is_active'],
            }
    return SourceResult(rows=[mapping])


_corpus_cache = _Cached(_load_corpus)
_files_cache = _Cached(_load_files)
_channels_cache = _Cached(_load_channels)


def invalidate_caches():
    """Used by tests and by an explicit refresh."""
    for cache in (_corpus_cache, _files_cache, _channels_cache):
        cache.invalidate()


def _channel_map() -> dict:
    result = _channels_cache.get()
    return result.rows[0] if result.rows else {}


def _local_day(moment: datetime) -> date:
    return moment.astimezone(DISPLAY_TZ).date()


def _today() -> date:
    return datetime.now(DISPLAY_TZ).date()


# --- Daily series -----------------------------------------------------------

@dataclass
class DailySeries:
    days: list
    series_names: list
    problems: list
    notes: list
    totals: dict


def _bucket_key(handle: str, video_domain, group: str, channel_map: dict):
    """Which series a video belongs to, and whether its category was a fallback."""
    record = channel_map.get(handle.lstrip('@').lower(), {})
    if group == 'channel':
        return record.get('name') or handle or 'Unknown', False

    resolution = resolve_category(record.get('domain'), video_domain)
    if group == 'subcategory':
        raw = (video_domain or record.get('domain') or 'general')
        return str(raw).strip().lower(), resolution.by_fallback
    return resolution.category, resolution.by_fallback


def daily_series(days: int = 90, group: str = 'category',
                 category: str | None = None) -> DailySeries:
    """Videos ingested per day, split into series.

    History splices two sources at CORPUS_TRUTH_FROM: the search library for days
    it can speak to, the transcript files for everything older. Splicing rather
    than summing — adding them would double-count every video that has both a file
    and a record, which is most of them.
    """
    days = max(1, min(int(days), 400))
    today = _today()
    start = today - timedelta(days=days - 1)

    corpus = _corpus_cache.get()
    files = _files_cache.get()
    channel_map = _channel_map()

    problems = [p for p in (corpus.problem, files.problem) if p]
    notes = []

    counts: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    fallback_videos = 0
    raw_domains = set()

    # Recent days: the search library, which covers BOTH ingestion paths.
    for row in corpus.rows:
        day = _local_day(row['at'])
        if day < max(start, CORPUS_TRUTH_FROM) or day > today:
            continue
        if day == REBUILD_DAY:
            continue
        raw_domains.add(row['domain'])
        name, by_fallback = _bucket_key(row['handle'], row['domain'], group, channel_map)
        if category and group in ('subcategory', 'channel'):
            resolved = resolve_category(
                channel_map.get(row['handle'].lstrip('@').lower(), {}).get('domain'),
                row['domain'],
            ).category
            if resolved != category:
                continue
        counts[day][name] += 1
        fallback_videos += 1 if by_fallback else 0

    # Older days: transcript files. These carry no domain of their own, so the
    # category comes from the channel record via the directory name.
    file_days_used = False
    for row in files.rows:
        day = _local_day(row['at'])
        if day < start or day >= CORPUS_TRUTH_FROM or day > today:
            continue
        if day == REBUILD_DAY:
            continue
        record = channel_map.get(row['handle'].lstrip('@').lower(), {})
        if group == 'channel':
            name = record.get('name') or row['handle']
        elif group == 'subcategory':
            name = str(record.get('domain') or 'general').strip().lower()
        else:
            name = canonical_category(record.get('domain'))
        if category and group in ('subcategory', 'channel'):
            if canonical_category(record.get('domain')) != category:
                continue
        counts[day][name] += 1
        file_days_used = True

    if file_days_used:
        notes.append(
            f"Days before {CORPUS_TRUTH_FROM.isoformat()} are reconstructed from "
            "transcript files on disk. They cover the file-writing path only, so a "
            "gap there is 'not recorded', not a confirmed zero."
        )

    # Every day in range gets a row, including empty ones. Ingestion runs in
    # bursts, so gaps are the honest shape of this data — but a missing DAY and a
    # zero day look identical on a chart, so we emit zeros explicitly.
    if group == 'category':
        series_names = list(TOP_LEVEL_ORDER)
    else:
        seen = set()
        for day_counts in counts.values():
            seen.update(day_counts)
        series_names = sorted(seen)

    day_rows = []
    cursor_day = start
    while cursor_day <= today:
        entry = {
            'date': cursor_day.isoformat(),
            'counts': {name: counts[cursor_day].get(name, 0) for name in series_names},
        }
        entry['total'] = sum(entry['counts'].values())
        if cursor_day == REBUILD_DAY:
            entry['rebuild'] = True
            entry['note'] = REBUILD_NOTE
        if cursor_day < CORPUS_TRUTH_FROM:
            entry['reconstructed'] = True
        day_rows.append(entry)
        cursor_day += timedelta(days=1)

    _, unknown_domains = split_known_unknown(raw_domains)
    if unknown_domains:
        notes.append(
            "Unrecognised category values found and counted as Other: "
            + ', '.join(sorted(unknown_domains))
        )

    totals = {name: sum(row['counts'].get(name, 0) for row in day_rows)
              for name in series_names}

    if group == 'category':
        unadopted = _unadopted_channel_count()
        if unadopted:
            notes.append(
                f"{unadopted} channels have videos but no channel record, so their "
                "category comes from the video itself rather than a curated setting."
            )

    return DailySeries(
        days=day_rows,
        series_names=series_names,
        problems=problems,
        notes=notes,
        totals=totals,
    )


def _unadopted_channel_count() -> int:
    corpus = _corpus_cache.get()
    channel_map = _channel_map()
    if not corpus.ok or not channel_map:
        return 0
    handles = {row['handle'].lstrip('@').lower() for row in corpus.rows if row['handle']}
    return len(handles - set(channel_map))


# --- Freshness --------------------------------------------------------------

def _state_for(newest: datetime | None, own_rhythm_hours: float | None = None,
               rhythm_known: bool = True) -> str:
    """Freshness verdict.

    Five states, and the distinctions between them are the point:

      fresh    — arrived recently, nothing to look at
      slowing  — past the fresh window but not yet worth acting on
      stalled  — we know this channel's rhythm and it has been exceeded 3x.
                 A confident "this is broken."
      quiet    — nothing new in a while, and we do NOT know this channel's normal
                 cadence, so we are not calling it broken. A monthly channel at
                 8 days lives here.
      never    — no videos at all. A setup problem, not an outage, and a
                 different fix.
    """
    if newest is None:
        return 'never'
    hours = (datetime.now(timezone.utc) - newest).total_seconds() / 3600
    if hours <= FRESH_HOURS:
        return 'fresh'

    if own_rhythm_hours:
        stalled_at = max(STALLED_HOURS, own_rhythm_hours * RHYTHM_MULTIPLIER)
        if hours <= stalled_at:
            return 'slowing'
        return 'stalled'

    if hours <= STALLED_HOURS:
        return 'slowing'
    # Past the fixed threshold with no rhythm to judge against. Say what we know
    # ("nothing in N days") without claiming what we don't ("this is broken").
    return 'stalled' if rhythm_known else 'quiet'


def _hours_since(moment: datetime | None) -> float | None:
    if moment is None:
        return None
    return round((datetime.now(timezone.utc) - moment).total_seconds() / 3600, 1)


def _median_gap_hours(times: list[datetime]) -> float | None:
    """A channel's own ingestion rhythm, from the gaps between its videos.

    The rebuild day is excluded: 3,057 records share one timestamp there, which
    would report a rhythm of zero and then call every channel stalled.

    Returns None when there is too little real history to say — which is common
    today and must stay honest rather than being guessed at. See RHYTHM_MULTIPLIER.
    """
    real = sorted(t for t in times if _local_day(t) != REBUILD_DAY)
    if len(real) < MIN_VIDEOS_FOR_RHYTHM:
        return None
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(real, real[1:])]
    gaps = [g for g in gaps if g > 0]
    if len(gaps) < MIN_VIDEOS_FOR_RHYTHM - 1:
        return None
    return median(gaps) if gaps else None


def freshness() -> dict:
    """Freshness overall, per category, and per channel.

    Per-slice on purpose. A global 'last ingest' number hides a dead category, and
    that exact blindness is what let a two-week outage report healthy.
    """
    corpus = _corpus_cache.get()
    channel_map = _channel_map()

    if not corpus.ok:
        # Explicitly NOT zeros. "We cannot read the library" and "the library is
        # empty" must never render the same way.
        return {
            'readable': False,
            'problem': corpus.problem,
            'overall': {'state': 'unknown', 'newest_at': None, 'hours_since': None},
            'categories': [],
            'channels': [],
        }

    newest_overall: datetime | None = None
    by_category: dict[str, datetime] = {}
    category_totals: dict[str, int] = defaultdict(int)
    by_channel: dict[str, dict] = {}

    for row in corpus.rows:
        moment = row['at']
        handle = row['handle'].lstrip('@').lower()
        record = channel_map.get(handle, {})
        category = resolve_category(record.get('domain'), row['domain']).category

        if newest_overall is None or moment > newest_overall:
            newest_overall = moment
        if category not in by_category or moment > by_category[category]:
            by_category[category] = moment
        category_totals[category] += 1

        channel = by_channel.setdefault(handle, {
            'handle': handle,
            'name': record.get('name') or row['name'],
            'category': category,
            'adopted': handle in channel_map,
            'videos': 0,
            'newest': None,
            'times': [],
        })
        channel['videos'] += 1
        channel['times'].append(moment)
        if channel['newest'] is None or moment > channel['newest']:
            channel['newest'] = moment

    categories = []
    for name in TOP_LEVEL_ORDER:
        newest = by_category.get(name)
        categories.append({
            'category': name,
            'state': _state_for(newest),
            'newest_at': newest.isoformat() if newest else None,
            'hours_since': _hours_since(newest),
            'videos': category_totals.get(name, 0),
        })

    channels = []
    for channel in by_channel.values():
        rhythm = _median_gap_hours(channel['times'])
        channels.append({
            'handle': channel['handle'],
            'name': channel['name'],
            'category': channel['category'],
            'adopted': channel['adopted'],
            'videos': channel['videos'],
            'newest_at': channel['newest'].isoformat() if channel['newest'] else None,
            'hours_since': _hours_since(channel['newest']),
            'state': _state_for(channel['newest'], rhythm, rhythm_known=rhythm is not None),
            'typical_gap_hours': round(rhythm, 1) if rhythm else None,
        })
    # Worst first: the reason to open this page is to find what stopped.
    order = {'stalled': 0, 'never': 1, 'quiet': 2, 'slowing': 3, 'fresh': 4}
    channels.sort(key=lambda c: (order.get(c['state'], 9), -(c['hours_since'] or 0)))

    today = _today()
    ingested_today = sum(
        1 for row in corpus.rows
        if _local_day(row['at']) == today and _local_day(row['at']) != REBUILD_DAY
    )

    return {
        'readable': True,
        'problem': None,
        'overall': {
            'state': _state_for(newest_overall),
            'newest_at': newest_overall.isoformat() if newest_overall else None,
            'hours_since': _hours_since(newest_overall),
        },
        'ingested_today': ingested_today,
        'today': today.isoformat(),
        'timezone': str(DISPLAY_TZ),
        'categories': categories,
        'channels': channels,
        'unadopted_channels': _unadopted_channel_count(),
        'thresholds': {
            'fresh_within_hours': FRESH_HOURS,
            'stalled_after_hours': STALLED_HOURS,
        },
    }


def library_totals() -> dict:
    """Corpus size. Context only — deliberately not the headline, because a total
    cannot tell you whether anything is still arriving."""
    corpus = _corpus_cache.get()
    if not corpus.ok:
        return {'readable': False, 'problem': corpus.problem}
    handles = {row['handle'].lower() for row in corpus.rows if row['handle']}
    return {
        'readable': True,
        'videos': len(corpus.rows),
        'channels': len(handles),
    }


def channel_video_counts() -> dict:
    """handle (lowercased) -> videos held in the library.

    Used to repoint the channel pages, which currently report queue rows and so
    show 0 indexed for a channel holding 86 videos.
    """
    corpus = _corpus_cache.get()
    if not corpus.ok:
        return {}
    counts: dict[str, int] = defaultdict(int)
    for row in corpus.rows:
        if row['handle']:
            counts[row['handle'].lstrip('@').lower()] += 1
    return dict(counts)
