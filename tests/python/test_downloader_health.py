"""Tests for the downloader check — the one that watches yt-dlp itself.

Every other check in this stack watches our own services. This one watches the
tool that does the fetching, which is the component most likely to break on its
own: yt-dlp is in a permanent cat-and-mouse with YouTube, so the binary that
worked when the image was built can stop working with no change on our side.

These tests lean on the cases where a health check earns or loses its keep:

  - it must FAIL when the tool is missing or cannot make a real call
  - it must NOT fail for things nobody can act on (a quiet release month, an
    absent JS runtime that the override flags are already compensating for)
  - a broken downloader must DEGRADE the stack, never mark it down — the corpus
    stays complete and readable, it just stops growing

The second group matters as much as the first. A check that cries wolf gets
ignored, and an ignored check is the same as no check, which is how the outage
in MISTAKES.md row 1 ran for two weeks.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src' / 'admin'))
sys.path.insert(0, str(ROOT / 'src' / 'transcript-service'))

from api import status  # noqa: E402
import tooling  # noqa: E402


# --------------------------------------------------------------------------
# The admin side: asking the transcript service across the container boundary
# --------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code=200, payload=None, is_json=True):
        self.status_code = status_code
        self.ok = 200 <= status_code < 400
        self._payload = payload
        self._is_json = is_json

    def json(self):
        if not self._is_json:
            raise ValueError('not json')
        return self._payload


@pytest.fixture
def healthy_stores(monkeypatch):
    """Datastores fine, so only the downloader can move the verdict."""
    monkeypatch.setattr(status, 'check_postgres',
                        lambda: {'ok': True, 'marked_indexed': 10,
                                 'hours_since_newest': 1.0})
    monkeypatch.setattr(status, 'check_surrealdb',
                        lambda: {'ok': True, 'videos': 10,
                                 'hours_since_newest': 1.0})
    monkeypatch.setattr(status, 'check_transcript_files',
                        lambda: {'ok': True, 'files': 10,
                                 'hours_since_newest': 1.0})


def test_a_working_downloader_reports_its_version_and_runtime(monkeypatch):
    monkeypatch.setattr(status.requests, 'get', lambda *a, **k: FakeResponse(
        payload={
            'ok': True,
            'problems': [],
            'yt_dlp': {'version': '2026.07.04', 'age_days': 41,
                       'latest_version': '2026.7.4', 'update_available': False},
            'js_runtime': {'name': 'deno', 'available': True},
            'override_flags': {'still_needed': False},
            'live_probe': {'ok': True, 'checked_at': 'now', 'cached': True},
        }))
    result = status.check_downloader()
    assert result['ok'] is True
    assert result['detail'] is None
    assert result['yt_dlp_version'] == '2026.07.04'
    assert result['js_runtime'] == 'deno'
    assert result['last_real_call']['ok'] is True


def test_the_tools_problems_become_the_components_detail(monkeypatch):
    monkeypatch.setattr(status.requests, 'get', lambda *a, **k: FakeResponse(
        payload={
            'ok': False,
            'problems': ['yt-dlp is not on PATH — nothing can be fetched'],
            'yt_dlp': {'version': None},
            'js_runtime': {},
            'override_flags': {},
            'live_probe': {},
        }))
    result = status.check_downloader()
    assert result['ok'] is False
    assert 'not on PATH' in result['detail']


def test_a_transcript_service_predating_the_check_says_so_plainly(monkeypatch):
    """404 must not read as "the downloader is broken" — it is a rebuild lag."""
    monkeypatch.setattr(status.requests, 'get',
                        lambda *a, **k: FakeResponse(status_code=404))
    result = status.check_downloader()
    assert result['ok'] is False
    assert 'rebuilt' in result['detail']
    assert '404' in result['detail']


def test_an_unreachable_transcript_service_is_named_not_swallowed(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError('connection refused')
    monkeypatch.setattr(status.requests, 'get', boom)
    result = status.check_downloader()
    assert result['ok'] is False
    assert 'unreachable' in result['detail']


def test_a_non_json_answer_does_not_crash_the_status_endpoint(monkeypatch):
    monkeypatch.setattr(status.requests, 'get',
                        lambda *a, **k: FakeResponse(is_json=False))
    result = status.check_downloader()
    assert result['ok'] is False
    assert 'did not return JSON' in result['detail']


def test_a_broken_downloader_degrades_the_stack_but_never_marks_it_down(
        monkeypatch, healthy_stores):
    """The corpus is still complete and queryable — it has just stopped growing.

    503 means "consumers cannot read". A dead downloader does not mean that, and
    saying it does would send readers away from data that is perfectly fine.
    """
    monkeypatch.setattr(status, 'check_downloader',
                        lambda: {'ok': False, 'detail': 'yt-dlp is not installed'})
    document, code = status.build_status()
    assert code == 200
    assert document['status'] == 'degraded'
    assert any(p.startswith('downloader:') for p in document['problems'])


def test_the_downloader_is_named_rather_than_left_to_the_freshness_warning(
        monkeypatch, healthy_stores):
    """Issue #23's whole point: name the cause, not the eventual symptom."""
    monkeypatch.setattr(status, 'check_downloader',
                        lambda: {'ok': False, 'detail': 'yt-dlp is not installed'})
    document, _ = status.build_status()
    assert document['components']['downloader']['ok'] is False
    assert 'freshness' not in ' '.join(document['problems'])


def test_a_healthy_downloader_adds_no_problems(monkeypatch, healthy_stores):
    monkeypatch.setattr(status, 'check_downloader',
                        lambda: {'ok': True, 'detail': None})
    document, code = status.build_status()
    assert code == 200
    assert document['status'] == 'ok'
    assert document['problems'] == []


# --------------------------------------------------------------------------
# The transcript-service side: what the tool actually looks like
# --------------------------------------------------------------------------

@pytest.fixture
def quiet_probe(monkeypatch):
    """No YouTube calls from a unit test."""
    monkeypatch.setattr(tooling, 'live_probe',
                        lambda force=False: {'ok': None, 'ran': False,
                                             'detail': 'off in tests'})


def _installed(version='2026.07.04', age_days=41, present=True):
    return {
        'present': present,
        'detail': None if present else 'yt-dlp is not on PATH',
        'version': version if present else None,
        'released_on': '2026-07-04' if present else None,
        'age_days': age_days if present else None,
        'path': '/usr/local/bin/yt-dlp' if present else None,
    }


def _no_js():
    return {'available': False, 'name': None, 'version': None, 'path': None,
            'searched': list(tooling.JS_RUNTIMES)}


def test_a_missing_downloader_is_a_problem(monkeypatch, quiet_probe):
    monkeypatch.setattr(tooling, 'ytdlp_version', lambda: _installed(present=False))
    monkeypatch.setattr(tooling, 'js_runtime', _no_js)
    document = tooling.tooling_status()
    assert document['ok'] is False
    assert 'nothing can be fetched' in document['problems'][0]


def test_old_but_already_the_newest_release_is_not_a_problem(
        monkeypatch, quiet_probe):
    """The trap this avoids.

    On the day this was written the installed yt-dlp was 41 days old AND was the
    newest release published. Age alone cannot tell "we are behind" from
    "upstream has been quiet", so a threshold on age alone would fire for
    something nobody can act on.
    """
    monkeypatch.setattr(tooling, 'MAX_AGE_DAYS', 10)
    monkeypatch.setattr(tooling, 'ytdlp_version', lambda: _installed())
    monkeypatch.setattr(tooling, 'js_runtime', _no_js)
    monkeypatch.setattr(tooling, 'latest_release',
                        lambda: {'checked': True, 'version': '2026.7.4',
                                 'detail': None})
    document = tooling.tooling_status()
    assert document['ok'] is True
    assert document['problems'] == []
    assert document['yt_dlp']['update_available'] is False


def test_old_and_a_newer_release_exists_is_a_problem(monkeypatch, quiet_probe):
    monkeypatch.setattr(tooling, 'MAX_AGE_DAYS', 10)
    monkeypatch.setattr(tooling, 'ytdlp_version', lambda: _installed())
    monkeypatch.setattr(tooling, 'js_runtime', _no_js)
    monkeypatch.setattr(tooling, 'latest_release',
                        lambda: {'checked': True, 'version': '2026.12.31',
                                 'detail': None})
    document = tooling.tooling_status()
    assert document['ok'] is False
    assert '2026.12.31 is available' in document['problems'][0]
    assert 'YTDLP_AUTO_UPDATE=true' in document['problems'][0]


def test_old_and_upstream_unknown_says_it_could_not_tell(monkeypatch, quiet_probe):
    monkeypatch.setattr(tooling, 'MAX_AGE_DAYS', 10)
    monkeypatch.setattr(tooling, 'ytdlp_version', lambda: _installed())
    monkeypatch.setattr(tooling, 'js_runtime', _no_js)
    monkeypatch.setattr(tooling, 'latest_release',
                        lambda: {'checked': False, 'version': None,
                                 'detail': 'PyPI unreachable'})
    document = tooling.tooling_status()
    assert document['ok'] is False
    assert 'could not be established' in document['problems'][0]


def test_a_missing_js_runtime_is_reported_but_is_not_a_failure(
        monkeypatch, quiet_probe):
    """It is what the override flags exist for. Calling it broken would put the
    stack into a permanent degraded state describing something that works."""
    monkeypatch.setattr(tooling, 'ytdlp_version', lambda: _installed())
    monkeypatch.setattr(tooling, 'js_runtime', _no_js)
    monkeypatch.setattr(tooling, 'latest_release',
                        lambda: {'checked': True, 'version': '2026.7.4',
                                 'detail': None})
    document = tooling.tooling_status()
    assert document['ok'] is True
    assert document['js_runtime']['available'] is False
    assert 'issue #22' in document['override_flags']['detail']


def test_a_failed_real_call_is_a_problem(monkeypatch):
    monkeypatch.setattr(tooling, 'ytdlp_version', lambda: _installed())
    monkeypatch.setattr(tooling, 'js_runtime', _no_js)
    monkeypatch.setattr(tooling, 'latest_release',
                        lambda: {'checked': True, 'version': '2026.7.4',
                                 'detail': None})
    monkeypatch.setattr(tooling, 'live_probe',
                        lambda force=False: {'ok': False, 'ran': True,
                                             'detail': 'HTTP Error 403'})
    document = tooling.tooling_status()
    assert document['ok'] is False
    assert 'cannot complete a real call' in document['problems'][0]


def test_version_comparison_ignores_zero_padding():
    """yt-dlp prints 2026.07.04; PyPI prints 2026.7.4. Same release."""
    assert tooling._version_tuple('2026.07.04') == tooling._version_tuple('2026.7.4')
    assert tooling._version_tuple('2026.07.04') < tooling._version_tuple('2026.8.1')
    assert tooling._version_tuple('not-a-version') is None


def test_the_health_summary_makes_no_network_call(monkeypatch):
    """/health is polled every 60s under a 10s timeout. It must never be able to
    block on YouTube — a rate-limited YouTube says nothing about whether this
    container is well."""
    def forbidden(*a, **k):
        raise AssertionError('tooling_summary must not touch the network')
    monkeypatch.setattr(tooling, 'live_probe', forbidden)
    monkeypatch.setattr(tooling, 'latest_release', forbidden)
    monkeypatch.setattr(tooling, 'ytdlp_version', lambda: _installed())
    monkeypatch.setattr(tooling, 'js_runtime', _no_js)
    summary = tooling.tooling_summary()
    assert summary['yt_dlp'] == '2026.07.04'
    assert summary['js_runtime'] is None
