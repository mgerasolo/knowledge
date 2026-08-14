"""POST /api/search route contract on the embedding service.

Failure paths are the point: a dead gateway must read as a retryable 503,
a bad request as a 400, and an empty result as a successful 200 — consumers
must be able to tell these apart by status code alone.
"""
import pytest

from embedding_loader import load_app


@pytest.fixture()
def stack(monkeypatch):
    _cfg, _emb, srch, appm = load_app()
    client = appm.app.test_client()
    return srch, appm, client


def test_missing_query_is_400(stack):
    _, _, client = stack
    resp = client.post('/api/search', json={})
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False


def test_short_query_is_400(stack):
    _, _, client = stack
    resp = client.post('/api/search', json={'query': 'ab'})
    assert resp.status_code == 400


def test_no_body_is_400(stack):
    _, _, client = stack
    resp = client.post('/api/search',
                       data='not json', content_type='text/plain')
    assert resp.status_code == 400


@pytest.mark.parametrize('body', ['[]', '"just a string"', '1', '[1,2,3]'])
def test_non_object_json_is_400_not_500(stack, body):
    """Valid JSON that isn't an object must hit the 400 contract, not crash."""
    _, _, client = stack
    resp = client.post('/api/search', data=body,
                       content_type='application/json')
    assert resp.status_code == 400


def test_gateway_down_is_retryable_503(stack, monkeypatch):
    srch, appm, client = stack

    def boom(query_text, domain=None, limit=10, min_score=0.4):
        raise srch.EmbeddingUnavailable('no key')

    monkeypatch.setattr(appm, 'semantic_search', boom)
    resp = client.post('/api/search', json={'query': 'bible wealth'})
    assert resp.status_code == 503
    body = resp.get_json()
    assert body['success'] is False
    assert body['retryable'] is True


def test_surrealdb_failure_is_retryable_503(stack, monkeypatch):
    srch, appm, client = stack

    def boom(query_text, domain=None, limit=10, min_score=0.4):
        raise RuntimeError('SurrealDB unreachable')

    monkeypatch.setattr(appm, 'semantic_search', boom)
    resp = client.post('/api/search', json={'query': 'bible wealth'})
    assert resp.status_code == 503
    assert resp.get_json()['retryable'] is True


def test_success_envelope(stack, monkeypatch):
    srch, appm, client = stack
    fake_results = [{'video_youtube_id': 'abc', 'video_title': 't',
                     'chunk_index': 0, 'start_time': 1.0, 'end_time': 2.0,
                     'text': 'real text', 'domain': 'religion',
                     'score': 0.55}]

    monkeypatch.setattr(
        appm, 'semantic_search',
        lambda query_text, domain=None, limit=10, min_score=0.4:
        {'results': fake_results, 'model': 'test-model'})

    resp = client.post('/api/search', json={'query': 'bible wealth'})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['success'] is True
    assert body['query'] == 'bible wealth'
    assert body['results'] == fake_results
    assert body['count'] == 1
    assert body['model'] == 'test-model'


def test_empty_results_is_200(stack, monkeypatch):
    srch, appm, client = stack
    monkeypatch.setattr(
        appm, 'semantic_search',
        lambda query_text, domain=None, limit=10, min_score=0.4:
        {'results': [], 'model': 'test-model'})

    resp = client.post('/api/search',
                       json={'query': 'anything', 'domain': 'no-matches'})
    assert resp.status_code == 200
    assert resp.get_json()['count'] == 0


def test_params_forwarded_and_limit_clamped(stack, monkeypatch):
    srch, appm, client = stack
    seen = {}

    def spy(query_text, domain=None, limit=10, min_score=0.4):
        seen.update(query_text=query_text, domain=domain,
                    limit=limit, min_score=min_score)
        return {'results': [], 'model': 'm'}

    monkeypatch.setattr(appm, 'semantic_search', spy)
    client.post('/api/search', json={'query': 'bible wealth',
                                     'domain': 'religion',
                                     'limit': 5000,
                                     'min_score': 0.6})
    assert seen['domain'] == 'religion'
    assert seen['limit'] == 100          # clamped
    assert seen['min_score'] == 0.6


def test_bad_limit_type_is_400(stack):
    _, _, client = stack
    resp = client.post('/api/search',
                       json={'query': 'bible wealth', 'limit': 'lots'})
    assert resp.status_code == 400
