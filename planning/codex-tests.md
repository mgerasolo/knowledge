Reading additional input from stdin...
OpenAI Codex v0.147.0
--------
workdir: /home/mgerasolo/Dev/KnowledgeStack-wt-semantic-search
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: none
reasoning summaries: none
session id: 019ffe8b-406d-7c30-99cb-6dfe374ed6fe
--------
user
Independently verify this repo's python test battery. Run: .venv-test/bin/python -m pytest tests/python/ -v 2>&1 | tail -60. Then inspect tests/python/*.py for gaming: pytest.mark.skip/xfail, assertions that can never fail, tests asserting on mocks so tightly they test nothing, fixtures that fake what they claim to verify. The fixture tests/python/fixtures/real_segments_2026-08-14.json is claimed to be REAL corpus data — sanity-check its structure (6 segments with 768-dim embeddings + 2 queries). End with exactly one line: VERDICT: PASS or VERDICT: FAIL — followed by reasons.
hook: SessionStart
hook: SessionStart Completed
codex
I’ll run the exact test command, then audit the Python tests and validate the claimed real-data fixture’s counts and embedding dimensions.
exec
/usr/bin/zsh -lc '.venv-test/bin/python -m pytest tests/python/ -v 2>&1 | tail -60' in /home/mgerasolo/Dev/KnowledgeStack-wt-semantic-search
 succeeded in 317ms:
tests/python/test_metrics.py::TestDrilldown::test_grouping_by_channel_uses_channel_names PASSED [ 56%]
tests/python/test_metrics.py::TestDrilldown::test_channel_drilldown_filters_to_one_category PASSED [ 57%]
tests/python/test_metrics.py::TestDrilldown::test_subcategory_drilldown_splits_ai_apart PASSED [ 58%]
tests/python/test_metrics.py::TestFreshness::test_recent_video_reads_fresh PASSED [ 59%]
tests/python/test_metrics.py::TestFreshness::test_old_video_reads_stalled PASSED [ 59%]
tests/python/test_metrics.py::TestFreshness::test_middle_ground_reads_slowing PASSED [ 60%]
tests/python/test_metrics.py::TestFreshness::test_a_dead_category_is_visible_even_when_overall_is_fresh PASSED [ 61%]
tests/python/test_metrics.py::TestFreshness::test_category_with_no_videos_reads_never_not_stalled PASSED [ 62%]
tests/python/test_metrics.py::TestFreshness::test_every_top_level_category_is_reported PASSED [ 62%]
tests/python/test_metrics.py::TestFreshness::test_worst_channels_sort_first PASSED [ 63%]
tests/python/test_metrics.py::TestChannelRhythm::test_low_frequency_channel_is_not_red_inside_its_own_rhythm PASSED [ 64%]
tests/python/test_metrics.py::TestChannelRhythm::test_channel_with_unknown_rhythm_reads_quiet_not_stalled PASSED [ 65%]
tests/python/test_metrics.py::TestChannelRhythm::test_rebuild_day_does_not_poison_the_rhythm_calculation PASSED [ 65%]
tests/python/test_metrics.py::TestChannelRhythm::test_batch_ingested_channel_reports_no_rhythm PASSED [ 66%]
tests/python/test_metrics.py::TestChannelRhythm::test_a_genuine_cadence_is_still_reported PASSED [ 67%]
tests/python/test_metrics.py::TestChannelRhythm::test_a_quiet_channel_still_sorts_above_a_healthy_one PASSED [ 68%]
tests/python/test_metrics.py::TestUnadoptedChannels::test_channels_without_a_record_are_counted_and_marked PASSED [ 68%]
tests/python/test_metrics.py::TestUnadoptedChannels::test_unadopted_channel_still_appears_in_counts PASSED [ 69%]
tests/python/test_metrics.py::TestVideosWithNoChannel::test_blank_handle_does_not_become_a_channel_row PASSED [ 70%]
tests/python/test_metrics.py::TestVideosWithNoChannel::test_unattributed_videos_are_counted_not_hidden PASSED [ 71%]
tests/python/test_metrics.py::TestVideosWithNoChannel::test_unattributed_videos_still_count_toward_their_category PASSED [ 71%]
tests/python/test_metrics.py::TestVideosWithNoChannel::test_channel_count_matches_the_library_count PASSED [ 72%]
tests/python/test_metrics.py::TestTaxonomyDriftIsSurfaced::test_unrecognised_domain_is_reported_in_notes PASSED [ 73%]
tests/python/test_metrics.py::TestTaxonomyDriftIsSurfaced::test_unrecognised_domain_still_gets_counted_under_other PASSED [ 74%]
tests/python/test_metrics.py::TestTimestampParsing::test_nanosecond_precision_is_accepted PASSED [ 75%]
tests/python/test_metrics.py::TestTimestampParsing::test_plain_iso_is_accepted PASSED [ 75%]
tests/python/test_metrics.py::TestTimestampParsing::test_garbage_returns_none_rather_than_raising PASSED [ 76%]
tests/python/test_metrics.py::TestTimestampParsing::test_naive_timestamps_are_treated_as_utc PASSED [ 77%]
tests/python/test_metrics.py::TestDayBucketing::test_days_are_bucketed_in_the_display_timezone PASSED [ 78%]
tests/python/test_metrics.py::TestDayBucketing::test_a_video_lands_on_exactly_one_day PASSED [ 78%]
tests/python/test_search_route_admin.py::test_missing_q_is_400 PASSED    [ 79%]
tests/python/test_search_route_admin.py::test_short_q_is_400 PASSED      [ 80%]
tests/python/test_search_route_admin.py::test_success_passthrough PASSED [ 81%]
tests/python/test_search_route_admin.py::test_limit_clamped_to_50 PASSED [ 81%]
tests/python/test_search_route_admin.py::test_embedding_service_down_is_retryable_503 PASSED [ 82%]
tests/python/test_search_route_admin.py::test_embedding_service_503_passthrough PASSED [ 83%]
tests/python/test_search_route_admin.py::test_embedding_service_400_passthrough PASSED [ 84%]
tests/python/test_search_route_admin.py::test_non_json_reply_is_503 PASSED [ 84%]
tests/python/test_search_route_admin.py::test_bad_numeric_params_are_400 PASSED [ 85%]
tests/python/test_search_route_embedding.py::test_missing_query_is_400 PASSED [ 86%]
tests/python/test_search_route_embedding.py::test_short_query_is_400 PASSED [ 87%]
tests/python/test_search_route_embedding.py::test_no_body_is_400 PASSED  [ 87%]
tests/python/test_search_route_embedding.py::test_gateway_down_is_retryable_503 PASSED [ 88%]
tests/python/test_search_route_embedding.py::test_surrealdb_failure_is_retryable_503 PASSED [ 89%]
tests/python/test_search_route_embedding.py::test_success_envelope PASSED [ 90%]
tests/python/test_search_route_embedding.py::test_empty_results_is_200 PASSED [ 90%]
tests/python/test_search_route_embedding.py::test_params_forwarded_and_limit_clamped PASSED [ 91%]
tests/python/test_search_route_embedding.py::test_bad_limit_type_is_400 PASSED [ 92%]
tests/python/test_semantic_search.py::test_query_uses_query_kind_embedding PASSED [ 93%]
tests/python/test_semantic_search.py::test_knn_query_shape PASSED        [ 93%]
tests/python/test_semantic_search.py::test_domain_filter_escaped_and_anded_before_knn PASSED [ 94%]
tests/python/test_semantic_search.py::test_results_scored_titled_and_ordered PASSED [ 95%]
tests/python/test_semantic_search.py::test_min_score_drops_weak_rows PASSED [ 96%]
tests/python/test_semantic_search.py::test_limit_truncates PASSED        [ 96%]
tests/python/test_semantic_search.py::test_no_matches_is_empty_not_error PASSED [ 97%]
tests/python/test_semantic_search.py::test_gateway_down_raises_embedding_unavailable PASSED [ 98%]
tests/python/test_semantic_search.py::test_surreal_failure_raises_runtime_error PASSED [ 99%]
tests/python/test_semantic_search.py::test_surreal_statement_error_raises PASSED [100%]

============================= 132 passed in 0.25s ==============================

codex
The battery is green: 132 passed in 0.25s. I’m now checking whether that result is meaningful—first for skip/xfail and suspicious assertion patterns, then for fixture provenance/structure and whether tests substitute away the behavior they claim to cover.
exec
/usr/bin/zsh -lc "rg --files tests/python | sort && rg -n \"pytest\\.mark\\.(skip|skipif|xfail)|pytest\\.skip|\\b(skip|xfail)\\b|assert\\s+(True|False|None|[0-9]+\\s*==\\s*[0-9]+)|unittest\\.mock|\\bMock\\b|MagicMock|monkeypatch|patch\\(\" tests/python --glob '*.py'" in /home/mgerasolo/Dev/KnowledgeStack-wt-semantic-search
 succeeded in 0ms:
tests/python/embedding_loader.py
tests/python/fixtures/real_segments_2026-08-14.json
tests/python/test_backfill.py
tests/python/test_categories.py
tests/python/test_embedder.py
tests/python/test_ingest_embeds.py
tests/python/test_metrics.py
tests/python/test_search_route_admin.py
tests/python/test_search_route_embedding.py
tests/python/test_semantic_search.py
tests/python/test_ingest_embeds.py:22:def ts(monkeypatch):
tests/python/test_ingest_embeds.py:30:    monkeypatch.setattr(fetcher.requests, 'post', fake_post)
tests/python/test_ingest_embeds.py:44:def test_index_video_embeds_when_enabled(ts, monkeypatch):
tests/python/test_ingest_embeds.py:46:    monkeypatch.setattr(fetcher.Config, 'EMBED_ON_INGEST', True)
tests/python/test_ingest_embeds.py:52:def test_index_video_skips_when_disabled(ts, monkeypatch):
tests/python/test_ingest_embeds.py:54:    monkeypatch.setattr(fetcher.Config, 'EMBED_ON_INGEST', False)
tests/python/test_embedder.py:21:def emb(monkeypatch):
tests/python/test_embedder.py:23:    monkeypatch.setattr(emb.Config, 'LITELLM_API_KEY', 'test-key')
tests/python/test_embedder.py:24:    monkeypatch.setattr(emb.Config, 'EMBEDDING_DOC_PREFIX', 'search_document: ')
tests/python/test_embedder.py:25:    monkeypatch.setattr(emb.Config, 'EMBEDDING_QUERY_PREFIX', 'search_query: ')
tests/python/test_embedder.py:57:def test_document_prefix_applied(emb, monkeypatch):
tests/python/test_embedder.py:59:    monkeypatch.setattr(emb, 'requests', fake)
tests/python/test_embedder.py:64:def test_query_prefix_applied(emb, monkeypatch):
tests/python/test_embedder.py:66:    monkeypatch.setattr(emb, 'requests', fake)
tests/python/test_embedder.py:71:def test_default_kind_is_document(emb, monkeypatch):
tests/python/test_embedder.py:73:    monkeypatch.setattr(emb, 'requests', fake)
tests/python/test_embedder.py:78:def test_truncation_happens_before_prefix(emb, monkeypatch):
tests/python/test_embedder.py:81:    monkeypatch.setattr(emb, 'requests', fake)
tests/python/test_embedder.py:88:def test_empty_prefix_sends_raw_text(emb, monkeypatch):
tests/python/test_embedder.py:89:    monkeypatch.setattr(emb.Config, 'EMBEDDING_DOC_PREFIX', '')
tests/python/test_embedder.py:91:    monkeypatch.setattr(emb, 'requests', fake)
tests/python/test_embedder.py:96:def test_missing_key_returns_none_without_http(emb, monkeypatch):
tests/python/test_embedder.py:97:    monkeypatch.setattr(emb.Config, 'LITELLM_API_KEY', '')
tests/python/test_embedder.py:99:    monkeypatch.setattr(emb, 'requests', fake)
tests/python/test_embedder.py:104:def test_batch_splits_at_64_and_preserves_order(emb, monkeypatch):
tests/python/test_embedder.py:106:    monkeypatch.setattr(emb, 'requests', fake)
tests/python/test_embedder.py:118:def test_batch_missing_key_returns_all_none(emb, monkeypatch):
tests/python/test_embedder.py:119:    monkeypatch.setattr(emb.Config, 'LITELLM_API_KEY', '')
tests/python/test_embedder.py:121:    monkeypatch.setattr(emb, 'requests', fake)
tests/python/test_embedder.py:126:def test_batch_gateway_failure_returns_none_per_text(emb, monkeypatch):
tests/python/test_embedder.py:128:    monkeypatch.setattr(emb, 'requests', fake)
tests/python/test_embedder.py:149:def test_embed_video_reports_embedding_failures_honestly(emb, monkeypatch):
tests/python/test_embedder.py:152:    monkeypatch.setattr(emb, 'surreal_write', lambda q: (True, None))
tests/python/test_embedder.py:153:    monkeypatch.setattr(emb, 'get_embedding', lambda text, kind='document': None)
tests/python/test_embedder.py:163:def test_embed_video_success_counts_no_failures(emb, monkeypatch):
tests/python/test_embedder.py:164:    monkeypatch.setattr(emb, 'surreal_write', lambda q: (True, None))
tests/python/test_embedder.py:165:    monkeypatch.setattr(emb, 'get_embedding',
tests/python/test_embedder.py:175:def test_embed_video_skip_embeddings_reports_not_generated(emb, monkeypatch):
tests/python/test_embedder.py:176:    monkeypatch.setattr(emb, 'surreal_write', lambda q: (True, None))
tests/python/test_search_route_embedding.py:13:def stack(monkeypatch):
tests/python/test_search_route_embedding.py:39:def test_gateway_down_is_retryable_503(stack, monkeypatch):
tests/python/test_search_route_embedding.py:45:    monkeypatch.setattr(appm, 'semantic_search', boom)
tests/python/test_search_route_embedding.py:53:def test_surrealdb_failure_is_retryable_503(stack, monkeypatch):
tests/python/test_search_route_embedding.py:59:    monkeypatch.setattr(appm, 'semantic_search', boom)
tests/python/test_search_route_embedding.py:65:def test_success_envelope(stack, monkeypatch):
tests/python/test_search_route_embedding.py:72:    monkeypatch.setattr(
tests/python/test_search_route_embedding.py:87:def test_empty_results_is_200(stack, monkeypatch):
tests/python/test_search_route_embedding.py:89:    monkeypatch.setattr(
tests/python/test_search_route_embedding.py:100:def test_params_forwarded_and_limit_clamped(stack, monkeypatch):
tests/python/test_search_route_embedding.py:109:    monkeypatch.setattr(appm, 'semantic_search', spy)
tests/python/embedding_loader.py:39:    Modules keep references to THEIR OWN Config object — tests monkeypatch
tests/python/test_search_route_admin.py:49:def test_success_passthrough(client, monkeypatch):
tests/python/test_search_route_admin.py:62:    monkeypatch.setattr(videos.requests, 'post', fake_post)
tests/python/test_search_route_admin.py:75:def test_limit_clamped_to_50(client, monkeypatch):
tests/python/test_search_route_admin.py:83:    monkeypatch.setattr(videos.requests, 'post', fake_post)
tests/python/test_search_route_admin.py:88:def test_embedding_service_down_is_retryable_503(client, monkeypatch):
tests/python/test_search_route_admin.py:92:    monkeypatch.setattr(videos.requests, 'post', fake_post)
tests/python/test_search_route_admin.py:100:def test_embedding_service_503_passthrough(client, monkeypatch):
tests/python/test_search_route_admin.py:105:    monkeypatch.setattr(videos.requests, 'post', fake_post)
tests/python/test_search_route_admin.py:111:def test_embedding_service_400_passthrough(client, monkeypatch):
tests/python/test_search_route_admin.py:115:    monkeypatch.setattr(videos.requests, 'post', fake_post)
tests/python/test_search_route_admin.py:120:def test_non_json_reply_is_503(client, monkeypatch):
tests/python/test_search_route_admin.py:124:    monkeypatch.setattr(videos.requests, 'post', fake_post)
tests/python/test_semantic_search.py:27:def srch(monkeypatch):
tests/python/test_semantic_search.py:29:    monkeypatch.setattr(srch, 'get_embedding',
tests/python/test_semantic_search.py:72:def test_query_uses_query_kind_embedding(srch, monkeypatch):
tests/python/test_semantic_search.py:79:    monkeypatch.setattr(srch, 'get_embedding', spy)
tests/python/test_semantic_search.py:81:    monkeypatch.setattr(srch, 'surreal_query', fake)
tests/python/test_semantic_search.py:86:def test_knn_query_shape(srch, monkeypatch):
tests/python/test_semantic_search.py:88:    monkeypatch.setattr(srch, 'surreal_query', fake)
tests/python/test_semantic_search.py:99:def test_domain_filter_escaped_and_anded_before_knn(srch, monkeypatch):
tests/python/test_semantic_search.py:101:    monkeypatch.setattr(srch, 'surreal_query', fake)
tests/python/test_semantic_search.py:108:def test_results_scored_titled_and_ordered(srch, monkeypatch):
tests/python/test_semantic_search.py:113:    monkeypatch.setattr(srch, 'surreal_query', fake)
tests/python/test_semantic_search.py:127:def test_min_score_drops_weak_rows(srch, monkeypatch):
tests/python/test_semantic_search.py:130:    monkeypatch.setattr(srch, 'surreal_query', fake)
tests/python/test_semantic_search.py:145:def test_limit_truncates(srch, monkeypatch):
tests/python/test_semantic_search.py:147:    monkeypatch.setattr(srch, 'surreal_query', fake)
tests/python/test_semantic_search.py:152:def test_no_matches_is_empty_not_error(srch, monkeypatch):
tests/python/test_semantic_search.py:154:    monkeypatch.setattr(srch, 'surreal_query', fake)
tests/python/test_semantic_search.py:159:def test_gateway_down_raises_embedding_unavailable(srch, monkeypatch):
tests/python/test_semantic_search.py:160:    monkeypatch.setattr(srch, 'get_embedding', lambda text, kind='query': None)
tests/python/test_semantic_search.py:165:def test_surreal_failure_raises_runtime_error(srch, monkeypatch):
tests/python/test_semantic_search.py:167:    monkeypatch.setattr(srch, 'surreal_query', fake)
tests/python/test_semantic_search.py:172:def test_surreal_statement_error_raises(srch, monkeypatch):
tests/python/test_semantic_search.py:176:    monkeypatch.setattr(srch, 'surreal_query', err)
tests/python/test_metrics.py:35:def sources(monkeypatch):
tests/python/test_metrics.py:56:    monkeypatch.setattr(metrics, '_corpus_cache', _Fake('corpus'))
tests/python/test_metrics.py:57:    monkeypatch.setattr(metrics, '_files_cache', _Fake('files'))
tests/python/test_metrics.py:58:    monkeypatch.setattr(metrics, '_channels_cache', _Fake('channels'))
tests/python/test_metrics.py:110:            pytest.skip("rebuild day is in the future for this clock")
tests/python/test_metrics.py:122:            pytest.skip("rebuild day is in the future for this clock")
tests/python/test_metrics.py:331:            pytest.skip("rebuild day is in the future for this clock")
tests/python/test_backfill.py:76:def test_backoff_ladder_then_gives_up(monkeypatch):
tests/python/test_backfill.py:78:    monkeypatch.setattr(bf.time, 'sleep', lambda s: sleeps.append(s))
tests/python/test_backfill.py:91:def test_backoff_stops_early_on_success(monkeypatch):
tests/python/test_backfill.py:93:    monkeypatch.setattr(bf.time, 'sleep', lambda s: sleeps.append(s))

exec
/usr/bin/zsh -lc "wc -l tests/python/*.py && sed -n '1,240p' tests/python/test_backfill.py && sed -n '1,240p' tests/python/test_categories.py && sed -n '1,260p' tests/python/test_embedder.py && sed -n '1,220p' tests/python/test_ingest_embeds.py" in /home/mgerasolo/Dev/KnowledgeStack-wt-semantic-search
 succeeded in 0ms:
   86 tests/python/embedding_loader.py
  110 tests/python/test_backfill.py
  178 tests/python/test_categories.py
  182 tests/python/test_embedder.py
   56 tests/python/test_ingest_embeds.py
  476 tests/python/test_metrics.py
  134 tests/python/test_search_route_admin.py
  123 tests/python/test_search_route_embedding.py
  178 tests/python/test_semantic_search.py
 1523 total
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


def test_remaining_count_parser():
    payload = [{'status': 'OK', 'result': [{'count': 42}]}]
    assert bf.count_from_payload(payload) == 42
    assert bf.count_from_payload([{'status': 'OK', 'result': []}]) == 0
    assert bf.count_from_payload(None) is None
    assert bf.count_from_payload([{'status': 'ERR', 'result': 'boom'}]) is None
"""Tests for the canonical category taxonomy.

The taxonomy exists because the two stores disagree about category names and the
corpus vocabulary is itself split — AI arrives as four different strings, faith as
two. A per-category chart built on raw values is wrong, so every raw value passes
through here first.

These tests are deliberately I/O-free: the taxonomy is the part most likely to
change as channels get re-tagged, and it must be correctable without a database.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src' / 'admin'))

from api.categories import (  # noqa: E402
    OTHER,
    TOP_LEVEL_ORDER,
    canonical_category,
    resolve_category,
    split_known_unknown,
    subcategories_of,
)


class TestTopLevelMapping:
    """Every raw value seen in either store maps to the right top-level bucket."""

    @pytest.mark.parametrize("raw", ["ai", "ai-coding", "ai-automation", "ai-tech"])
    def test_all_four_ai_variants_collapse_to_ai(self, raw):
        # 689 videos are split across these four strings. Charting them
        # separately by default was explicitly rejected.
        assert canonical_category(raw) == "AI"

    @pytest.mark.parametrize("raw", ["faith", "religion"])
    def test_faith_and_religion_merge(self, raw):
        assert canonical_category(raw) == "Faith"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("political", "Politics"),
            ("mindset", "Mindset"),
            ("business", "Business"),
            ("health", "Health"),
            ("finance", "Finance"),
        ],
    )
    def test_single_value_categories(self, raw, expected):
        assert canonical_category(raw) == expected

    def test_general_is_other(self):
        assert canonical_category("general") == OTHER


class TestBusinessAndFinanceAreDistinct:
    """Matt: 'Finance is about investing in money. Business is about running a
    business, like Alex Hormozi's.' Collapsing them would erase that distinction."""

    def test_business_does_not_become_finance(self):
        assert canonical_category("business") == "Business"
        assert canonical_category("business") != "Finance"

    def test_finance_exists_as_a_category_even_though_nothing_is_tagged_it(self):
        # Rendering it at zero is the point: a hidden empty category is
        # indistinguishable from a category that stopped producing.
        assert "Finance" in TOP_LEVEL_ORDER

    def test_finance_and_business_are_both_present(self):
        assert "Business" in TOP_LEVEL_ORDER
        assert TOP_LEVEL_ORDER.index("Business") != TOP_LEVEL_ORDER.index("Finance")


class TestUnknownValues:
    """Taxonomy drift must be visible, never silently absorbed."""

    def test_unknown_value_falls_to_other(self):
        assert canonical_category("crypto-nonsense") == OTHER

    def test_none_falls_to_other(self):
        assert canonical_category(None) == OTHER

    def test_empty_string_falls_to_other(self):
        assert canonical_category("") == OTHER

    def test_unknown_values_are_reported_not_swallowed(self):
        known, unknown = split_known_unknown(
            ["ai", "political", "brand-new-thing", "another-new-one"]
        )
        assert unknown == {"another-new-one", "brand-new-thing"}
        assert "ai" in known

    def test_general_is_not_reported_as_unknown(self):
        # 'general' maps to Other deliberately; it is not drift.
        _, unknown = split_known_unknown(["general"])
        assert unknown == set()


class TestCaseAndWhitespaceTolerance:
    """Domain values are hand-entered upstream; a stray capital must not create
    a phantom category."""

    @pytest.mark.parametrize("raw", ["AI", "Ai", " ai ", "AI-CODING"])
    def test_case_and_padding_ignored(self, raw):
        assert canonical_category(raw) == "AI"


class TestResolutionOrder:
    """A video's category comes from the channel record first, because that is the
    human-curated answer. 22 channels have videos but no record, so the video's own
    domain is the fallback."""

    def test_channel_domain_wins_when_present(self):
        result = resolve_category(channel_domain="business", video_domain="ai")
        assert result.category == "Business"
        assert result.by_fallback is False

    def test_falls_back_to_video_domain_when_channel_unknown(self):
        result = resolve_category(channel_domain=None, video_domain="political")
        assert result.category == "Politics"
        assert result.by_fallback is True

    def test_other_when_neither_is_known(self):
        result = resolve_category(channel_domain=None, video_domain=None)
        assert result.category == OTHER
        assert result.by_fallback is True

    def test_blank_channel_domain_is_treated_as_absent(self):
        # An empty string in the column must not beat a real video domain.
        result = resolve_category(channel_domain="   ", video_domain="health")
        assert result.category == "Health"
        assert result.by_fallback is True


class TestSubcategoryDrilldown:
    """Drill-down is display-only. The stored value is never rewritten, so
    re-tagging upstream later needs no migration."""

    def test_ai_exposes_its_four_variants(self):
        assert subcategories_of("AI") == [
            "ai",
            "ai-automation",
            "ai-coding",
            "ai-tech",
        ]

    def test_faith_exposes_both_spellings(self):
        assert subcategories_of("Faith") == ["faith", "religion"]

    def test_single_value_category_returns_its_one_value(self):
        assert subcategories_of("Politics") == ["political"]

    def test_finance_has_no_subcategories_yet(self):
        assert subcategories_of("Finance") == ["finance"]

    def test_unknown_top_level_returns_empty(self):
        assert subcategories_of("NotACategory") == []


class TestOrderingIsStable:
    """Chart colours are assigned by position. If the order shifts between
    requests, a category silently changes colour and the chart lies about
    continuity."""

    def test_order_is_deterministic(self):
        assert TOP_LEVEL_ORDER == list(TOP_LEVEL_ORDER)
        assert len(TOP_LEVEL_ORDER) == len(set(TOP_LEVEL_ORDER))

    def test_other_sorts_last(self):
        assert TOP_LEVEL_ORDER[-1] == OTHER

    def test_every_top_level_except_other_has_at_least_one_raw_value(self):
        for name in TOP_LEVEL_ORDER:
            if name == OTHER:
                continue
            assert subcategories_of(name), f"{name} maps from nothing"
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

exec
/usr/bin/zsh -lc "sed -n '1,520p' tests/python/test_metrics.py && sed -n '1,180p' tests/python/test_search_route_admin.py && sed -n '1,170p' tests/python/test_search_route_embedding.py && sed -n '1,230p' tests/python/test_semantic_search.py" in /home/mgerasolo/Dev/KnowledgeStack-wt-semantic-search
 succeeded in 0ms:
"""Tests for the daily-counts and freshness layer.

The failure this project actually suffered was silent: for two weeks the corpus was
empty while every check reported healthy. So these tests lean hard on the failure
cases — an unreadable source must never render as zeros, and a real zero must never
render as a failure.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src' / 'admin'))

from api import metrics  # noqa: E402
from api.metrics import SourceResult  # noqa: E402


def at(days_ago=0, hours_ago=0):
    """A timestamp relative to now, in UTC."""
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)


def video(handle="ailabs-393", domain="ai", days_ago=0, hours_ago=0, name=None):
    return {
        'at': at(days_ago, hours_ago),
        'domain': domain,
        'handle': handle,
        'name': name or handle,
    }


@pytest.fixture
def sources(monkeypatch):
    """Swap the three sources for in-memory fakes.

    Returns a setter so each test states exactly what the world looks like.
    """
    state = {
        'corpus': SourceResult(rows=[]),
        'files': SourceResult(rows=[]),
        'channels': SourceResult(rows=[{}]),
    }

    class _Fake:
        def __init__(self, key):
            self.key = key

        def get(self):
            return state[self.key]

        def invalidate(self):
            pass

    monkeypatch.setattr(metrics, '_corpus_cache', _Fake('corpus'))
    monkeypatch.setattr(metrics, '_files_cache', _Fake('files'))
    monkeypatch.setattr(metrics, '_channels_cache', _Fake('channels'))
    return state


class TestUnreadableSourcesNeverLookLikeZero:
    """The single most important behaviour on this page."""

    def test_unreadable_library_reports_unknown_not_fresh(self, sources):
        sources['corpus'] = SourceResult(problem="search library unreadable (refused)")

        result = metrics.freshness()

        assert result['readable'] is False
        assert result['overall']['state'] == 'unknown'
        assert 'unreadable' in result['problem']

    def test_unreadable_library_does_not_claim_zero_ingested_today(self, sources):
        sources['corpus'] = SourceResult(problem="down")

        result = metrics.freshness()

        # Reporting "0 ingested today" here would be a lie — we do not know.
        assert 'ingested_today' not in result or result.get('ingested_today') is None

    def test_empty_but_readable_library_is_a_real_zero(self, sources):
        sources['corpus'] = SourceResult(rows=[])

        result = metrics.freshness()

        assert result['readable'] is True
        assert result['problem'] is None
        assert result['ingested_today'] == 0
        assert result['overall']['state'] == 'never'

    def test_daily_series_surfaces_the_problem_text(self, sources):
        sources['corpus'] = SourceResult(problem="search library unreadable (timeout)")
        sources['files'] = SourceResult(problem="transcript archive not mounted")

        series = metrics.daily_series(days=7)

        assert len(series.problems) == 2
        assert any('library' in p for p in series.problems)
        assert any('transcript' in p for p in series.problems)


class TestTheRebuildDayIsNotIngestion:
    """3,057 records were re-filed on 2026-08-05. Charting that as a day's work
    would show a fake spike ~60x the real rate and wreck the Y-axis forever."""

    def test_rebuild_day_is_flagged_in_the_output(self, sources):
        days_since_rebuild = (metrics._today() - metrics.REBUILD_DAY).days
        if days_since_rebuild < 0:
            pytest.skip("rebuild day is in the future for this clock")

        series = metrics.daily_series(days=days_since_rebuild + 2)
        rebuild_rows = [d for d in series.days if d.get('rebuild')]

        assert len(rebuild_rows) == 1
        assert rebuild_rows[0]['date'] == metrics.REBUILD_DAY.isoformat()
        assert 'rebuilt' in rebuild_rows[0]['note']

    def test_videos_stamped_on_the_rebuild_day_are_excluded_from_counts(self, sources):
        days_since_rebuild = (metrics._today() - metrics.REBUILD_DAY).days
        if days_since_rebuild < 0:
            pytest.skip("rebuild day is in the future for this clock")
        sources['corpus'] = SourceResult(rows=[
            video(days_ago=days_since_rebuild) for _ in range(3057)
        ])

        series = metrics.daily_series(days=days_since_rebuild + 2)
        rebuild_row = next(d for d in series.days if d.get('rebuild'))

        assert rebuild_row['total'] == 0


class TestDailyCounts:
    def test_counts_group_by_top_level_category(self, sources):
        sources['corpus'] = SourceResult(rows=[
            video(domain='ai'), video(domain='ai-coding'), video(domain='ai-tech'),
            video(domain='political'),
        ])

        series = metrics.daily_series(days=2)
        today = series.days[-1]

        # All three AI spellings land on one bar.
        assert today['counts']['AI'] == 3
        assert today['counts']['Politics'] == 1

    def test_every_day_in_range_is_present_even_when_empty(self, sources):
        sources['corpus'] = SourceResult(rows=[video()])

        series = metrics.daily_series(days=10)

        # Ingestion is bursty. A missing day and a zero day look identical on a
        # chart, so zeros must be emitted rather than left out.
        assert len(series.days) == 10
        assert all('total' in day for day in series.days)

    def test_empty_days_are_zero_not_absent(self, sources):
        sources['corpus'] = SourceResult(rows=[video(days_ago=0)])

        series = metrics.daily_series(days=5)

        assert series.days[0]['total'] == 0
        assert series.days[-1]['total'] == 1

    def test_finance_series_is_present_even_though_it_is_empty(self, sources):
        sources['corpus'] = SourceResult(rows=[video(domain='business')])

        series = metrics.daily_series(days=3)

        # A hidden empty category cannot be told apart from one that stopped.
        assert 'Finance' in series.series_names
        assert series.totals['Finance'] == 0
        assert series.totals['Business'] == 1

    def test_business_and_finance_do_not_merge(self, sources):
        sources['corpus'] = SourceResult(rows=[
            video(domain='business'), video(domain='finance'),
        ])

        series = metrics.daily_series(days=3)

        assert series.totals['Business'] == 1
        assert series.totals['Finance'] == 1

    def test_channel_record_domain_beats_the_video_domain(self, sources):
        sources['channels'] = SourceResult(rows=[{
            'ailabs-393': {'name': 'AI Labs', 'domain': 'business', 'is_active': True},
        }])
        sources['corpus'] = SourceResult(rows=[video(handle='ailabs-393', domain='ai')])

        series = metrics.daily_series(days=2)

        assert series.totals['Business'] == 1
        assert series.totals['AI'] == 0

    def test_days_are_capped_to_something_sane(self, sources):
        assert len(metrics.daily_series(days=100000).days) <= 400
        assert len(metrics.daily_series(days=0).days) == 1


class TestDrilldown:
    def test_grouping_by_channel_uses_channel_names(self, sources):
        sources['channels'] = SourceResult(rows=[{
            'ailabs-393': {'name': 'AI Labs', 'domain': 'ai-tech', 'is_active': True},
        }])
        sources['corpus'] = SourceResult(rows=[
            video(handle='ailabs-393', domain='ai'),
            video(handle='gregisenberg', domain='ai'),
        ])

        series = metrics.daily_series(days=2, group='channel')

        assert 'AI Labs' in series.series_names
        assert 'gregisenberg' in series.series_names

    def test_channel_drilldown_filters_to_one_category(self, sources):
        sources['corpus'] = SourceResult(rows=[
            video(handle='ailabs-393', domain='ai'),
            video(handle='rubinreport', domain='political'),
        ])

        series = metrics.daily_series(days=2, group='channel', category='AI')

        assert 'ailabs-393' in series.series_names
        assert 'rubinreport' not in series.series_names

    def test_subcategory_drilldown_splits_ai_apart(self, sources):
        sources['corpus'] = SourceResult(rows=[
            video(domain='ai'), video(domain='ai-coding'), video(domain='ai-coding'),
        ])

        series = metrics.daily_series(days=2, group='subcategory', category='AI')

        assert series.totals['ai'] == 1
        assert series.totals['ai-coding'] == 2


class TestFreshness:
    def test_recent_video_reads_fresh(self, sources):
        sources['corpus'] = SourceResult(rows=[video(hours_ago=1)])

        assert metrics.freshness()['overall']['state'] == 'fresh'

    def test_old_video_reads_stalled(self, sources):
        sources['corpus'] = SourceResult(rows=[video(days_ago=30)])

        assert metrics.freshness()['overall']['state'] == 'stalled'

    def test_middle_ground_reads_slowing(self, sources):
        sources['corpus'] = SourceResult(rows=[video(hours_ago=metrics.FRESH_HOURS + 5)])

        assert metrics.freshness()['overall']['state'] == 'slowing'

    def test_a_dead_category_is_visible_even_when_overall_is_fresh(self, sources):
        """The exact blindness that let a two-week outage report healthy."""
        sources['corpus'] = SourceResult(rows=[
            video(domain='ai', hours_ago=1),
            video(domain='political', days_ago=40),
        ])

        result = metrics.freshness()
        states = {c['category']: c['state'] for c in result['categories']}

        assert result['overall']['state'] == 'fresh'
        assert states['AI'] == 'fresh'
        assert states['Politics'] == 'stalled'

    def test_category_with_no_videos_reads_never_not_stalled(self, sources):
        sources['corpus'] = SourceResult(rows=[video(domain='ai')])

        states = {c['category']: c['state'] for c in metrics.freshness()['categories']}

        # "Never delivered" is a setup problem, not an outage. Different fix.
        assert states['Finance'] == 'never'

    def test_every_top_level_category_is_reported(self, sources):
        sources['corpus'] = SourceResult(rows=[video()])

        categories = [c['category'] for c in metrics.freshness()['categories']]

        assert categories == list(metrics.TOP_LEVEL_ORDER)

    def test_worst_channels_sort_first(self, sources):
        sources['corpus'] = SourceResult(rows=[
            video(handle='fresh-one', hours_ago=1),
            video(handle='dead-one', days_ago=60),
        ])

        channels = metrics.freshness()['channels']

        assert channels[0]['handle'] == 'dead-one'


class TestChannelRhythm:
    """A monthly channel is not stalled at 8 days. Painting it red trains the
    reader to ignore the colour.

    Equally: where we cannot compute a channel's rhythm — which is common, because
    publish dates are epoch-zero corpus-wide and ingestion history only became
    trustworthy on 2026-08-07 — we must NOT assert that it is broken."""

    def test_low_frequency_channel_is_not_red_inside_its_own_rhythm(self, sources):
        # Posts roughly every 30 days; last one 40 days ago.
        rows = [video(handle='monthly', days_ago=40 + 30 * i) for i in range(6)]
        sources['corpus'] = SourceResult(rows=rows)

        channel = next(c for c in metrics.freshness()['channels']
                       if c['handle'] == 'monthly')

        assert channel['state'] != 'stalled'
        assert channel['typical_gap_hours'] is not None

    def test_channel_with_unknown_rhythm_reads_quiet_not_stalled(self, sources):
        """The honest verdict: 'nothing in 40 days, and we don't know if that's
        normal for this channel'. Calling it stalled would assert a problem we
        have no evidence for."""
        sources['corpus'] = SourceResult(rows=[video(handle='sparse', days_ago=40)])

        channel = next(c for c in metrics.freshness()['channels']
                       if c['handle'] == 'sparse')

        assert channel['state'] == 'quiet'
        assert channel['typical_gap_hours'] is None
        assert channel['hours_since'] > 24 * 39

    def test_rebuild_day_does_not_poison_the_rhythm_calculation(self, sources):
        """3,057 records share one timestamp on the rebuild day. Including them
        would report a rhythm of zero and then call every channel stalled."""
        days_since_rebuild = (metrics._today() - metrics.REBUILD_DAY).days
        if days_since_rebuild < 0:
            pytest.skip("rebuild day is in the future for this clock")
        rows = [video(handle='mixed', days_ago=days_since_rebuild) for _ in range(20)]
        rows += [video(handle='mixed', days_ago=i) for i in range(0, 2)]
        sources['corpus'] = SourceResult(rows=rows)

        channel = next(c for c in metrics.freshness()['channels']
                       if c['handle'] == 'mixed')

        assert channel['typical_gap_hours'] != 0

    def test_batch_ingested_channel_reports_no_rhythm(self, sources):
        """A backfill writes a whole catalogue in minutes. Those gaps describe the
        backfill's speed, not the channel's cadence — reporting 'typical gap: 0h'
        looks like a measurement while meaning nothing."""
        rows = [video(handle='backfilled', hours_ago=i * 0.02) for i in range(30)]
        sources['corpus'] = SourceResult(rows=rows)

        channel = next(c for c in metrics.freshness()['channels']
                       if c['handle'] == 'backfilled')

        assert channel['typical_gap_hours'] is None

    def test_a_genuine_cadence_is_still_reported(self, sources):
        rows = [video(handle='weekly', days_ago=7 * i) for i in range(8)]
        sources['corpus'] = SourceResult(rows=rows)

        channel = next(c for c in metrics.freshness()['channels']
                       if c['handle'] == 'weekly')

        assert channel['typical_gap_hours'] == pytest.approx(168, rel=0.1)

    def test_a_quiet_channel_still_sorts_above_a_healthy_one(self, sources):
        sources['corpus'] = SourceResult(rows=[
            video(handle='healthy', hours_ago=1),
            video(handle='quiet-one', days_ago=40),
        ])

        channels = metrics.freshness()['channels']

        assert channels[0]['handle'] == 'quiet-one'


class TestUnadoptedChannels:
    def test_channels_without_a_record_are_counted_and_marked(self, sources):
        sources['channels'] = SourceResult(rows=[{
            'known': {'name': 'Known', 'domain': 'ai', 'is_active': True},
        }])
        sources['corpus'] = SourceResult(rows=[
            video(handle='known'), video(handle='stranger'),
        ])

        result = metrics.freshness()
        by_handle = {c['handle']: c for c in result['channels']}

        assert result['unadopted_channels'] == 1
        assert by_handle['known']['adopted'] is True
        assert by_handle['stranger']['adopted'] is False

    def test_unadopted_channel_still_appears_in_counts(self, sources):
        """The channel list is an enrichment layer, never a filter."""
        sources['channels'] = SourceResult(rows=[{}])
        sources['corpus'] = SourceResult(rows=[video(handle='stranger', domain='ai')])

        assert metrics.daily_series(days=2).totals['AI'] == 1


class TestVideosWithNoChannel:
    """A video with no channel handle is not a channel. Grouping them under ''
    invented a row called 'Unknown' and made the channel count disagree with the
    library's — two pages answering the same question differently."""

    def test_blank_handle_does_not_become_a_channel_row(self, sources):
        sources['corpus'] = SourceResult(rows=[
            video(handle='real'), video(handle=''), video(handle='   '),
        ])

        result = metrics.freshness()

        assert [c['handle'] for c in result['channels']] == ['real']

    def test_unattributed_videos_are_counted_not_hidden(self, sources):
        sources['corpus'] = SourceResult(rows=[
            video(handle='real'), video(handle=''), video(handle=''),
        ])

        assert metrics.freshness()['unattributed_videos'] == 2

    def test_unattributed_videos_still_count_toward_their_category(self, sources):
        sources['corpus'] = SourceResult(rows=[video(handle='', domain='ai')])

        assert metrics.daily_series(days=2).totals['AI'] == 1

    def test_channel_count_matches_the_library_count(self, sources):
        sources['corpus'] = SourceResult(rows=[
            video(handle='one'), video(handle='two'), video(handle=''),
        ])

        assert len(metrics.freshness()['channels']) == metrics.library_totals()['channels']


class TestTaxonomyDriftIsSurfaced:
    def test_unrecognised_domain_is_reported_in_notes(self, sources):
        sources['corpus'] = SourceResult(rows=[video(domain='brand-new-topic')])

        series = metrics.daily_series(days=2)

        assert any('brand-new-topic' in note for note in series.notes)

    def test_unrecognised_domain_still_gets_counted_under_other(self, sources):
        sources['corpus'] = SourceResult(rows=[video(domain='brand-new-topic')])

        assert metrics.daily_series(days=2).totals['Other'] == 1


class TestTimestampParsing:
    def test_nanosecond_precision_is_accepted(self):
        parsed = metrics._parse_ts("2026-08-09T04:54:24.421981847Z")

        assert parsed is not None
        assert parsed.year == 2026 and parsed.month == 8 and parsed.day == 9

    def test_plain_iso_is_accepted(self):
        assert metrics._parse_ts("2026-08-09T04:54:24Z") is not None

    def test_garbage_returns_none_rather_than_raising(self):
        assert metrics._parse_ts("not a date") is None
        assert metrics._parse_ts(None) is None

    def test_naive_timestamps_are_treated_as_utc(self):
        parsed = metrics._parse_ts("2026-08-09T04:54:24")

        assert parsed.tzinfo is not None


class TestDayBucketing:
    def test_days_are_bucketed_in_the_display_timezone(self, sources):
        """Both hosts run Eastern. Bucketing in UTC would push an evening's
        ingestion onto tomorrow's bar."""
        assert 'America' in str(metrics.DISPLAY_TZ) or str(metrics.DISPLAY_TZ) == 'UTC'

    def test_a_video_lands_on_exactly_one_day(self, sources):
        sources['corpus'] = SourceResult(rows=[video(hours_ago=1)])

        series = metrics.daily_series(days=5)

        assert sum(day['total'] for day in series.days) == 1
"""GET /videos/api/semantic-search on the Admin API — the consumer surface.

Thin proxy to the embedding service. The contract consumers rely on:
400 = fix your request · 503 + retryable = try again later · 200 = answer
(empty results included). The embedding service being down must never
surface as a 200-with-error-inside or a bare 500.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src' / 'admin'))

from api import videos  # noqa: E402
from flask import Flask  # noqa: E402


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
    vids = [{'youtube_id': s['video_youtube_id'], 'title': f"title-{i}"}
            for i, s in enumerate(FIXTURE['segments'])]
    fake = FakeSurreal(seg_rows=rows, video_rows=vids)
    monkeypatch.setattr(srch, 'surreal_query', fake)

    out = srch.semantic_search('bible wealth', min_score=0.0)

    assert out['results'], 'expected real fixture rows to come back'
    for r, row in zip(out['results'], rows):
        assert r['score'] == round(1.0 - row['dist'], 4)
        assert r['text'] == row['text']
        assert r['video_title'].startswith('title-')
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

exec
/usr/bin/zsh -lc "jq 'keys, .metadata, (.segments|length), (.queries|length), (.segments[0]|keys), (.queries[0]|keys), [.segments[].embedding|length], [.queries[].embedding|length]' tests/python/fixtures/real_segments_2026-08-14.json && jq -r '[.segments[] | {id,video_youtube_id,chunk_index,domain,text_len:(.text|length),dim:(.embedding|length),norm:(.embedding|map(. * .)|add|sqrt),min:(.embedding|min),max:(.embedding|max)}], [.queries[] | {query,dim:(.embedding|length),norm:(.embedding|map(. * .)|add|sqrt),min:(.embedding|min),max:(.embedding|max)}]' tests/python/fixtures/real_segments_2026-08-14.json && git log --oneline -- tests/python/fixtures/real_segments_2026-08-14.json | head -10 && git status --short" in /home/mgerasolo/Dev/KnowledgeStack-wt-semantic-search
 succeeded in 0ms:
[
  "captured",
  "dim",
  "model",
  "queries",
  "segments",
  "source"
]
null
6
2
[
  "chunk_index",
  "domain",
  "embedding",
  "end_time",
  "id",
  "start_time",
  "text",
  "video_youtube_id"
]
[
  "embedding",
  "text"
]
[
  768,
  768,
  768,
  768,
  768,
  768
]
[
  768,
  768
]
[
  {
    "id": "segment:087f932cafa6",
    "video_youtube_id": "b8-hI5CE9jc",
    "chunk_index": 9,
    "domain": "religion",
    "text_len": 445,
    "dim": 768,
    "norm": 1.0000000199591272,
    "min": -0.12940827012062073,
    "max": 0.11449598520994186
  },
  {
    "id": "segment:08939a53f818",
    "video_youtube_id": "UzsiGvsFtpk",
    "chunk_index": 149,
    "domain": "religion",
    "text_len": 485,
    "dim": 768,
    "norm": 1.0000000211613924,
    "min": -0.10948287695646286,
    "max": 0.15105047821998596
  },
  {
    "id": "segment:08a751596d2f",
    "video_youtube_id": "gMcp1g_MTZ0",
    "chunk_index": 10,
    "domain": "religion",
    "text_len": 414,
    "dim": 768,
    "norm": 1.0000000453597422,
    "min": -0.1334584653377533,
    "max": 0.11311475187540054
  },
  {
    "id": "segment:04ec435ded68",
    "video_youtube_id": "_kZCoW-Qxnc",
    "chunk_index": 66,
    "domain": "ai-automation",
    "text_len": 501,
    "dim": 768,
    "norm": 0.9999999765331729,
    "min": -0.11804770678281784,
    "max": 0.11304402351379395
  },
  {
    "id": "segment:04f77ac7cfa6",
    "video_youtube_id": "_l6WvbM1TbI",
    "chunk_index": 24,
    "domain": "ai-automation",
    "text_len": 496,
    "dim": 768,
    "norm": 1.000000003652614,
    "min": -0.09944397956132889,
    "max": 0.12106674909591675
  },
  {
    "id": "segment:04facab8ce28",
    "video_youtube_id": "Aj6hoC9JaLI",
    "chunk_index": 17,
    "domain": "ai-automation",
    "text_len": 496,
    "dim": 768,
    "norm": 0.9999999827948287,
    "min": -0.12454082816839218,
    "max": 0.11277114599943161
  }
]
[
  {
    "query": null,
    "dim": 768,
    "norm": 0.9999999989197491,
    "min": -0.12162633240222931,
    "max": 0.13197897374629974
  },
  {
    "query": null,
    "dim": 768,
    "norm": 0.9999999452624588,
    "min": -0.10600998252630234,
    "max": 0.10860975831747055
  }
]
9f52eb1 test: real-data fixture + isolated embedding-service module loader
?? planning/

exec
/usr/bin/zsh -lc "jq '{source,captured,model,dim,queries:[.queries[].text]}' tests/python/fixtures/real_segments_2026-08-14.json && git show --stat --oneline 9f52eb1 && git show 9f52eb1 -- tests/python/fixtures/real_segments_2026-08-14.json | sed -n '1,45p' && rg -n \"real_segments_2026|REAL fixture|captured 2026\" -S . --glob '"'!tests/python/fixtures/*.json'"'" in /home/mgerasolo/Dev/KnowledgeStack-wt-semantic-search
 succeeded in 0ms:
{
  "source": "live SurrealDB ns=knowledge db=transcripts + nomic-embed-text-v2-moe on Jarvis",
  "captured": "2026-08-14",
  "model": "nomic-embed-text-v2-moe",
  "dim": 768,
  "queries": [
    "what the Bible teaches about building wealth",
    "using AI agents to automate repetitive work"
  ]
}
9f52eb1 test: real-data fixture + isolated embedding-service module loader
 docs/plans/2026-08-14-semantic-search.md           |  174 +
 tests/python/embedding_loader.py                   |   62 +
 .../python/fixtures/real_segments_2026-08-14.json  | 6230 ++++++++++++++++++++
 3 files changed, 6466 insertions(+)
commit 9f52eb1822cfb557929beb05be14b9537121f066
Author: Matt Gerasolo <matt@gerasolo.com>
Date:   Fri Aug 14 00:06:23 2026 -0400

    test: real-data fixture + isolated embedding-service module loader
    
    Fixture is 6 real corpus segments + 2 real query vectors captured
    2026-08-14 from the live SurrealDB corpus and the live
    nomic-embed-text-v2-moe model (Tier-4 frozen real-data fixture).
    
    Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

diff --git a/tests/python/fixtures/real_segments_2026-08-14.json b/tests/python/fixtures/real_segments_2026-08-14.json
new file mode 100644
index 0000000..02cc920
--- /dev/null
+++ b/tests/python/fixtures/real_segments_2026-08-14.json
@@ -0,0 +1,6230 @@
+{
+ "captured": "2026-08-14",
+ "source": "live SurrealDB ns=knowledge db=transcripts + nomic-embed-text-v2-moe on Jarvis",
+ "model": "nomic-embed-text-v2-moe",
+ "dim": 768,
+ "segments": [
+  {
+   "chunk_index": 9,
+   "domain": "religion",
+   "end_time": 0.0,
+   "id": "segment:087f932cafa6",
+   "start_time": 0.0,
+   "text": "And then I use the assignment that he makes me king over to serve the people I come in contact with. And by the way, if we can remember that our whole lives, if that's the thing we focus on our whole lives, it it changes everything. >> It doesn't just change everything for you. It changes everything for you and everybody that you affect. >> But the enemy doesn't like that because the enemy wants God's praise. The enemy wants God's authority.",
+   "video_youtube_id": "b8-hI5CE9jc",
+   "embedding": [
+    0.015937382355332375,
+    0.01748500019311905,
+    -0.004488455597311258,
+    -0.025744104757905006,
+    -0.010231402702629566,
+    -0.039421066641807556,
+    0.018339697271585464,
+    0.02624260075390339,
+    0.05263461545109749,
+    -0.004592342302203178,
+    0.021593691781163216,
+    -0.008879000321030617,
./planning/codex-tests.md:14:Independently verify this repo's python test battery. Run: .venv-test/bin/python -m pytest tests/python/ -v 2>&1 | tail -60. Then inspect tests/python/*.py for gaming: pytest.mark.skip/xfail, assertions that can never fail, tests asserting on mocks so tightly they test nothing, fixtures that fake what they claim to verify. The fixture tests/python/fixtures/real_segments_2026-08-14.json is claimed to be REAL corpus data — sanity-check its structure (6 segments with 768-dim embeddings + 2 queries). End with exactly one line: VERDICT: PASS or VERDICT: FAIL — followed by reasons.
./planning/codex-tests.md:89:tests/python/fixtures/real_segments_2026-08-14.json
./planning/codex-tests.md:230:# The real index definition string from the live server (captured 2026-08-14)
./planning/codex-tests.md:512:    (Path(__file__).parent / 'fixtures' / 'real_segments_2026-08-14.json')
./planning/codex-tests.md:629:    """A payload built from the frozen REAL fixture segments."""
./planning/codex-tests.md:1475:Vectors and distances come from the frozen REAL fixture (live corpus + live
./planning/codex-tests.md:1476:model, captured 2026-08-14) — no invented embeddings.
./planning/codex-tests.md:1486:    (Path(__file__).parent / 'fixtures' / 'real_segments_2026-08-14.json')
./planning/codex-tests.md:1652:/usr/bin/zsh -lc "jq 'keys, .metadata, (.segments|length), (.queries|length), (.segments[0]|keys), (.queries[0]|keys), [.segments[].embedding|length], [.queries[].embedding|length]' tests/python/fixtures/real_segments_2026-08-14.json && jq -r '[.segments[] | {id,video_youtube_id,chunk_index,domain,text_len:(.text|length),dim:(.embedding|length),norm:(.embedding|map(. * .)|add|sqrt),min:(.embedding|min),max:(.embedding|max)}], [.queries[] | {query,dim:(.embedding|length),norm:(.embedding|map(. * .)|add|sqrt),min:(.embedding|min),max:(.embedding|max)}]' tests/python/fixtures/real_segments_2026-08-14.json && git log --oneline -- tests/python/fixtures/real_segments_2026-08-14.json | head -10 && git status --short" in /home/mgerasolo/Dev/KnowledgeStack-wt-semantic-search
./tests/python/test_semantic_search.py:4:Vectors and distances come from the frozen REAL fixture (live corpus + live
./tests/python/test_semantic_search.py:5:model, captured 2026-08-14) — no invented embeddings.
./tests/python/test_semantic_search.py:15:    (Path(__file__).parent / 'fixtures' / 'real_segments_2026-08-14.json')
./tests/python/test_embedder.py:16:    (Path(__file__).parent / 'fixtures' / 'real_segments_2026-08-14.json')
./tests/python/test_embedder.py:133:    """A payload built from the frozen REAL fixture segments."""
./tests/python/test_backfill.py:22:# The real index definition string from the live server (captured 2026-08-14)
./docs/plans/2026-08-14-semantic-search.md:38:| `tests/python/fixtures/real_segments_2026-08-14.json` (create) | Frozen real segments + real 768-dim vectors from the live model, capture-dated |
./docs/plans/2026-08-14-semantic-search.md:91:**Files:** Create `tests/python/embedding_loader.py` (code above), `tests/python/fixtures/real_segments_2026-08-14.json`.

exec
/usr/bin/zsh -lc "jq '[.segments[] | {id,chunk_index,start_time,end_time,time_valid:(.end_time >= .start_time),embedding_numeric:(.embedding|all(type == \"number\"))}], {segment_ids_unique:([.segments[].id]|length == ([.segments[].id]|unique|length)), videos_unique:([.segments[].video_youtube_id]|length == ([.segments[].video_youtube_id]|unique|length)), all_segment_dims_match:(.segments|all(.embedding|length == 768)), all_query_dims_match:(.queries|all(.embedding|length == 768)), declared_dim:.dim}' tests/python/fixtures/real_segments_2026-08-14.json" in /home/mgerasolo/Dev/KnowledgeStack-wt-semantic-search
 exited 5 in 0ms:
jq: error (at tests/python/fixtures/real_segments_2026-08-14.json:6230): Cannot index array with string "segments"
[
  {
    "id": "segment:087f932cafa6",
    "chunk_index": 9,
    "start_time": 0.0,
    "end_time": 0.0,
    "time_valid": true,
    "embedding_numeric": true
  },
  {
    "id": "segment:08939a53f818",
    "chunk_index": 149,
    "start_time": 0.0,
    "end_time": 0.0,
    "time_valid": true,
    "embedding_numeric": true
  },
  {
    "id": "segment:08a751596d2f",
    "chunk_index": 10,
    "start_time": 0.0,
    "end_time": 0.0,
    "time_valid": true,
    "embedding_numeric": true
  },
  {
    "id": "segment:04ec435ded68",
    "chunk_index": 66,
    "start_time": 1684.0,
    "end_time": 1706.0,
    "time_valid": true,
    "embedding_numeric": true
  },
  {
    "id": "segment:04f77ac7cfa6",
    "chunk_index": 24,
    "start_time": 582.0,
    "end_time": 605.0,
    "time_valid": true,
    "embedding_numeric": true
  },
  {
    "id": "segment:04facab8ce28",
    "chunk_index": 17,
    "start_time": 422.0,
    "end_time": 451.0,
    "time_valid": true,
    "embedding_numeric": true
  }
]

codex
VERDICT: PASS — 132/132 tests passed; no skip/xfail markers (three inactive date guards only); mocks exercise observable contracts; assertions are generally meaningful; fixture has 6 unique segments and 2 queries, all numeric 768-dimensional, near-unit-normalized embeddings with credible corpus metadata/provenance.
hook: Stop
hook: Stop Completed
tokens used
37,342
VERDICT: PASS — 132/132 tests passed; no skip/xfail markers (three inactive date guards only); mocks exercise observable contracts; assertions are generally meaningful; fixture has 6 unique segments and 2 queries, all numeric 768-dimensional, near-unit-normalized embeddings with credible corpus metadata/provenance.
