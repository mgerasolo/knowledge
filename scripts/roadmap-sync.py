#!/usr/bin/env python3
"""Regenerate ROADMAP.md from the GitHub issue tracker.

Why this exists
---------------
Matt wants a roadmap he can open in his editor. He does NOT want a second
record of the work that quietly drifts away from the issue tracker — and a
hand-maintained roadmap always does, because nobody updates two places.

Those two wants are only compatible if the roadmap is a *projection* of the
issues rather than a parallel copy of them. So this script owns the file:
everything in ROADMAP.md is derived from `gh issue list` on every run, and the
only human-authored region is the block between the HAND-WRITTEN markers, which
is carried across untouched. Nothing else in the file survives a regeneration,
which is exactly the property that makes drift impossible.

The shape is the nested work tree Matt already reads in conversation: one
anchor line, themes as branches, issues as leaves, finished work left in place
under its theme rather than exiled to a trophy case at the bottom. Every leaf
carries an issue number, a title and a priority — and nothing else. No text is
copied out of an issue body, because copied text is precisely what rots.

Design rules that matter if you edit this
-----------------------------------------
* Every open issue lands in exactly one theme, and that is ASSERTED before
  anything is written. An issue that matched no theme would silently vanish
  from the roadmap, which is the same failure as letting the file go stale —
  so unmatched issues get a visible "Not yet themed" branch instead.
* Themes are DERIVED each run by matching rules against the issue title (with
  the body as a fallback), never by storing a theme against an issue number.
  A stored mapping would be a second record, and a second record drifts.
* An issue with no `phase:` label counts as backlog — "awaiting triage" and
  "nobody has labelled it yet" are the same state, and treating them
  differently is how issues fall off the edge of the page.
* Failure is loud and leaves the existing file alone. A roadmap that is a day
  stale is useful; an empty roadmap written over a good one is a data loss.

Usage:
    python3 scripts/roadmap-sync.py            # rewrite ROADMAP.md
    python3 scripts/roadmap-sync.py --stdout   # print it, write nothing
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROADMAP = REPO_ROOT / "ROADMAP.md"
REGEN_COMMAND = "python3 scripts/roadmap-sync.py"

# Fetch cap. If a run ever comes back with exactly this many issues we cannot
# tell a full tracker from a truncated one, so the run fails rather than
# publishing a tree that is quietly missing the newest work.
FETCH_LIMIT = 500

HAND_START = "<!-- HAND-WRITTEN:START -->"
HAND_END = "<!-- HAND-WRITTEN:END -->"

# Closed issues shown in the tree. Finished work stays visible under its theme
# so the roadmap shows where we are going AND what got done — but capped, or
# the tree slowly turns into a trophy case and buries what is left.
MAX_CLOSED_SHOWN = 15

# --- Icons, matching what Matt already reads in conversation ---------------
I_DONE = "\N{THUMBS UP SIGN}"          # done and verified
I_RAN = "\N{WHITE HEAVY CHECK MARK}"   # ran, not yet verified
I_PROG = "\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}"  # in progress
I_TODO = "\N{WHITE LARGE SQUARE}"      # not started
I_ASK = "\N{BLACK QUESTION MARK ORNAMENT}"   # needs a decision from Matt
I_WAIT = "\N{HOURGLASS WITH FLOWING SAND}"   # waiting on an external system
I_LATER = "\N{PUSHPIN}"                # future enhancement

# --- "Needs Matt" detection -------------------------------------------------
# The backlog-capture agent does NOT use next:* / status:* labels; it flags a
# blocking decision in the issue body, with one marker that is reliably
# machine-readable and one written for humans. Both are matched here.
#
# Deliberately narrow. A false positive drags routine work into the section
# Matt reads first, which is how that signal stops being read at all. In
# particular "a written plan, agreed with Matt" does NOT count: the deliverable
# there is a plan we write, not an answer we are waiting on.
NEEDS_MATT_CHECKBOX = re.compile(r"^\s*[-*]\s*\[ \]\s*Matt has\b", re.I | re.M)
NEEDS_MATT_SENTENCE = re.compile(
    r"a\s+(?:one-line\s+)?decision\s+from\s+Matt\b"
    r"|needs\s+a\s+design\s+conversation\s+with\s+Matt\b",
    re.I,
)
# Labels are still honoured if anyone ever does apply them.
NEEDS_MATT_LABELS = {
    "next:human-input",
    "next:human-verification",
    "status:pending-approval",
}
BLOCKED_LABELS = {"status:blocked"}

PHASE_RE = re.compile(r"^phase:(\d+)-")
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unset": 4}

# --- Themes -----------------------------------------------------------------
# Ordered; first match wins, matched against the title first and the body only
# as a fallback. Titles here are written as full sentences and are far more
# reliable than bodies, which mention everything in passing.
#
# Order is also the order the branches appear in the tree, so it reads as a
# narrative: what the product is missing, then keeping the intake alive, then
# trusting what we already have, then the archive programme, then our own tools.
THEMES: list[tuple[str, str]] = [
    (
        "Capabilities the product assumes but does not have",
        r"embedding|semantic search|meaning-based search|vector|qdrant"
        r"|tagging|tag graph|\b501\b|\brag\b|professor|personality",
    ),
    (
        "Ingestion reliability — keeping transcripts arriving",
        r"rate.?limit|yt-dlp|proxy|consent page|\bfeeds?\b|sweep|cadence"
        r"|schedul|queue|worker|scraper|javascript runtime|dormant",
    ),
    (
        "Corpus quality — trusting what is already stored",
        r"search library|metadata|publish date|description|quarantin"
        r"|duplicat|channel folder|deleted, made private|age-restricted"
        r"|shorts|dilute|view count|chapter|drift apart",
    ),
    (
        "The backfill programme — how deep we go",
        r"stage 2|stage two|deep livestream|livestream archives"
        r"|\d+ livestreams|per-channel depth",
    ),
    (
        "Tooling and process — how we keep ourselves honest",
        r"consumer guide|documentation|\bdocs?\b|\bguide\b|roadmap|dashboard"
        r"|re-verification|verif|\btests?\b|health",
    ),
]
UNTHEMED = "Not yet themed"

SEED_HAND_WRITTEN = """## Direction

*This block is the only hand-written part of this file. Everything below it is
regenerated from the issue tracker, so anything you type outside these two
markers will be erased on the next run — but whatever you write in here is kept
forever. Use it for the "why": where KnowledgeStack is going, and what matters
most right now. Matt, replace this paragraph with that.*

Three themes run through the work currently on the board:

- **Ingestion reliability.** Transcripts have to keep arriving without anyone
  watching for them. The pipeline once ran empty for two weeks while its health
  check reported healthy, and nothing about that should be repeatable.
- **Corpus quality.** What is already stored has to be complete, correctly
  attributed, and free of duplicate channel folders and encoding damage.
  A library you cannot trust is not a library.
- **The two capabilities that were never built.** Semantic search and tagging.
  The rest of the product is written as though both already exist. Neither
  does.
"""


class SyncError(RuntimeError):
    """Anything that must stop the run before ROADMAP.md is touched."""


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------


def fetch_issues() -> list[dict]:
    """Pull every issue from GitHub, or raise. Never returns a partial list."""
    cmd = [
        "gh", "issue", "list",
        "--state", "all",
        "--limit", str(FETCH_LIMIT),
        "--json", "number,title,state,labels,body,closedAt,url",
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=120
        )
    except FileNotFoundError:
        raise SyncError("`gh` is not installed or not on PATH.")
    except subprocess.TimeoutExpired:
        raise SyncError("`gh issue list` timed out after 120s.")

    if proc.returncode != 0:
        raise SyncError(
            f"`gh issue list` exited {proc.returncode}.\n"
            f"stderr: {proc.stderr.strip() or '(empty)'}"
        )

    try:
        issues = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SyncError(f"`gh issue list` did not return valid JSON: {exc}")

    if not isinstance(issues, list):
        raise SyncError("`gh issue list` returned something other than a list.")

    if not issues:
        raise SyncError(
            "`gh issue list` returned zero issues. Refusing to overwrite "
            "ROADMAP.md with an empty roadmap — this is almost always a broken "
            "credential or the wrong repo, not an empty tracker."
        )

    if len(issues) >= FETCH_LIMIT:
        raise SyncError(
            f"Fetched exactly {FETCH_LIMIT} issues, so the list may be "
            f"truncated and the tree could be missing recent work. Raise "
            f"FETCH_LIMIT in {Path(__file__).name} and re-run."
        )

    return issues


# --------------------------------------------------------------------------
# Reading one issue
# --------------------------------------------------------------------------


def label_names(issue: dict) -> set[str]:
    return {lab.get("name", "") for lab in (issue.get("labels") or [])}


def priority_of(issue: dict) -> str:
    """Highest priority label on the issue, or 'unset'.

    Deliberately not "the first one found": labels arrive as a set, so an issue
    carrying two priority labels would otherwise render differently between
    runs and show up as a phantom diff every time.
    """
    found = [
        n.split(":", 1)[1] for n in label_names(issue) if n.startswith("priority:")
    ]
    if not found:
        return "unset"
    return min(found, key=lambda p: PRIORITY_ORDER.get(p, 8))


def area_of(issue: dict) -> str | None:
    areas = sorted(
        n.split(":", 1)[1] for n in label_names(issue) if n.startswith("area:")
    )
    return areas[0] if areas else None


def phase_of(issue: dict) -> int | None:
    """Phase number, or None when the issue carries no phase label at all."""
    for name in sorted(label_names(issue)):
        match = PHASE_RE.match(name)
        if match:
            return int(match.group(1))
    return None


def needs_matt(issue: dict) -> bool:
    if label_names(issue) & NEEDS_MATT_LABELS:
        return True
    body = issue.get("body") or ""
    return bool(NEEDS_MATT_CHECKBOX.search(body) or NEEDS_MATT_SENTENCE.search(body))


def icon_of(issue: dict) -> str:
    """One icon per issue, highest-precedence state wins."""
    if issue.get("state") == "CLOSED":
        # Closed but still asking for a human to check it is "ran, unverified".
        if label_names(issue) & {"needs:verification", "next:human-verification"}:
            return I_RAN
        return I_DONE
    if needs_matt(issue):
        return I_ASK
    if label_names(issue) & BLOCKED_LABELS:
        return I_WAIT
    phase = phase_of(issue)
    if phase is not None and 1 <= phase <= 8:
        return I_PROG
    if priority_of(issue) == "low":
        return I_LATER
    return I_TODO


def theme_of(issue: dict) -> str:
    """Derive the theme from the issue text. Never stored, always recomputed."""
    title = issue.get("title") or ""
    body = issue.get("body") or ""
    for name, pattern in THEMES:
        if re.search(pattern, title, re.I):
            return name
    for name, pattern in THEMES:
        if re.search(pattern, body, re.I):
            return name
    return UNTHEMED


# --------------------------------------------------------------------------
# Building the tree
# --------------------------------------------------------------------------

# Order issues within a theme: what is asked of Matt first, what is moving
# next, then what is queued, and finished work last so the tree reads as
# "here is what is left" rather than "here is what we did".
ICON_SORT = {I_ASK: 0, I_PROG: 1, I_WAIT: 2, I_TODO: 3, I_LATER: 4,
             I_RAN: 5, I_DONE: 6}


def build_tree(issues: list[dict]) -> tuple[list[tuple[str, list[dict]]], dict]:
    """Group issues into themes and assert nothing was dropped."""
    open_issues = [i for i in issues if i.get("state") == "OPEN"]
    closed = [i for i in issues if i.get("state") == "CLOSED" and i.get("closedAt")]
    closed.sort(key=lambda i: i["closedAt"], reverse=True)
    shown_closed = closed[:MAX_CLOSED_SHOWN]

    grouped: dict[str, list[dict]] = {}
    for issue in open_issues + shown_closed:
        grouped.setdefault(theme_of(issue), []).append(issue)

    # Every issue must appear exactly once. A dropped issue is invisible work,
    # and a duplicated one makes the counts lie — both are worse than failing.
    placed_numbers = [i["number"] for v in grouped.values() for i in v]
    expected_numbers = [i["number"] for i in open_issues + shown_closed]
    if sorted(placed_numbers) != sorted(expected_numbers):
        missing = set(expected_numbers) - set(placed_numbers)
        dupes = {n for n in placed_numbers if placed_numbers.count(n) > 1}
        raise SyncError(
            f"Theme assignment is not a clean partition — missing {sorted(missing)}, "
            f"duplicated {sorted(dupes)}. Refusing to write a roadmap that "
            f"drops or double-counts work."
        )

    for issue in open_issues:
        if phase_of(issue) == 9:
            print(
                f"  warning: #{issue['number']} is open but labelled "
                f"phase:9-done.", file=sys.stderr,
            )

    ordered: list[tuple[str, list[dict]]] = []
    for name, _ in THEMES:
        if grouped.get(name):
            ordered.append((name, sort_theme(grouped[name])))
    if grouped.get(UNTHEMED):
        # Always visible: an unthemed issue is a gap in the rules, not a
        # reason to hide work.
        ordered.append((UNTHEMED, sort_theme(grouped[UNTHEMED])))

    counts = {
        "total": len(issues),
        "open": len(open_issues),
        "in_flight": sum(1 for i in open_issues if icon_of(i) == I_PROG),
        "asking": sum(1 for i in open_issues if icon_of(i) == I_ASK),
        "closed": sum(1 for i in issues if i.get("state") == "CLOSED"),
        "closed_shown": len(shown_closed),
    }
    return ordered, counts


def sort_theme(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda i: (
            ICON_SORT.get(icon_of(i), 9),
            PRIORITY_ORDER.get(priority_of(i), 9),
            i["number"],
        ),
    )


def theme_icon(items: list[dict]) -> str:
    """A branch shows the most urgent state underneath it."""
    icons = {icon_of(i) for i in items}
    for candidate in (I_PROG, I_ASK, I_WAIT, I_TODO, I_LATER, I_RAN):
        if candidate in icons:
            return candidate
    return I_DONE


def anchor_state(counts: dict) -> str:
    if counts["in_flight"]:
        state = "IN PROGRESS"
    elif counts["asking"]:
        state = "NEEDS MATT"
    elif counts["open"]:
        state = "NOT STARTED"
    else:
        state = "COMPLETE"

    bits = [state]
    if counts["asking"]:
        bits.append(
            f"{counts['asking']} decision{'s' if counts['asking'] != 1 else ''} "
            f"waiting on you"
        )
    bits.append(
        f"{counts['in_flight']} in flight" if counts["in_flight"]
        else "nothing in flight"
    )
    return " · ".join(bits)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
# Tree lines end with two spaces: that is a markdown hard line break, so the
# tree keeps its shape in a rendered preview while the issue links stay
# clickable. A fenced code block would preserve the shape but kill the links.


def leaf_text(issue: dict) -> str:
    meta = priority_of(issue)
    if issue.get("state") == "CLOSED" and issue.get("closedAt"):
        meta = f"{meta} · closed {issue['closedAt'][:10]}"
    return (
        f"{icon_of(issue)} {issue['title']} "
        f"([#{issue['number']}]({issue['url']})) — _{meta}_"
    )


def render_tree(themes: list[tuple[str, list[dict]]], counts: dict) -> list[str]:
    lines = [f"\N{ANCHOR} **KnowledgeStack** — {anchor_state(counts)}"]
    for t_index, (name, items) in enumerate(themes):
        last_theme = t_index == len(themes) - 1
        branch = "└─" if last_theme else "├─"
        spine = "   " if last_theme else "│  "
        open_here = sum(1 for i in items if i.get("state") == "OPEN")
        lines.append(f"{branch}{theme_icon(items)} **{name}** — {open_here} open")
        for i_index, issue in enumerate(items):
            twig = "└─" if i_index == len(items) - 1 else "├─"
            lines.append(f"{spine}{twig}{leaf_text(issue)}")
    return [f"{line}  " for line in lines]


def render(themes: list, counts: dict, hand: str) -> str:
    stamp = datetime.now(timezone.utc).astimezone()
    lines = [
        "# KnowledgeStack Roadmap",
        "",
        "> **This file is generated. Do not hand-edit it** — except inside the",
        "> hand-written block below, which survives every regeneration.",
        ">",
        f"> Regenerate with `{REGEN_COMMAND}`",
        ">",
        "> The GitHub issue tracker is the source of truth. If this file and an",
        "> issue disagree, the issue is right and this file is stale. Fix the",
        "> issue and re-run — never patch this file by hand.",
        ">",
        f"> Generated {stamp.strftime('%Y-%m-%d %H:%M %Z')} from "
        f"{counts['total']} issues.",
        "",
        f"**{counts['open']} open · {counts['in_flight']} in flight · "
        f"{counts['asking']} awaiting your decision · "
        f"{counts['closed']} closed**",
        "",
        HAND_START,
        "",
        hand.strip("\n"),
        "",
        HAND_END,
        "",
        "## Where everything stands",
        "",
    ]
    lines += render_tree(themes, counts)
    lines += [
        "",
        f"{I_DONE} done and verified · {I_RAN} ran, not yet verified · "
        f"{I_PROG} in progress · {I_TODO} not started · "
        f"{I_ASK} needs a decision from you · "
        f"{I_WAIT} waiting on an external system · "
        f"{I_LATER} future enhancement",
    ]
    if counts["closed"] > counts["closed_shown"]:
        lines += [
            "",
            f"*Showing the {counts['closed_shown']} most recently closed "
            f"issues of {counts['closed']}.*",
        ]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------
# Hand-written block preservation
# --------------------------------------------------------------------------


def read_hand_written(path: Path) -> str:
    """Recover Matt's prose from the existing file, or fail rather than guess.

    Losing this block silently is the single worst thing this script could do,
    so every ambiguous case stops the run instead of picking an interpretation.
    """
    if not path.exists():
        return SEED_HAND_WRITTEN

    text = path.read_text(encoding="utf-8")
    starts, ends = text.count(HAND_START), text.count(HAND_END)

    if starts == 0 and ends == 0:
        raise SyncError(
            f"{path.name} exists but has no {HAND_START} / {HAND_END} markers, "
            f"so there is no safe way to tell hand-written prose from generated "
            f"content. Restore the markers around the prose you want kept, or "
            f"delete the file to start over from the seed text."
        )
    if starts != 1 or ends != 1:
        raise SyncError(
            f"{path.name} has {starts} start marker(s) and {ends} end "
            f"marker(s); exactly one of each is required. Fix the markers by "
            f"hand — refusing to guess which text is yours."
        )

    head = text.index(HAND_START) + len(HAND_START)
    tail = text.index(HAND_END)
    if tail < head:
        raise SyncError(
            f"{path.name} has {HAND_END} before {HAND_START}. Fix the marker "
            f"order by hand — refusing to guess."
        )

    block = text[head:tail].strip("\n")
    return block if block.strip() else SEED_HAND_WRITTEN


def write_atomically(path: Path, content: str) -> None:
    """Write via a temp file + rename so a crash cannot truncate a good file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate ROADMAP.md from GitHub issues."
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print the roadmap instead of writing it (still fails loudly)",
    )
    args = parser.parse_args()

    try:
        hand = read_hand_written(ROADMAP)
        issues = fetch_issues()
        themes, counts = build_tree(issues)
        content = render(themes, counts, hand)
    except SyncError as exc:
        print(f"roadmap-sync: {exc}", file=sys.stderr)
        print("roadmap-sync: ROADMAP.md was NOT modified.", file=sys.stderr)
        return 1

    if args.stdout:
        sys.stdout.write(content)
        return 0

    write_atomically(ROADMAP, content)
    themed = " · ".join(
        f"{name.split(' — ')[0]} {len(items)}" for name, items in themes
    )
    print(
        f"roadmap-sync: wrote {ROADMAP.relative_to(REPO_ROOT)} from "
        f"{counts['total']} issues ({counts['open']} open, "
        f"{counts['asking']} awaiting Matt, {counts['closed']} closed)."
    )
    print(f"roadmap-sync: themes — {themed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
