"""Backfill script units: the pure pieces that must not be wrong at 300k scale.

The script itself is resumable BY CONSTRUCTION (its work queue is the DB
predicate `embedding = NONE`), so these tests focus on the parts where a
silent bug corrupts data or wastes a full run: update-statement building,
the index-dimension guard, and the retry/backoff ladder.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'backfill_embeddings.py'

spec = importlib.util.spec_from_file_location('backfill_embeddings', SCRIPT)
bf = importlib.util.module_from_spec(spec)
sys.modules['backfill_embeddings'] = bf
spec.loader.exec_module(bf)


# The real index definition string from the live server (captured 2026-08-14)
LIVE_INDEX_DEF = ("DEFINE INDEX segment_embedding_idx ON segment FIELDS embedding "
                  "HNSW DIMENSION 1536 DIST COSINE TYPE F32 EFC 150 M 12 M0 24 "
                  "LM 0.40242960438184466f")


def test_dimension_parsed_from_live_index_def():
    assert bf.index_dimension({'segment_embedding_idx': LIVE_INDEX_DEF}) == 1536


def test_dimension_none_when_index_missing():
    assert bf.index_dimension({'segment_domain_idx':
                               'DEFINE INDEX segment_domain_idx ON segment FIELDS domain'}) is None


def test_update_statements_batch_and_escape():
    rows = [{'id': 'segment:abc123', 'embedding': [0.25, -0.5]},
            {'id': "segment:⟨weird'id⟩", 'embedding': [1.0, 2.0]}]
    stmts = bf.update_statements(rows)
    assert len(stmts) == 2
    assert stmts[0] == 'UPDATE segment:abc123 SET embedding = [0.25, -0.5];'
    # non-alphanumeric record ids must go through the safe form, not raw
    assert "⟨weird'id⟩" not in stmts[1]
    assert stmts[1].startswith('UPDATE type::thing(')


def test_update_statements_round_floats():
    """Full-precision floats tripled statement size and blew SurrealDB's HTTP
    body limit (413 on the first live smoke run). 7 decimals is far beyond
    what the F16 index can even represent."""
    rows = [{'id': 'segment:a', 'embedding': [0.123456789012345, 1.0]}]
    assert bf.update_statements(rows)[0] == \
        'UPDATE segment:a SET embedding = [0.1234568, 1.0];'


def test_update_requests_chunked_at_20_default():
    rows = [{'id': f'segment:{i}', 'embedding': [0.1]} for i in range(50)]
    reqs = bf.chunked_requests(bf.update_statements(rows))
    assert [len(r.splitlines()) for r in reqs] == [20, 20, 10]


def test_update_requests_chunk_size_override():
    rows = [{'id': f'segment:{i}', 'embedding': [0.1]} for i in range(120)]
    reqs = bf.chunked_requests(bf.update_statements(rows), per_request=50)
    assert [len(r.splitlines()) for r in reqs] == [50, 50, 20]


def test_index_type_parsed():
    assert bf.index_is_f16({'segment_embedding_idx': LIVE_INDEX_DEF}) is False
    f16_def = LIVE_INDEX_DEF.replace('TYPE F32', 'TYPE F16')
    assert bf.index_is_f16({'segment_embedding_idx': f16_def}) is True
    assert bf.index_is_f16({}) is False


def test_backoff_ladder_then_gives_up(monkeypatch):
    sleeps = []
    monkeypatch.setattr(bf.time, 'sleep', lambda s: sleeps.append(s))
    attempts = {'n': 0}

    def always_fails():
        attempts['n'] += 1
        return None

    result = bf.with_retries(always_fails, tries=5, base_delay=2)
    assert result is None
    assert attempts['n'] == 5
    assert sleeps == [2, 4, 8, 16]      # exponential, no sleep after the last


def test_backoff_stops_early_on_success(monkeypatch):
    sleeps = []
    monkeypatch.setattr(bf.time, 'sleep', lambda s: sleeps.append(s))
    attempts = {'n': 0}

    def flaky():
        attempts['n'] += 1
        return 'ok' if attempts['n'] == 3 else None

    assert bf.with_retries(flaky, tries=5, base_delay=1) == 'ok'
    assert attempts['n'] == 3
    assert sleeps == [1, 2]


def test_gateway_rejects_malformed_indices(monkeypatch):
    """Duplicate/missing indices with the RIGHT total count must be refused —
    zip-pairing them would silently attach vectors to the wrong segments."""
    class Resp:
        ok = True

        def json(self):
            return {'data': [{'index': 0, 'embedding': [0.1]},
                             {'index': 0, 'embedding': [0.2]}]}  # dup index

    class FakeReq:
        exceptions = bf.requests.exceptions

        @staticmethod
        def post(*a, **k):
            return Resp()

    monkeypatch.setattr(bf, 'requests', FakeReq)
    assert bf.gateway_embed(['a', 'b']) is None


def test_gateway_accepts_exact_indices(monkeypatch):
    class Resp:
        ok = True

        def json(self):
            return {'data': [{'index': 1, 'embedding': [0.2]},
                             {'index': 0, 'embedding': [0.1]}]}

    class FakeReq:
        exceptions = bf.requests.exceptions

        @staticmethod
        def post(*a, **k):
            return Resp()

    monkeypatch.setattr(bf, 'requests', FakeReq)
    assert bf.gateway_embed(['a', 'b']) == [[0.1], [0.2]]


def test_write_updates_halves_on_body_limit():
    """A size-rejected bundle splits and retries smaller instead of retrying
    the identical request forever (the live 413 failure mode)."""
    sizes = []

    def fake_surreal(req):
        n = len([l for l in req.splitlines() if l.strip()])
        sizes.append(n)
        if n > 5:
            return None            # simulated body-limit rejection
        return [{'status': 'OK', 'result': []}]

    stmts = bf.update_statements(
        [{'id': f'segment:{i}', 'embedding': [0.1]} for i in range(20)])
    ok, err = bf.write_updates(stmts, per_request=20, surreal_fn=fake_surreal)
    assert ok, err
    assert max(sizes) == 20 and max(s for s in sizes if s <= 5) <= 5
    assert sum(s for s in sizes if s <= 5) == 20    # every statement landed


def test_write_updates_reports_statement_errors():
    def fake_surreal(req):
        return [{'status': 'ERR', 'result': 'schema rejection'}]

    ok, err = bf.write_updates(['UPDATE segment:a SET embedding = [0.1];'],
                               per_request=10, surreal_fn=fake_surreal)
    assert ok is False
    assert 'schema rejection' in err


def test_remaining_count_parser():
    payload = [{'status': 'OK', 'result': [{'count': 42}]}]
    assert bf.count_from_payload(payload) == 42
    assert bf.count_from_payload([{'status': 'OK', 'result': []}]) == 0
    assert bf.count_from_payload(None) is None
    assert bf.count_from_payload([{'status': 'ERR', 'result': 'boom'}]) is None
