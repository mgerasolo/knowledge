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
