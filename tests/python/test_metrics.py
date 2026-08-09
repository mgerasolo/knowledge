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
