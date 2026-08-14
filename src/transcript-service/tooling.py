"""What the downloader itself looks like — the one thing nothing else checks.

Written 2026-08-14. Every other check in this stack asks whether our own
processes are alive and whether content is arriving. None of them ask about
yt-dlp, which is the thing that actually does the fetching, and the thing most
likely to break: it is in a permanent cat-and-mouse with YouTube, so a binary
that was fine on the day the image was built is a plausible future outage all
by itself, with no code change on our side.

This is the shape of MISTAKES.md row 1 — a check that proved a process was
listening while the work it was supposed to be doing had stopped. The freshness
checks in the admin API would eventually notice a dead yt-dlp, but only after 72
hours of silence, and they would name it "ingestion has stalled" rather than
"the downloader is broken", which sends whoever reads it looking in the wrong
place.

Served at GET /api/tooling on this service, and read across the container
boundary by the admin API's GET /api/v1/status. It lives here and not there
because yt-dlp is installed in THIS container and nowhere else — the admin
container has no downloader to inspect, so any check written there would be
inspecting the wrong filesystem and reporting a confident answer about nothing.
"""
import os
import shutil
import subprocess
import threading
import time
from datetime import date, datetime, timezone

import requests

from config import Config

# yt-dlp's version IS its release date (2026.07.04), so age needs no lookup.
# Past this many days the binary is old enough to be worth naming BEFORE it
# fails, which is the point of a leading indicator.
#
# Age ALONE is not enough, though, and getting this wrong would make the check
# useless: on the day this was written the installed 2026.07.04 was 41 days old
# AND was the newest release yt-dlp had published. A pure age threshold cannot
# tell "we are behind" from "upstream has been quiet", so a slow release month
# would light this up for something nobody can act on. A staleness problem
# therefore needs BOTH: old enough to matter, and a newer release we have not
# taken. A false alarm in the endpoint this exists to make trustworthy is not a
# small cost — it is the whole cost.
MAX_AGE_DAYS = int(os.getenv('YTDLP_MAX_AGE_DAYS', '90'))

# "Is there a newer one?" asked of PyPI, cached hard. Advisory only: if PyPI is
# unreachable the check falls back to age alone and says so, because a health
# check must not fail on account of a third party being down.
LATEST_CHECK_ENABLED = os.getenv('YTDLP_LATEST_CHECK', 'true').lower() == 'true'
LATEST_CHECK_TTL_SECONDS = int(os.getenv('YTDLP_LATEST_TTL', '21600'))
PYPI_URL = 'https://pypi.org/pypi/yt-dlp/json'

# The live probe makes real YouTube calls, so its result is cached. A container
# healthcheck polling every 60s must not turn into 1,440 extra YouTube requests
# a day on top of the backfill's own traffic.
LIVE_PROBE_TTL_SECONDS = int(os.getenv('YTDLP_LIVE_PROBE_TTL', '3600'))
LIVE_PROBE_ENABLED = os.getenv('YTDLP_LIVE_PROBE', 'true').lower() == 'true'

# Seconds between the probe's own YouTube calls. Three calls is well under the
# batch threshold in CLAUDE.md, but the probe is the one place in this service
# that fires several in a row, so it paces itself anyway.
PROBE_CALL_SPACING_SECONDS = float(os.getenv('YTDLP_PROBE_SPACING', '2'))

# Runtimes yt-dlp can use to solve YouTube's JS challenge. Deno is the one
# yt-dlp enables by default, and the one the Dockerfile installs.
JS_RUNTIMES = ('deno', 'node', 'bun')

# Presence and version cost a subprocess each. /health is polled every 60s by
# the container healthcheck under a 10s timeout, so these are cached too — just
# briefly, since they only change when the image or an auto-update does.
LOCAL_FACTS_TTL_SECONDS = int(os.getenv('YTDLP_LOCAL_FACTS_TTL', '300'))

# Opt-in, and deliberately so: an unattended upgrade of the component that
# talks to YouTube can break ingestion as easily as it can fix it, so it is a
# lever someone pulls when yt-dlp has gone stale, not a default.
AUTO_UPDATE_ENABLED = os.getenv('YTDLP_AUTO_UPDATE', 'false').lower() == 'true'

_probe_lock = threading.Lock()
_probe_cache: dict = {'at': 0.0, 'result': None}

_facts_lock = threading.Lock()
_facts_cache: dict = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cached_fact(key: str, producer):
    """Memoize a subprocess-backed fact for LOCAL_FACTS_TTL_SECONDS."""
    with _facts_lock:
        entry = _facts_cache.get(key)
        if entry and (time.monotonic() - entry['at']) < LOCAL_FACTS_TTL_SECONDS:
            return entry['value']
        value = producer()
        _facts_cache[key] = {'at': time.monotonic(), 'value': value}
        return value


def _run(cmd: list[str], timeout: int) -> tuple[int, str, str]:
    """Run a command, never raise. Returns (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, '', f"{cmd[0]}: not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, '', f"timed out after {timeout}s"
    except Exception as e:  # noqa: BLE001 - a health check must never crash
        return 1, '', str(e)


def _parse_release_date(version: str) -> date | None:
    """yt-dlp versions are dates: 2026.07.04, or 2026.07.04.232919 nightly."""
    parts = version.split('.')
    if len(parts) < 3:
        return None
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (TypeError, ValueError):
        return None


def _ytdlp_version_uncached() -> dict:
    path = shutil.which('yt-dlp')
    if not path:
        return {
            'present': False,
            'detail': 'yt-dlp is not on PATH in the transcript-service container',
            'version': None,
            'released_on': None,
            'age_days': None,
            'path': None,
        }

    rc, out, err = _run(['yt-dlp', '--version'], timeout=20)
    if rc != 0 or not out:
        return {
            'present': False,
            'detail': f"yt-dlp is installed at {path} but will not report a version: "
                      f"{err or 'no output'}",
            'version': None,
            'released_on': None,
            'age_days': None,
            'path': path,
        }

    version = out.splitlines()[0].strip()
    released = _parse_release_date(version)
    age = (date.today() - released).days if released else None
    return {
        'present': True,
        'detail': None,
        'version': version,
        'released_on': released.isoformat() if released else None,
        'age_days': age,
        'path': path,
    }


def ytdlp_version() -> dict:
    """Is yt-dlp installed, and how far behind YouTube has it fallen?"""
    return _cached_fact('ytdlp_version', _ytdlp_version_uncached)


def _js_runtime_uncached() -> dict:
    for name in JS_RUNTIMES:
        path = shutil.which(name)
        if not path:
            continue
        rc, out, _ = _run([name, '--version'], timeout=15)
        version = out.splitlines()[0].strip() if (rc == 0 and out) else None
        return {
            'available': True,
            'name': name,
            'version': version,
            'path': path,
            'searched': list(JS_RUNTIMES),
        }

    return {
        'available': False,
        'name': None,
        'version': None,
        'path': None,
        'searched': list(JS_RUNTIMES),
    }


def _version_tuple(version: str | None) -> tuple[int, ...] | None:
    """'2026.07.04' and '2026.7.4' are the same release. Compare as numbers."""
    if not version:
        return None
    parts = version.strip().split('.')
    try:
        return tuple(int(p) for p in parts)
    except (TypeError, ValueError):
        return None


def _latest_release_uncached() -> dict:
    try:
        r = requests.get(PYPI_URL, timeout=10)
        r.raise_for_status()
        version = (r.json().get('info') or {}).get('version')
    except Exception as e:  # noqa: BLE001
        return {'checked': False, 'version': None,
                'detail': f"could not ask PyPI for the newest yt-dlp: {e}"}
    if not version:
        return {'checked': False, 'version': None,
                'detail': 'PyPI response carried no version'}
    return {'checked': True, 'version': version, 'detail': None}


def latest_release() -> dict:
    """Newest yt-dlp published upstream, cached hard. Advisory, never fatal."""
    if not LATEST_CHECK_ENABLED:
        return {'checked': False, 'version': None,
                'detail': 'upstream version check switched off '
                          '(YTDLP_LATEST_CHECK=false)'}
    with _facts_lock:
        entry = _facts_cache.get('latest_release')
        if entry and (time.monotonic() - entry['at']) < LATEST_CHECK_TTL_SECONDS:
            return entry['value']
    value = _latest_release_uncached()
    with _facts_lock:
        _facts_cache['latest_release'] = {'at': time.monotonic(), 'value': value}
    return value


def js_runtime() -> dict:
    """Does yt-dlp have a JavaScript runtime available for YouTube's challenge?

    Without one, yt-dlp cannot run the player JS YouTube uses to gate formats,
    and single-video metadata calls need the override flags in fetcher.py to
    work at all. Deno is what yt-dlp reaches for by default.
    """
    return _cached_fact('js_runtime', _js_runtime_uncached)


def _probe_channel_url() -> str:
    """A real channel to list from — one we already monitor, not a stranger's."""
    handle = os.getenv('YTDLP_PROBE_CHANNEL', '').strip()
    if not handle:
        channels = getattr(Config, 'CHANNELS', None) or []
        handle = channels[0].get('handle') if channels else None
    if not handle:
        return 'https://www.youtube.com/@YouTube/videos'
    return f"https://www.youtube.com/@{handle}/videos"


def _ytdlp_prefix() -> tuple[list[str], list[str], str | None]:
    """Borrow the caller's own yt-dlp invocation so the probe tests OUR path.

    Imported lazily and defensively: fetcher.py is the busiest file in this
    service, and a health-check module must not be the reason the whole service
    fails to boot if a constant there gets renamed. If the import fails, the
    probe says so instead of guessing at flags that may no longer be right.
    """
    try:
        from fetcher import YTDLP_SINGLE_VIDEO_ARGS, ytdlp_base_cmd
    except Exception as e:  # noqa: BLE001
        return [], [], f"cannot read the fetcher's yt-dlp settings: {e}"
    return ytdlp_base_cmd(), list(YTDLP_SINGLE_VIDEO_ARGS), None


def _live_probe() -> dict:
    """Make yt-dlp do the smallest real thing it does for us, end to end.

    Three calls, paced, and they mirror production rather than testing something
    convenient:

      1. list one video id from a monitored channel  (the discovery path)
      2. read that video's upload_date WITH the override flags  (the fetch path)
      3. read it again WITHOUT them  (diagnostic only, never a failure)

    Step 3 is what makes issue #22 finishable: once a JS runtime is in the image,
    this field is the evidence that the overrides can be deleted, rather than
    someone deciding it looks safe.
    """
    started = time.monotonic()
    base, overrides, import_err = _ytdlp_prefix()
    if import_err:
        return {
            'ok': False,
            'detail': import_err,
            'ran': False,
            'checked_at': _now_iso(),
        }

    url = _probe_channel_url()
    result: dict = {
        'ok': False,
        'detail': None,
        'ran': True,
        'checked_at': _now_iso(),
        'channel': url,
        'listed_video_id': None,
        'metadata_with_overrides': None,
        'metadata_without_overrides': None,
        'override_flags_needed': None,
        'elapsed_seconds': None,
    }

    rc, out, err = _run(
        base + ['--flat-playlist', '--playlist-items', '1',
                '--no-warnings', '--print', 'id', url],
        timeout=90,
    )
    if rc != 0 or not out:
        result['detail'] = (
            f"yt-dlp could not list a single video from {url}: "
            f"{(err or 'no output')[:300]}"
        )
        result['elapsed_seconds'] = round(time.monotonic() - started, 1)
        return result

    video_id = out.splitlines()[0].strip()
    result['listed_video_id'] = video_id
    watch_url = f"https://www.youtube.com/watch?v={video_id}"

    # Same flag shape as fetch_description() in fetcher.py, deliberately: a
    # probe that exercises a different code path than production can pass while
    # production fails, which is worse than no probe at all. Only the printed
    # field differs — upload_date instead of the description — because it comes
    # from the same extracted metadata and is a few bytes rather than a few KB.
    time.sleep(PROBE_CALL_SPACING_SECONDS)
    rc, out, err = _run(
        base + overrides + ['--skip-download', '--no-warnings',
                            '--print', '%(upload_date)s', watch_url],
        timeout=90,
    )
    with_overrides_ok = rc == 0 and bool(out.strip()) and out.strip() != 'NA'
    result['metadata_with_overrides'] = 'ok' if with_overrides_ok else 'failed'
    if not with_overrides_ok:
        result['detail'] = (
            f"yt-dlp fetched no publish date for {video_id}, which is the exact "
            f"failure that fills the corpus with dateless files: "
            f"{(err or out or 'no output')[:300]}"
        )
        result['elapsed_seconds'] = round(time.monotonic() - started, 1)
        return result

    time.sleep(PROBE_CALL_SPACING_SECONDS)
    rc, out, _ = _run(
        base + ['--skip-download', '--no-warnings',
                '--print', '%(upload_date)s', watch_url],
        timeout=90,
    )
    without_ok = rc == 0 and bool(out.strip()) and out.strip() != 'NA'
    result['metadata_without_overrides'] = 'ok' if without_ok else 'failed'
    result['override_flags_needed'] = not without_ok

    result['ok'] = True
    result['elapsed_seconds'] = round(time.monotonic() - started, 1)
    return result


def live_probe(force: bool = False) -> dict:
    """Cached wrapper around the real calls. Never blocks two callers at once."""
    if not LIVE_PROBE_ENABLED:
        return {
            'ok': None,
            'ran': False,
            'detail': 'live probe switched off (YTDLP_LIVE_PROBE=false) — '
                      'presence and version are still checked',
            'checked_at': _now_iso(),
        }

    with _probe_lock:
        age = time.monotonic() - _probe_cache['at']
        cached = _probe_cache['result']
        if cached is not None and not force and age < LIVE_PROBE_TTL_SECONDS:
            return {**cached, 'cached': True, 'cache_age_seconds': round(age)}

        fresh = _live_probe()
        _probe_cache['at'] = time.monotonic()
        _probe_cache['result'] = fresh
        return {**fresh, 'cached': False, 'cache_age_seconds': 0}


def tooling_status(force_probe: bool = False) -> dict:
    """The whole picture, with every failure named in plain language."""
    ytdlp = ytdlp_version()
    js = js_runtime()
    probe = live_probe(force=force_probe)
    upstream = latest_release() if ytdlp['present'] else {
        'checked': False, 'version': None, 'detail': 'yt-dlp is not installed'
    }

    installed_v = _version_tuple(ytdlp.get('version'))
    latest_v = _version_tuple(upstream.get('version'))
    behind = bool(installed_v and latest_v and installed_v < latest_v)
    ytdlp = {
        **ytdlp,
        'latest_version': upstream.get('version'),
        'update_available': behind if (installed_v and latest_v) else None,
        'upstream_check': upstream.get('detail'),
    }

    problems: list[str] = []

    if not ytdlp['present']:
        problems.append(f"yt-dlp: {ytdlp['detail']} — nothing can be fetched")
    else:
        age = ytdlp['age_days']
        if age is None:
            problems.append(
                f"yt-dlp: version '{ytdlp['version']}' is not a release date, so "
                f"its age cannot be judged"
            )
        elif age > MAX_AGE_DAYS and behind:
            problems.append(
                f"yt-dlp is {age} days old (running {ytdlp['version']}, released "
                f"{ytdlp['released_on']}) and {ytdlp['latest_version']} is "
                f"available — YouTube changes faster than that, and a stale "
                f"downloader is the most likely next outage. Set "
                f"YTDLP_AUTO_UPDATE=true and restart the transcript service to "
                f"take it; no image rebuild needed"
            )
        elif age > MAX_AGE_DAYS and not upstream.get('checked'):
            problems.append(
                f"yt-dlp is {age} days old (threshold {MAX_AGE_DAYS} days) and "
                f"whether a newer release exists could not be established: "
                f"{upstream.get('detail')}"
            )

    if probe.get('ran') and probe.get('ok') is False:
        problems.append(f"yt-dlp cannot complete a real call: {probe.get('detail')}")

    # A missing JS runtime is REPORTED but is not a problem while the override
    # flags are compensating for it. Calling it a failure would put this stack
    # into a permanent degraded state describing something that currently works
    # — which is how a health check stops being believed. Issue #22 removes the
    # workaround; until then this line is the reason the workaround exists.
    if js['available']:
        override_note = (
            f"a {js['name']} runtime is present, so yt-dlp can run YouTube's "
            f"player JS normally"
        )
    else:
        override_note = (
            'no JavaScript runtime in this image, so single-video metadata runs '
            'on the two override flags instead (issue #22)'
        )

    return {
        'ok': not problems,
        'problems': problems,
        'checked_at': _now_iso(),
        'yt_dlp': ytdlp,
        'js_runtime': js,
        'override_flags': {
            'in_use': _ytdlp_prefix()[1],
            'still_needed': probe.get('override_flags_needed'),
            'detail': override_note,
        },
        'live_probe': probe,
        'auto_update': {
            'enabled': AUTO_UPDATE_ENABLED,
            'detail': 'upgrades yt-dlp on container start when '
                      'YTDLP_AUTO_UPDATE=true — no image rebuild needed, and off '
                      'unless deliberately switched on',
        },
        'thresholds': {
            'max_age_days': MAX_AGE_DAYS,
            'live_probe_ttl_seconds': LIVE_PROBE_TTL_SECONDS,
            'staleness_needs_both': 'older than max_age_days AND a newer '
                                    'release published upstream',
        },
    }


def tooling_summary() -> dict:
    """Three lines for /health — local facts only, no network, no waiting.

    Deliberately does NOT run the live probe: /health is polled every 60s under
    a 10s timeout, and a health check that makes an outbound call it can be
    blocked on is a health check that fails when YouTube rate-limits us, which
    has nothing to do with whether this container is well.
    """
    ytdlp = ytdlp_version()
    js = js_runtime()
    return {
        'yt_dlp': ytdlp['version'] if ytdlp['present'] else 'MISSING',
        'yt_dlp_age_days': ytdlp['age_days'],
        'js_runtime': js['name'] if js['available'] else None,
        'full_report': 'GET /api/tooling',
    }
