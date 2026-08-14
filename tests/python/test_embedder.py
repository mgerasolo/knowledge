"""Embedder contract: task prefixes, batching, and honest failure reporting.

The deployed service spent months silently skipping embeddings because the
gateway key was never wired and `get_embedding` returned None without anyone
noticing — `embed_video` still reported `embeddings_generated: true`. These
tests pin the honest-failure contract so that can't recur silently.
"""
import json
from pathlib import Path

import pytest

from embedding_loader import load_embedder

FIXTURE = json.loads(
    (Path(__file__).parent / 'fixtures' / 'real_segments_2026-08-14.json')
    .read_text())


@pytest.fixture()
def emb(monkeypatch):
    _cfg, emb = load_embedder()
    monkeypatch.setattr(emb.Config, 'LITELLM_API_KEY', 'test-key')
    monkeypatch.setattr(emb.Config, 'EMBEDDING_DOC_PREFIX', 'search_document: ')
    monkeypatch.setattr(emb.Config, 'EMBEDDING_QUERY_PREFIX', 'search_query: ')
    return emb


class FakeRequests:
    """Stands in for the `requests` module inside embedder."""

    def __init__(self, dim=4, fail=False):
        self.calls = []
        self.dim = dim
        self.fail = fail

    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append({'url': url, 'json': json})
        fake = self

        class Resp:
            ok = not fake.fail

            def json(self):
                inputs = fake.calls[-1]['json']['input']
                if isinstance(inputs, str):
                    inputs = [inputs]
                # reversed index order on purpose: callers must re-sort
                return {'data': [
                    {'index': i, 'embedding': [float(i)] * fake.dim}
                    for i in reversed(range(len(inputs)))
                ]}

        return Resp()


def test_document_prefix_applied(emb, monkeypatch):
    fake = FakeRequests()
    monkeypatch.setattr(emb, 'requests', fake)
    emb.get_embedding('hello world', kind='document')
    assert fake.calls[0]['json']['input'] == 'search_document: hello world'


def test_query_prefix_applied(emb, monkeypatch):
    fake = FakeRequests()
    monkeypatch.setattr(emb, 'requests', fake)
    emb.get_embedding('find me', kind='query')
    assert fake.calls[0]['json']['input'] == 'search_query: find me'


def test_default_kind_is_document(emb, monkeypatch):
    fake = FakeRequests()
    monkeypatch.setattr(emb, 'requests', fake)
    emb.get_embedding('hello')
    assert fake.calls[0]['json']['input'].startswith('search_document: ')


def test_truncation_happens_before_prefix(emb, monkeypatch):
    """The 8000-char cap applies to the text; the prefix must survive."""
    fake = FakeRequests()
    monkeypatch.setattr(emb, 'requests', fake)
    emb.get_embedding('x' * 9000)
    sent = fake.calls[0]['json']['input']
    assert sent.startswith('search_document: ')
    assert len(sent) == len('search_document: ') + 8000


def test_empty_prefix_sends_raw_text(emb, monkeypatch):
    monkeypatch.setattr(emb.Config, 'EMBEDDING_DOC_PREFIX', '')
    fake = FakeRequests()
    monkeypatch.setattr(emb, 'requests', fake)
    emb.get_embedding('raw text')
    assert fake.calls[0]['json']['input'] == 'raw text'


def test_missing_key_returns_none_without_http(emb, monkeypatch):
    monkeypatch.setattr(emb.Config, 'LITELLM_API_KEY', '')
    fake = FakeRequests()
    monkeypatch.setattr(emb, 'requests', fake)
    assert emb.get_embedding('hello') is None
    assert fake.calls == []


def test_batch_splits_at_64_and_preserves_order(emb, monkeypatch):
    fake = FakeRequests()
    monkeypatch.setattr(emb, 'requests', fake)
    texts = [f'text number {i}' for i in range(130)]
    vecs = emb.get_embeddings(texts, kind='document')
    assert len(fake.calls) == 3            # 64 + 64 + 2
    assert [len(c['json']['input']) for c in fake.calls] == [64, 64, 2]
    assert len(vecs) == 130
    # FakeRequests returns embeddings in REVERSED index order; a correct
    # implementation re-sorts by index, so position 0 gets index 0's vector.
    assert vecs[0] == [0.0, 0.0, 0.0, 0.0]
    assert fake.calls[0]['json']['input'][0] == 'search_document: text number 0'


def test_batch_missing_key_returns_all_none(emb, monkeypatch):
    monkeypatch.setattr(emb.Config, 'LITELLM_API_KEY', '')
    fake = FakeRequests()
    monkeypatch.setattr(emb, 'requests', fake)
    assert emb.get_embeddings(['a', 'b']) == [None, None]
    assert fake.calls == []


def test_batch_gateway_failure_returns_none_per_text(emb, monkeypatch):
    fake = FakeRequests(fail=True)
    monkeypatch.setattr(emb, 'requests', fake)
    assert emb.get_embeddings(['a', 'b', 'c']) == [None, None, None]


def test_batch_malformed_indices_rejected(emb, monkeypatch):
    """Right count, wrong indices — must yield Nones, never mispair."""
    class BadIndexRequests(FakeRequests):
        def post(self, url, headers=None, json=None, timeout=None):
            self.calls.append({'url': url, 'json': json})

            class Resp:
                ok = True

                def json(_self):
                    return {'data': [
                        {'index': 0, 'embedding': [0.1] * 4},
                        {'index': 0, 'embedding': [0.2] * 4},  # duplicate
                    ]}

            return Resp()

    monkeypatch.setattr(emb, 'requests', BadIndexRequests())
    assert emb.get_embeddings(['a', 'b']) == [None, None]


def _real_video_payload():
    """A payload built from the frozen REAL fixture segments."""
    segs = FIXTURE['segments'][:3]
    return {
        'video_id': segs[0]['video_youtube_id'],
        'title': 'fixture-backed video',
        'channel_handle': 'fixture-channel',
        'domain': segs[0]['domain'],
        'segments': [
            {'start': s['start_time'],
             'duration': max(0.0, s['end_time'] - s['start_time']),
             'text': s['text']}
            for s in segs
        ],
    }


def test_embed_video_reports_embedding_failures_honestly(emb, monkeypatch):
    """Gateway down: segments still written, but the result must say
    embeddings_generated=False and count the failures — never claim success."""
    monkeypatch.setattr(emb, 'surreal_write', lambda q: (True, None))
    monkeypatch.setattr(emb, 'get_embedding', lambda text, kind='document': None)

    result = emb.embed_video(_real_video_payload())

    assert result['success'] is True
    assert result['embeddings_generated'] is False
    assert result['embeddings_failed'] == result['segment_count']
    assert result['segment_count'] > 0


def test_embed_video_success_counts_no_failures(emb, monkeypatch):
    monkeypatch.setattr(emb, 'surreal_write', lambda q: (True, None))
    monkeypatch.setattr(emb, 'get_embedding',
                        lambda text, kind='document': [0.1, 0.2, 0.3])

    result = emb.embed_video(_real_video_payload())

    assert result['success'] is True
    assert result['embeddings_generated'] is True
    assert result['embeddings_failed'] == 0


def test_embed_video_skip_embeddings_reports_not_generated(emb, monkeypatch):
    monkeypatch.setattr(emb, 'surreal_write', lambda q: (True, None))

    result = emb.embed_video(_real_video_payload(), skip_embeddings=True)

    assert result['success'] is True
    assert result['embeddings_generated'] is False
    assert result['embeddings_failed'] == 0
