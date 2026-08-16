"""Status endpoint's cached segment count: never a fake zero, never a
request-path scan.

The regression this pins: once segments carried 1536-dim embeddings, the
per-request `count() FROM segment` scan took ~40s, monitoring polls stacked
scans until the endpoint flapped "down", and a timed-out count was silently
reported as `segments: 0` — indistinguishable from the empty-corpus disaster
the endpoint exists to catch.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

ADMIN = Path(__file__).resolve().parents[2] / 'src' / 'admin'


def load_status(monkeypatch):
    """Exec status.py with its bare-module imports isolated and postgres
    stubbed out (these tests never touch a database)."""
    saved = {k: sys.modules.get(k) for k in ('config', 'db', 'admin_status')}
    try:
        spec = importlib.util.spec_from_file_location('config', ADMIN / 'config.py')
        cfg = importlib.util.module_from_spec(spec)
        sys.modules['config'] = cfg
        spec.loader.exec_module(cfg)

        fake_db = types.ModuleType('db')
        fake_db.get_db_cursor = lambda: (_ for _ in ()).throw(
            RuntimeError('postgres must not be touched in these tests'))
        sys.modules['db'] = fake_db

        spec = importlib.util.spec_from_file_location('admin_status',
                                                      ADMIN / 'api' / 'status.py')
        mod = importlib.util.module_from_spec(spec)
        # stop the import-time kick-off from spawning real threads/timers
        monkeypatch.setattr('threading.Thread',
                            lambda *a, **k: types.SimpleNamespace(start=lambda: None))
        sys.modules['admin_status'] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        for k, v in saved.items():
            if v is not None:
                sys.modules[k] = v
            else:
                sys.modules.pop(k, None)


@pytest.fixture()
def st(monkeypatch):
    mod = load_status(monkeypatch)
    # neutralize rescheduling inside the refresher
    monkeypatch.setattr(mod.threading, 'Timer',
                        lambda *a, **k: types.SimpleNamespace(
                            start=lambda: None,
                            __setattr__=object.__setattr__))
    return mod


def fake_surreal_factory(video_count=10, segment_count=None, segment_err=None):
    def fake(query, timeout=15):
        if 'FROM video GROUP ALL' in query:
            return [{'count': video_count}], None
        if 'FROM segment GROUP ALL' in query:
            if segment_err:
                return None, segment_err
            return [{'count': segment_count}], None
        if 'ORDER BY ingested_at' in query:
            return [{'ingested_at': '2026-08-16T00:00:00Z'}], None
        raise AssertionError(f'unexpected query: {query}')
    return fake


def test_uncounted_reports_null_not_zero(st, monkeypatch):
    monkeypatch.setattr(st, '_surreal', fake_surreal_factory())
    out = st.check_surrealdb()
    assert out['segments'] is None
    assert out['segments_counted_at'] is None
    assert out['ok'] is True          # verdict rides on videos, not segments


def test_request_path_never_counts_segments(st, monkeypatch):
    seen = []

    def spy(query, timeout=15):
        seen.append(query)
        return fake_surreal_factory()(query, timeout)

    monkeypatch.setattr(st, '_surreal', spy)
    st.check_surrealdb()
    assert not any('FROM segment' in q for q in seen)


def test_refresh_populates_cache(st, monkeypatch):
    monkeypatch.setattr(st, '_surreal',
                        fake_surreal_factory(segment_count=354196))
    st._refresh_segment_count()
    assert st._SEGMENT_COUNT_CACHE['count'] == 354196
    assert st._SEGMENT_COUNT_CACHE['counted_at'] is not None

    monkeypatch.setattr(st, '_surreal', fake_surreal_factory())
    out = st.check_surrealdb()
    assert out['segments'] == 354196
    assert out['segments_counted_at'] == st._SEGMENT_COUNT_CACHE['counted_at']


def test_failed_refresh_keeps_last_good_value(st, monkeypatch):
    monkeypatch.setattr(st, '_surreal',
                        fake_surreal_factory(segment_count=354196))
    st._refresh_segment_count()
    stamped = st._SEGMENT_COUNT_CACHE['counted_at']

    monkeypatch.setattr(st, '_surreal',
                        fake_surreal_factory(segment_err='unreachable: timeout'))
    st._refresh_segment_count()
    assert st._SEGMENT_COUNT_CACHE['count'] == 354196   # not clobbered
    assert st._SEGMENT_COUNT_CACHE['counted_at'] == stamped


def test_refresh_uses_long_timeout(st, monkeypatch):
    seen = {}

    def spy(query, timeout=15):
        seen['timeout'] = timeout
        return [{'count': 1}], None

    monkeypatch.setattr(st, '_surreal', spy)
    st._refresh_segment_count()
    assert seen['timeout'] == st.SEGMENT_COUNT_TIMEOUT_SECONDS
    assert seen['timeout'] > 15
