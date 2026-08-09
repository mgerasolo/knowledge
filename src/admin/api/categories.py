"""Canonical category taxonomy.

The two stores disagree about category names, and the corpus vocabulary is itself
split: AI arrives as `ai`, `ai-coding`, `ai-automation` and `ai-tech` (689 videos
between them), faith as `faith` and `religion`. A per-category chart built on the
raw values would show four AI bars and two faith bars, none of which are wrong
individually and all of which are wrong together.

Everything here is a READ-TIME mapping. Nothing rewrites the stored value, so
re-tagging channels upstream later needs no migration and no backfill.

Business and Finance are deliberately separate. Matt: "Finance is about investing
in money. Business is about running a business, like Alex Hormozi's." Nothing is
currently tagged finance — the category still renders, at zero, because a hidden
empty category is indistinguishable from a category that stopped producing.
"""
from dataclasses import dataclass

OTHER = "Other"

# Top-level category -> the raw values that map into it.
#
# Order matters: the chart assigns colours by position, so a reordering would
# silently recolour a category and make the chart imply a change that did not
# happen. Other is last so it reads as the remainder it is.
_TAXONOMY: dict[str, tuple[str, ...]] = {
    "AI": ("ai", "ai-automation", "ai-coding", "ai-tech"),
    "Business": ("business",),
    "Finance": ("finance",),
    "Politics": ("political",),
    "Mindset": ("mindset",),
    "Health": ("health",),
    "Faith": ("faith", "religion"),
    OTHER: (),
}

TOP_LEVEL_ORDER: list[str] = list(_TAXONOMY.keys())

# Reverse index, built once. Raw value -> top-level name.
_RAW_TO_TOP: dict[str, str] = {
    raw: top for top, raws in _TAXONOMY.items() for raw in raws
}

# Values we deliberately route to Other. Listed explicitly so they are NOT
# reported as taxonomy drift — "general" is a real upstream category meaning
# uncategorised, not a new value nobody has mapped yet.
_KNOWN_OTHER: frozenset[str] = frozenset({"general", "unknown", "none", ""})


def _normalise(raw: str | None) -> str:
    """Domain values are hand-entered upstream. A stray capital or trailing space
    must not create a phantom category."""
    if raw is None:
        return ""
    return str(raw).strip().lower()


def canonical_category(raw: str | None) -> str:
    """Map any raw domain value to its top-level category.

    Unknown values land in Other rather than raising — a new upstream category
    must not take the dashboard down. Use split_known_unknown() to surface them.
    """
    return _RAW_TO_TOP.get(_normalise(raw), OTHER)


def subcategories_of(top_level: str) -> list[str]:
    """The raw values that roll up into a top-level category, for drill-down.

    Display-only. Returns [] for an unrecognised name so a bad query parameter
    yields an empty chart rather than an error page.
    """
    return list(_TAXONOMY.get(top_level, ()))


def split_known_unknown(raws) -> tuple[set[str], set[str]]:
    """Partition raw values into recognised and unrecognised.

    The unrecognised set is surfaced on the page. Taxonomy drift that nobody sees
    is how the AI-into-four-strings split happened in the first place.
    """
    known: set[str] = set()
    unknown: set[str] = set()
    for raw in raws:
        value = _normalise(raw)
        if value in _RAW_TO_TOP:
            known.add(value)
        elif value in _KNOWN_OTHER:
            known.add(value)
        else:
            unknown.add(value)
    return known, unknown


@dataclass(frozen=True)
class CategoryResolution:
    """A category plus how confident we are in it.

    `by_fallback` is not cosmetic: 22 channels have videos but no channel record,
    so their category comes from the video's own field rather than the curated
    channel one. The page reports how many videos landed that way, so "22 channels
    are unadopted" stays visible instead of dissolving into Other.
    """

    category: str
    by_fallback: bool


def resolve_category(
    channel_domain: str | None, video_domain: str | None
) -> CategoryResolution:
    """Decide a video's category.

    Order: the channel record's domain (human-curated), then the video's own
    domain, then Other.
    """
    channel_value = _normalise(channel_domain)
    if channel_value and channel_value in _RAW_TO_TOP:
        return CategoryResolution(_RAW_TO_TOP[channel_value], by_fallback=False)

    return CategoryResolution(canonical_category(video_domain), by_fallback=True)
