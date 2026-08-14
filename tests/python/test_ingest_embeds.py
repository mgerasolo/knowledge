"""Ingest path: new videos get embeddings by default.

The old hardcoded `skip_embeddings: True` ("no semantic search consumes
embeddings yet") is exactly how the corpus ended up with zero vectors.
The flag is now config: EMBED_ON_INGEST, default ON.
"""
import pytest

from embedding_loader import load_transcript_service


class FakeResponse:
    ok = True
    status_code = 200

    def json(self):
        return {'success': True, 'segment_count': 1,
                'embeddings_generated': True, 'embeddings_failed': 0}


@pytest.fixture()
def ts(monkeypatch):
    cfg, fetcher = load_transcript_service()
    seen = {}

    def fake_post(url, json=None, timeout=None):
        seen.update(url=url, payload=json)
        return FakeResponse()

    monkeypatch.setattr(fetcher.requests, 'post', fake_post)
    return cfg, fetcher, seen


VIDEO = {'id': 'vid123', 'title': 'T', 'channel_handle': 'ch',
         'channel_name': 'Ch', 'domain': 'ai'}
SEGMENTS = [{'start': 0.0, 'duration': 5.0, 'text': 'real segment text'}]


def test_default_config_embeds_on_ingest(ts):
    cfg, fetcher, seen = ts
    assert cfg.Config.EMBED_ON_INGEST is True


def test_index_video_embeds_when_enabled(ts, monkeypatch):
    cfg, fetcher, seen = ts
    monkeypatch.setattr(fetcher.Config, 'EMBED_ON_INGEST', True)
    indexed, err = fetcher._index_video(VIDEO, SEGMENTS, 'desc')
    assert indexed is True and err is None
    assert seen['payload']['skip_embeddings'] is False


def test_index_video_skips_when_disabled(ts, monkeypatch):
    cfg, fetcher, seen = ts
    monkeypatch.setattr(fetcher.Config, 'EMBED_ON_INGEST', False)
    fetcher._index_video(VIDEO, SEGMENTS, 'desc')
    assert seen['payload']['skip_embeddings'] is True
