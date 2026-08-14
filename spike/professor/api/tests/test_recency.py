from datetime import date, timedelta

import pytest

from retrieval import freshness_score, recency_weighted_score


TODAY = date(2026, 8, 14)


def test_freshness_is_one_today_and_for_future_dates():
    assert freshness_score(TODAY, today=TODAY, horizon_days=730) == 1.0
    assert freshness_score(TODAY + timedelta(days=5), today=TODAY, horizon_days=730) == 1.0


def test_freshness_linearly_decays_to_zero_at_horizon():
    assert freshness_score(TODAY - timedelta(days=365), today=TODAY, horizon_days=730) == 0.5
    assert freshness_score(TODAY - timedelta(days=730), today=TODAY, horizon_days=730) == 0.0
    assert freshness_score(TODAY - timedelta(days=900), today=TODAY, horizon_days=730) == 0.0
    assert freshness_score(None, today=TODAY, horizon_days=730) == 0.0


def test_recency_weighting_applies_configured_boost():
    assert recency_weighted_score(0.8, TODAY, today=TODAY, rec_boost=0.15) == pytest.approx(0.92)
    assert recency_weighted_score(
        0.8, TODAY - timedelta(days=730), today=TODAY, rec_boost=0.15
    ) == pytest.approx(0.8)


def test_invalid_scoring_knobs_are_rejected():
    with pytest.raises(ValueError):
        freshness_score(TODAY, horizon_days=0)
    with pytest.raises(ValueError):
        recency_weighted_score(0.5, TODAY, rec_boost=-0.1)
