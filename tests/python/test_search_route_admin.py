"""GET /videos/api/semantic-search on the Admin API — the consumer surface.

Thin proxy to the embedding service. The contract consumers rely on:
400 = fix your request · 503 + retryable = try again later · 200 = answer
(empty results included). The embedding service being down must never
surface as a 200-with-error-inside or a bare 500.
"""
import pytest
from flask import Flask

from embedding_loader import load_admin_videos

_cfg, videos = load_admin_videos()


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(videos.videos_bp, url_prefix='/videos')
    return app.test_client()


class FakeResponse:
    def __init__(self, status_code=200, body=None, bad_json=False):
        self.status_code = status_code
        self._body = body or {}
        self._bad_json = bad_json
        self.ok = status_code < 400

    def json(self):
        if self._bad_json:
            raise ValueError('not json')
        return self._body


def test_missing_q_is_400(client):
    resp = client.get('/videos/api/semantic-search')
    assert resp.status_code == 400


def test_short_q_is_400(client):
    resp = client.get('/videos/api/semantic-search?q=ab')
    assert resp.status_code == 400


def test_success_passthrough(client, monkeypatch):
    payload = {'success': True, 'query': 'bible wealth',
               'results': [{'video_youtube_id': 'x', 'video_title': 't',
                            'chunk_index': 0, 'start_time': 0.0,
                            'end_time': 5.0, 'text': 'real', 'domain': 'religion',
                            'score': 0.51}],
               'count': 1, 'model': 'test-model'}
    seen = {}

    def fake_post(url, json=None, timeout=None):
        seen.update(url=url, payload=json, timeout=timeout)
        return FakeResponse(200, payload)

    monkeypatch.setattr(videos.requests, 'post', fake_post)
    resp = client.get('/videos/api/semantic-search'
                      '?q=bible wealth&domain=religion&limit=5&min_score=0.5')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['results'] == payload['results']
    assert body['count'] == 1
    assert body['model'] == 'test-model'
    assert seen['url'].endswith('/api/search')
    assert seen['payload'] == {'query': 'bible wealth', 'domain': 'religion',
                               'limit': 5, 'min_score': 0.5}


def test_limit_clamped_to_50(client, monkeypatch):
    seen = {}

    def fake_post(url, json=None, timeout=None):
        seen.update(payload=json)
        return FakeResponse(200, {'success': True, 'query': 'q',
                                  'results': [], 'count': 0, 'model': 'm'})

    monkeypatch.setattr(videos.requests, 'post', fake_post)
    client.get('/videos/api/semantic-search?q=bible wealth&limit=500')
    assert seen['payload']['limit'] == 50


def test_embedding_service_down_is_retryable_503(client, monkeypatch):
    def fake_post(url, json=None, timeout=None):
        raise videos.requests.exceptions.ConnectionError('refused')

    monkeypatch.setattr(videos.requests, 'post', fake_post)
    resp = client.get('/videos/api/semantic-search?q=bible wealth')
    assert resp.status_code == 503
    body = resp.get_json()
    assert body['retryable'] is True
    assert body['source'] == 'embedding-service'


def test_embedding_service_503_passthrough(client, monkeypatch):
    def fake_post(url, json=None, timeout=None):
        return FakeResponse(503, {'error': 'gateway down', 'success': False,
                                  'retryable': True})

    monkeypatch.setattr(videos.requests, 'post', fake_post)
    resp = client.get('/videos/api/semantic-search?q=bible wealth')
    assert resp.status_code == 503
    assert resp.get_json()['retryable'] is True


def test_embedding_service_400_passthrough(client, monkeypatch):
    def fake_post(url, json=None, timeout=None):
        return FakeResponse(400, {'error': 'Query too short', 'success': False})

    monkeypatch.setattr(videos.requests, 'post', fake_post)
    resp = client.get('/videos/api/semantic-search?q=bible wealth')
    assert resp.status_code == 400


def test_non_json_reply_is_503(client, monkeypatch):
    def fake_post(url, json=None, timeout=None):
        return FakeResponse(200, bad_json=True)

    monkeypatch.setattr(videos.requests, 'post', fake_post)
    resp = client.get('/videos/api/semantic-search?q=bible wealth')
    assert resp.status_code == 503
    assert resp.get_json()['retryable'] is True


def test_bad_numeric_params_are_400(client):
    resp = client.get('/videos/api/semantic-search?q=bible wealth&limit=lots')
    assert resp.status_code == 400
    resp = client.get('/videos/api/semantic-search?q=bible wealth&min_score=high')
    assert resp.status_code == 400
