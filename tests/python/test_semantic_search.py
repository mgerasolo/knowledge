"""semantic_search contract: KNN query construction, score mapping, filters,
and the failure paths (gateway down, SurrealDB error).

Vectors and distances come from the frozen REAL fixture (live corpus + live
model, captured 2026-08-14) — no invented embeddings.
"""
import json
from pathlib import Path

import pytest

from embedding_loader import load_search

FIXTURE = json.loads(
    (Path(__file__).parent / 'fixtures' / 'real_segments_2026-08-14.json')
    .read_text())

QUERY_VEC = FIXTURE['queries'][0]['embedding']   # "what the Bible teaches..."


def real_cosine_distance(a, b):
    # fixture vectors are L2-normalised, so distance = 1 - dot
    return 1.0 - sum(x * y for x, y in zip(a, b))


@pytest.fixture()
def srch(monkeypatch):
    _cfg, emb, srch = load_search()
    monkeypatch.setattr(srch, 'get_embedding',
                        lambda text, kind='document': QUERY_VEC)
    return srch


class FakeSurreal:
    """Dispatches on query text: segment KNN vs video title join.
    Returns raw SurrealDB /sql payloads (list of statement dicts)."""

    def __init__(self, seg_rows=None, video_rows=None, fail=False):
        self.seg_rows = seg_rows or []
        self.video_rows = video_rows or []
        self.fail = fail
        self.queries = []

    def __call__(self, q):
        self.queries.append(q)
        if self.fail:
            return None
        if 'FROM segment' in q:
            return [{'status': 'OK', 'result': self.seg_rows}]
        return [{'status': 'OK', 'result': self.video_rows}]


def seg_row(fix_seg, dist):
    return {
        'video_youtube_id': fix_seg['video_youtube_id'],
        'chunk_index': fix_seg['chunk_index'],
        'start_time': fix_seg['start_time'],
        'end_time': fix_seg['end_time'],
        'text': fix_seg['text'],
        'domain': fix_seg['domain'],
        'dist': dist,
    }


def real_rows():
    """KNN rows with REAL distances between the fixture query and segments."""
    rows = [seg_row(s, real_cosine_distance(QUERY_VEC, s['embedding']))
            for s in FIXTURE['segments']]
    return sorted(rows, key=lambda r: r['dist'])


def test_query_uses_query_kind_embedding(srch, monkeypatch):
    calls = {}

    def spy(text, kind='document'):
        calls['kind'] = kind
        return QUERY_VEC

    monkeypatch.setattr(srch, 'get_embedding', spy)
    fake = FakeSurreal()
    monkeypatch.setattr(srch, 'surreal_query', fake)
    srch.semantic_search('bible wealth')
    assert calls['kind'] == 'query'


def test_knn_query_shape(srch, monkeypatch):
    fake = FakeSurreal()
    monkeypatch.setattr(srch, 'surreal_query', fake)
    srch.semantic_search('bible wealth', limit=10)
    q = fake.queries[0]
    # default min_score=0.4 forces over-fetch: k = 10*4 = 40, ef = max(100, 40)
    assert '<|40,100|>' in q
    assert 'vector::distance::knn() AS dist' in q
    assert 'ORDER BY dist ASC' in q
    assert 'LIMIT 40' in q
    assert 'FROM segment' in q


def test_domain_filter_escaped_and_anded_before_knn(srch, monkeypatch):
    fake = FakeSurreal()
    monkeypatch.setattr(srch, 'surreal_query', fake)
    srch.semantic_search('q text long enough', domain="ai'-tech")
    q = fake.queries[0]
    assert "domain = 'ai\\'-tech' AND" in q
    assert q.index('domain =') < q.index('<|')


def test_results_scored_titled_and_ordered(srch, monkeypatch):
    rows = real_rows()
    title_of = {s['video_youtube_id']: f"title-for-{s['video_youtube_id']}"
                for s in FIXTURE['segments']}
    vids = [{'youtube_id': vid, 'title': t} for vid, t in title_of.items()]
    fake = FakeSurreal(seg_rows=rows, video_rows=vids)
    monkeypatch.setattr(srch, 'surreal_query', fake)

    out = srch.semantic_search('bible wealth', min_score=0.0)

    assert out['results'], 'expected real fixture rows to come back'
    for r, row in zip(out['results'], rows):
        assert r['score'] == round(1.0 - row['dist'], 4)
        assert r['text'] == row['text']
        # each result must carry the title of ITS OWN video, not just any title
        assert r['video_title'] == title_of[r['video_youtube_id']]
    scores = [r['score'] for r in out['results']]
    assert scores == sorted(scores, reverse=True)
    assert out['model']  # the configured model alias travels with results


def test_min_score_drops_weak_rows(srch, monkeypatch):
    rows = real_rows()
    fake = FakeSurreal(seg_rows=rows)
    monkeypatch.setattr(srch, 'surreal_query', fake)

    # Real fixture geometry: religion segments score well against the bible
    # query, ai-automation segments poorly. A threshold between the two
    # keeps only the strong ones.
    strong = srch.semantic_search('bible wealth', min_score=0.0)['results']
    all_scores = [r['score'] for r in strong]
    threshold = sorted(all_scores)[len(all_scores) // 2]

    filtered = srch.semantic_search('bible wealth', min_score=threshold)['results']
    assert filtered
    assert all(r['score'] >= threshold for r in filtered)
    assert len(filtered) < len(strong)


def test_limit_truncates(srch, monkeypatch):
    fake = FakeSurreal(seg_rows=real_rows())
    monkeypatch.setattr(srch, 'surreal_query', fake)
    out = srch.semantic_search('bible wealth', limit=2, min_score=0.0)
    assert len(out['results']) == 2


def test_no_matches_is_empty_not_error(srch, monkeypatch):
    fake = FakeSurreal(seg_rows=[])
    monkeypatch.setattr(srch, 'surreal_query', fake)
    out = srch.semantic_search('anything at all', domain='no-such-domain')
    assert out['results'] == []


def test_gateway_down_raises_embedding_unavailable(srch, monkeypatch):
    monkeypatch.setattr(srch, 'get_embedding', lambda text, kind='query': None)
    with pytest.raises(srch.EmbeddingUnavailable):
        srch.semantic_search('bible wealth')


def test_surreal_failure_raises_runtime_error(srch, monkeypatch):
    fake = FakeSurreal(fail=True)
    monkeypatch.setattr(srch, 'surreal_query', fake)
    with pytest.raises(RuntimeError):
        srch.semantic_search('bible wealth')


def test_surreal_statement_error_raises(srch, monkeypatch):
    def err(q):
        return [{'status': 'ERR', 'result': 'Index not found'}]

    monkeypatch.setattr(srch, 'surreal_query', err)
    with pytest.raises(RuntimeError, match='Index not found'):
        srch.semantic_search('bible wealth')
