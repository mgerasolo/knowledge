# Personalities and Appearances — Design

**Date:** 2026-08-17
**Status:** Design only. Nothing here is built. Awaiting Matt's approval before implementation.
**Anchor:** Track the *people* worth following — not just the channels — and notice, without
being asked, when one of them turns up in a video we already have.

---

## 1. What this is, in plain English

Today the system follows **channels**. That is the wrong unit for a person like Elon Musk,
who has no channel we follow but shows up constantly on channels we do. It is also a clumsy
unit for Lex Fridman, who *does* own a channel — but the interesting thing about a Lex video
is usually the guest, not Lex.

So this adds a second thing to track: a **personality** — a named person we care about. A
personality may own one of our tracked channels, in which case we link to that channel rather
than storing a second copy of it.

And it adds a record of where those people turn up: an **appearance** — one row saying "this
person is in this video, as a guest / as the host / just mentioned in passing, and here is how
sure we are and why."

Nothing goes hunting on YouTube. This release only notices people in videos we **already
hold**, by reading the title and description we already stored. Searching YouTube by a
person's name is deliberately deferred — see §9.

The payoff: when a video lands in the review Inbox, the ones with a tracked person in them
float to the top, and Matt sees "Elon Musk — guest" next to the title instead of a bare row.

---

## 2. The one rule this design is built around

This project's core defect, diagnosed with live evidence, is that every feature built its own
private store. There are currently **four different answers** to "how many videos do we have":

| Store | Count |
|---|---|
| Transcript files on disk | 5,393 |
| SurrealDB video records | 5,337 |
| A JSON list inside the transcript service | 5,955 |
| Postgres `pipeline_items` rows | 1,150 |

That is issue #18, and it is the reason a channel page once showed "0 indexed" for a channel
holding 86 videos.

**So: this feature adds no store of its own.** Two new tables, both in the same Postgres
database as `channels` and `pipeline_items`, both referencing `pipeline_items` by foreign key.
There is no personalities cache, no appearances JSON file, no SurrealDB mirror, no in-memory
registry that outlives a request. If a question about a personality or an appearance can be
answered, it is answered by a SQL query against these two tables.

A parallel session is converting `pipeline_items` into **the** register of record — one row per
video, every service reading and writing it. This design assumes that lands and depends on it:
`appearances.video_id` is a foreign key into it, and the matcher's work queue is a predicate on
it. If that conversion slips, this feature can still ship, but it will only see the ~1,150
videos currently in the table, and §7's backfill numbers get correspondingly smaller. That is a
sequencing note, not a blocker.

---

## 3. Schema

### 3.1 The migration

New file: `src/db/schema/005_personalities_and_appearances.sql`.

**Depends on `004_video_register.sql`** (the register design, written the same day). Both specs
were drafted in parallel and both originally claimed the number `004` — this one was renumbered.
That collision is worth naming rather than quietly fixing: two sessions each picking the next free
number without either knowing about the other is the same failure this whole effort exists to end,
in miniature. `004` must be applied first: it is what makes `pipeline_items` the register these
tables reference.

House style, matched from `002_ingestion_modes.sql` and `003_shorts_default_off.sql`: additive,
idempotent, applied by hand with `psql` against Banner, safe to run twice.

```sql
-- ============================================
-- 005: Personalities and Appearances
--
-- Two tables, both in THIS database, both keyed to pipeline_items. Nothing here
-- introduces a second place to ask "what videos do we have" — see issue #18,
-- where four stores already answer that question four different ways.
-- ============================================

-- ---------------------------------------------------------------
-- PERSONALITIES — people and experts worth tracking.
--
-- Deliberately NOT modelled as a kind of channel. Elon Musk has no channel we
-- follow and never will; Lex Fridman has one, and gets LINKED to it rather than
-- duplicated into it. A person and a publishing surface are different things and
-- collapsing them is what forces the "does this row mean the human or the feed?"
-- question later.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS personalities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,                     -- display form: "Elon Musk"
    slug TEXT NOT NULL,                     -- url form: "elon-musk"

    -- Every OTHER way this person's name appears in a title or description.
    -- "Elon", "@elonmusk", "E. Musk". Match quality lives and dies here, so the
    -- UI makes adding one cheap and previews what it would match first.
    aliases TEXT[] NOT NULL DEFAULT '{}',

    -- Set when this person owns a channel we already track. NULL is the normal
    -- case. ON DELETE SET NULL, not CASCADE: un-enrolling Lex's channel must not
    -- delete Lex — his guest spots on other channels are still the point.
    channel_id UUID REFERENCES channels(id) ON DELETE SET NULL,

    domain VARCHAR(50) NOT NULL DEFAULT 'general',
    priority INT NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    is_monitored BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,
    thumbnail_url TEXT,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT personalities_slug_unique UNIQUE (slug)
);

CREATE INDEX IF NOT EXISTS idx_personalities_monitored
    ON personalities(is_monitored) WHERE is_monitored = TRUE;
CREATE INDEX IF NOT EXISTS idx_personalities_domain ON personalities(domain);
CREATE INDEX IF NOT EXISTS idx_personalities_channel ON personalities(channel_id);
-- GIN over aliases so "is this alias already taken by someone else?" is one
-- indexed lookup rather than a scan. Aliases collide across people more often
-- than names do ("Chris" belongs to nobody and everybody).
CREATE INDEX IF NOT EXISTS idx_personalities_aliases ON personalities USING GIN (aliases);

-- ---------------------------------------------------------------
-- APPEARANCES — this person is in this video.
--
-- ONE row per (person, video). See the note on the unique constraint below:
-- a second row for the same pair is how you get two answers to one question,
-- which is the defect class this whole design is reacting to.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appearances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    personality_id UUID NOT NULL REFERENCES personalities(id) ON DELETE CASCADE,
    video_id UUID NOT NULL REFERENCES pipeline_items(id) ON DELETE CASCADE,

    -- Denormalised on purpose, and this is the ONE denormalisation in the design.
    -- It is the video's immutable natural key, it makes an appearance row
    -- readable without a join while debugging, and it is the recovery key if the
    -- register-of-record conversion ever rebuilds pipeline_items rows and takes
    -- the human confirmations down with them via the CASCADE above. Written by
    -- the API from the pipeline_items row, never from caller input.
    youtube_video_id VARCHAR(11) NOT NULL,

    role TEXT NOT NULL CHECK (role IN ('host', 'guest', 'mentioned')),

    -- 0.00-1.00. Constrained because an unconstrained numeric accepts both 0.87
    -- and 87 for "87% sure", and the second one silently wins every ranking.
    confidence NUMERIC(3,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),

    source TEXT NOT NULL CHECK (source IN
        ('channel-owner', 'title-pattern', 'description', 'llm', 'manual')),

    -- Who says so. The machine may only ever write 'suggested'. 'confirmed' and
    -- 'rejected' are written by a human pressing a button, and a matcher re-run
    -- must never overwrite either — see the upsert in §6.4. 'rejected' is a
    -- TOMBSTONE, not a deletion: without it, every rescan resurrects the false
    -- positive Matt just dismissed.
    status TEXT NOT NULL DEFAULT 'suggested'
        CHECK (status IN ('suggested', 'confirmed', 'rejected')),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    confirmed_by VARCHAR(100),

    -- The exact substring that matched, kept so a human reviewing a suggestion
    -- can see WHY in one glance, and so a false positive is diagnosable months
    -- later without re-deriving it.
    matched_text TEXT,
    -- How many independent signals agreed. Two weak signals are worth more than
    -- one, and the ranking needs to know the difference.
    signal_count INT NOT NULL DEFAULT 1,

    -- Which ruleset produced this row. A matcher improvement re-derives only the
    -- rows it owns; human decisions are never re-derived.
    matcher_version INT,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT appearances_person_video_unique UNIQUE (personality_id, video_id)
);

CREATE INDEX IF NOT EXISTS idx_appearances_personality ON appearances(personality_id);
CREATE INDEX IF NOT EXISTS idx_appearances_video ON appearances(video_id);
CREATE INDEX IF NOT EXISTS idx_appearances_youtube ON appearances(youtube_video_id);
-- The Inbox ranking reads only live rows; rejected tombstones must not cost it.
CREATE INDEX IF NOT EXISTS idx_appearances_live
    ON appearances(video_id, confidence DESC) WHERE status <> 'rejected';

-- ---------------------------------------------------------------
-- Scan state lives ON THE VIDEO, because that is what it is a fact about.
--
-- This also makes the matcher's work queue a database predicate rather than a
-- checkpoint file — the same property the embedding backfill relies on, which is
-- why that script is resumable by construction rather than by bookkeeping.
-- ---------------------------------------------------------------
ALTER TABLE pipeline_items
    ADD COLUMN IF NOT EXISTS appearances_scanned_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE pipeline_items
    ADD COLUMN IF NOT EXISTS appearances_matcher_version INT;

CREATE INDEX IF NOT EXISTS idx_pipeline_appearances_unscanned
    ON pipeline_items(appearances_scanned_at)
    WHERE appearances_scanned_at IS NULL;

-- ---------------------------------------------------------------
-- VIDEO_APPEARANCE_RANK — one score per video, for the review Inbox.
--
-- A VIEW, not a column: a stored score is a fifth number that drifts from the
-- rows it was computed from the first time anyone forgets to recompute it.
-- ---------------------------------------------------------------
CREATE OR REPLACE VIEW video_appearance_rank AS
SELECT
    a.video_id,
    -- Weights, and why they are what they are:
    --   guest 1.0     — the signal Matt actually wants
    --   mentioned 0.4 — real but weak; being talked about is not being there
    --   host 0.2      — TRUE FOR EVERY VIDEO ON THAT PERSON'S OWN CHANNEL, so it
    --                   discriminates nothing within a channel. Weighted low on
    --                   purpose: without this, all 800 Lex Fridman uploads
    --                   outrank a genuine Elon guest spot somewhere else.
    -- A suggested row is discounted to 0.7 because no human has agreed with it
    -- yet; it still counts, because Matt will never confirm 5,000 rows by hand
    -- and a feature that needs him to is a feature that does nothing.
    MAX(
        p.priority
        * CASE a.role WHEN 'guest' THEN 1.0 WHEN 'mentioned' THEN 0.4 ELSE 0.2 END
        * a.confidence
        * CASE a.status WHEN 'confirmed' THEN 1.0 ELSE 0.7 END
    )::NUMERIC(6,3)                                   AS personality_score,
    COUNT(*)                                          AS appearance_count,
    COUNT(*) FILTER (WHERE a.status = 'confirmed')    AS confirmed_count
FROM appearances a
JOIN personalities p ON p.id = a.personality_id
WHERE a.status <> 'rejected'
  AND p.is_monitored
GROUP BY a.video_id;

-- Reuse the existing trigger function from 001 rather than defining a parallel one.
DROP TRIGGER IF EXISTS personalities_updated_at ON personalities;
CREATE TRIGGER personalities_updated_at
    BEFORE UPDATE ON personalities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS appearances_updated_at ON appearances;
CREATE TRIGGER appearances_updated_at
    BEFORE UPDATE ON appearances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE personalities IS
    'People and experts we track, independent of whether they own a channel we follow';
COMMENT ON TABLE appearances IS
    'One row per (person, video): where a tracked person turns up, and how sure we are';
```

### 3.2 Changes from the shape in the brief, and why

Three deviations. Everything else is as proposed.

**1. `UNIQUE (personality_id, video_id)` instead of `UNIQUE (personality_id, video_id, role)`.**

The three-column key permits a person to hold `mentioned` *and* `guest` rows on the same video —
which is exactly what happens when the matcher first sees the name in a description and later,
after a better title rule ships, sees it after a "w/". You then have two rows disagreeing about
one fact, plus a UI that has to decide which to show and a rank that counts the person twice.
That is issue #18 reproduced at row scale.

Instead: one row, `role` is a mutable column, and the matcher **promotes** along a ladder
`mentioned → guest → host` and never demotes an existing row. A person cannot be both the host
and a guest of the same video, so nothing real is lost.

**2. `status` / `confirmed_at` / `confirmed_by`, and no auto-confirmation.**

The brief asks what threshold "auto-creates a row versus flagging for human confirmation." Both
of those need a place to live. The machine writes only `suggested`. A human writes `confirmed`
or `rejected`. This keeps "the computer thinks so" and "Matt checked" distinguishable forever —
the exact distinction MISTAKES.md #1 lost when a claimed-success count and an actual-writes
count were allowed to be the same number.

`rejected` rows are kept, not deleted. Without the tombstone, the next matcher run recreates
every false positive a human just cleared, and the human learns to stop clearing them.

**3. `NUMERIC(3,2)` with a range check, plus `matched_text`, `signal_count`, `matcher_version`.**

Bare `numeric` accepts `87` for "87% sure" and that value then dominates every ranking silently.
`matched_text` makes a suggestion reviewable in one glance. `matcher_version` is what makes a
rule improvement cheap: re-derive only the rows that version owns.

### 3.3 A note on why these are `TEXT ... CHECK` and not `ENUM`

`001` used Postgres enums. `002` then had to extend one with five `ALTER TYPE ... ADD VALUE`
statements, and an enum value cannot be removed at all. Meanwhile a `CHECK` constraint is
edited with one idempotent `ALTER TABLE`. There is a live example of the cost of getting this
wrong nearby: `pipeline_items.status` is written as `'skipped'` in
`src/admin/api/channels.py:764` and `:829`, and `'skipped'` is not a member of the
`pipeline_status` enum in any migration in this repo. Text plus a check would have failed
loudly on the first write instead.

---

## 4. API

New blueprint `src/admin/api/personalities.py`, registered in `src/admin/app.py` exactly like
the others:

```python
from api.personalities import personalities_bp
app.register_blueprint(personalities_bp, url_prefix=Config.API_PREFIX)
```

Conventions copied verbatim from `api/channels.py`: `get_db_cursor()` / `get_db_cursor(commit=True)`,
`<uuid:...>` route converters, `request.get_json(silent=True) or {}`, `{'error': ...}` bodies,
409 on a unique-constraint collision, 404 when a row is absent. Add the endpoint list to the
`/api/v1` index in `app.py` in the same commit, and to `docs/CONSUMER_GUIDE.md` in the same
commit — the consumer-guide rule is same-unit-of-work, not "later."

### 4.1 Personality CRUD

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/v1/personalities` | Filters `domain`, `is_monitored`, `has_channel`, `q` (name/alias substring). `sort` ∈ `name`\|`priority`\|`appearances`\|`last_seen`, `dir` ∈ `asc`\|`desc`. `limit` (default 100) / `offset`. Returns `{personalities: [...], total, limit, offset}`; each row carries `appearance_count`, `confirmed_count`, `last_seen_at`, and `channel_name` from a LEFT JOIN so the list page needs one call. |
| `GET` | `/api/v1/personalities/<uuid>` | Full row + owned-channel summary. 404 if absent. |
| `GET` | `/api/v1/personalities/by-slug/<slug>` | Same body. Exists because the page URL is slug-based (§5.3). |
| `POST` | `/api/v1/personalities` | Required: `name`. `slug` derived from the name when omitted (casefold, strip accents, non-alphanumerics → `-`); a collision returns **409** with the existing id, never a silently suffixed slug. Optional: `aliases`, `channel_id`, `domain`, `priority`, `is_monitored`, `notes`, `thumbnail_url`. `priority` outside 1–10 → **400** before the database sees it. |
| `PUT` | `/api/v1/personalities/<uuid>` | Same allow-list. `slug` is editable but a collision is still 409. Changing `aliases` returns `{"rescan_recommended": true}` so the UI can offer the preview in §4.4. |
| `POST` | `/api/v1/personalities/<uuid>/toggle` | Flips `is_monitored`. Mirrors `/channels/<id>/toggle`. |
| `DELETE` | `/api/v1/personalities/<uuid>` | Cascades to appearances, **including confirmed ones**. Without `?confirm=true` it performs nothing and returns **409** with `{"appearance_count": N, "confirmed_count": M, "message": "..."}`. The UI shows those numbers and requires a second click. This is the deletion-protocol shape: inventory first, explicit confirmation second. |
| `GET` | `/api/v1/personalities/stats` | `{total, monitored, by_domain: [...], total_appearances, unconfirmed_appearances}`. Mirrors `/channels/stats` so the list page's domain filter is populated by the same code path the channels page already uses. |

### 4.2 Reading appearances

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/v1/personalities/<uuid>/appearances` | Filters `status`, `role`, `min_confidence`, `channel_id`. `sort` ∈ `published`\|`confidence`\|`created`, default `published desc`. Paginated. Joins `pipeline_items` and `channels` so each row carries `youtube_video_id`, `title`, `youtube_url`, `published_at`, `channel_id`, `channel_name` — the detail table renders from one call. |
| `GET` | `/api/v1/appearances?video_id=<uuid>` | Everyone in one video. This is what a future Inbox row calls to draw its badges. Also accepts `youtube_video_id=`. |

### 4.3 Writing appearances by hand

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/v1/personalities/<uuid>/appearances` | Body: `{video_id}` or `{youtube_video_id}` or `{url}` (any YouTube URL shape — reuse `extract_video_id` from `src/transcript-service/single_video.py` rather than writing a second parser), plus `role`. Writes `source='manual'`, `confidence=1.00`, `status='confirmed'`, `confirmed_by` from the request. **If the video is not in `pipeline_items`, this returns 404 with a pointer to Enroll Video, and does not create anything.** That refusal is load-bearing: inventing a register row from here is precisely how a fifth store starts. If a `suggested` row already exists for the pair, it is **upgraded in place** to confirmed and the response says `{"action": "confirmed_existing"}` — not a 409, because the user's intent is unambiguous. |
| `POST` | `/api/v1/appearances/<uuid>/confirm` | `status='confirmed'`, stamps `confirmed_at`/`confirmed_by`. |
| `POST` | `/api/v1/appearances/<uuid>/reject` | `status='rejected'`. The row stays as a tombstone. |
| `DELETE` | `/api/v1/appearances/<uuid>` | Behaviour depends on origin, and the response says which happened: a machine-made row (`source != 'manual'`) becomes `rejected` and returns `{"action": "rejected"}`; a hand-made row is genuinely removed and returns `{"action": "deleted"}`. Deleting a machine row outright would let the next rescan bring it straight back, which reads to the user as the delete button not working. |

### 4.4 Running the matcher

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/v1/personalities/<uuid>/rescan` | Matches this one person against every video in the register. **`dry_run` defaults to `true`** and returns `{would_create, would_promote, unchanged, suppressed_by_rejection, samples: [...20 matched titles with the matched_text and score...]}` without writing anything. `dry_run=false` writes. The preview is the main defence against a bad alias: adding `"Chris"` to a personality and seeing 340 matches with sample titles is a decision Matt can make in five seconds, and it is unrecoverable-by-hand if it writes first. |
| `POST` | `/api/v1/personalities/rescan-all` | Whole corpus, all monitored personalities. Same `dry_run` semantics. Body accepts `limit` and `since`. Long-running — the UI calls it with a limit; the full sweep is the script in §7. |

No endpoint here calls anything outside the 10.0.0.x network, so the project's mandatory
2-second external-API delay does not apply to any of them. The matcher reads columns already
stored in Postgres. This is stated explicitly because "it touches YouTube data" invites the
wrong assumption.

---

## 5. The pages

Both pages extend `templates/base.html` and use **only classes that already exist there**:
`.panel`, `.panel-header`, `.panel-title`, `.card`, `.card-title`, `.card-value`, `.card-sub`,
`.grid`, `.badge`, `.badge-active` / `.badge-inactive`, `.topic-tag`, `.btn` / `.btn-sm` /
`.btn-secondary` / `.btn-outline` / `.btn-danger` / `.btn-success`, `.form-input`, `.form-select`,
`.form-label`, `.form-group`, `.thumbnail` / `.thumbnail-sm`, `.channel-row`, `.channel-info`,
`.channel-name`, `.channel-handle`, `.breadcrumb`, `.status-healthy` / `.status-warning` /
`.status-error`, `.empty-state`, `.loading`, `.spinner`, `.flex` utilities, `.two-col`.

**No new stylesheet, no new class, no new colour token.** Where an inline colour is genuinely
unavoidable it is written `rgb(...)` / `rgba(...)` — never hex, never `oklch` — matching the
newer inline styles in `channels.html` (e.g. `rgb(148,163,184)` in the preview block). The
existing hex values already in `base.html` are left alone; this feature does not add more.

Two additions to `base.html`: a `Personalities` link in the tier-2 nav between `Channels` and
`Pipeline`, and a `+ Add Personality` action link alongside the existing `+ Add Channel`.

### 5.1 `/personalities` — the list

**Header row** (same shape as `channels.html` line 5–23): `<h1>Personalities</h1>` on the left;
on the right, `Add Personality` button, a domain `<select>`, a role/status `<select>`
(`All` / `Has unconfirmed matches` / `Owns a channel` / `No appearances yet`), and a search
`<input>` with the same 300 ms debounce.

**Table** — dense, one line per person, sortable by clicking any `<th>`:

| Column | Content |
|---|---|
| Personality | `.channel-row` — thumbnail + **name as a real `<a href>`** + alias count beneath in `.channel-handle` |
| Owns channel | `<a>` to `/channels/<uuid>`, or `—` |
| Domain | `.topic-tag` |
| Priority | The number, coloured with the existing status classes: 8–10 `.status-healthy`, 4–7 `.status-warning`, 1–3 `.status-error` (Matt's red/green performance-colour preference, using classes that already exist) |
| Appearances | `12 confirmed · 4 to review`, the second half in `.status-warning` when non-zero |
| Last seen | Date of the newest appearance's `published_at`, or `never` |
| Monitored | `.badge-active` / `.badge-inactive` |
| Actions | `Pause`/`Resume` button + `View` link |

**Real URLs — the point where `channels.html` is currently wrong.** That page sets
`tr.onclick = ... window.location.href` (line 126), so right-click → Open in new tab does
nothing on 90% of the row. Matt's design rule #3 requires a real link. Here the name cell is a
genuine `<a href="{{ url_prefix }}/personalities/<slug>">`; the row `onclick` stays as a
convenience on top of it, not instead of it.

Filter and sort state goes in the query string — `/personalities?domain=business&sort=appearances&dir=desc`
— so a filtered view is a URL Matt can bookmark or paste, and a page reload does not lose it.

**Add Personality modal**, same construction as the Add Channel modal: name, aliases (one per
line), domain (the existing tag-button + free-text control from `channels.html`, so the domain
vocabulary stays shared with channels), priority (1–10 select), "Owns one of our channels"
searchable select over `GET /api/v1/channels`, monitored checkbox, notes. On submit it creates
the personality, then immediately calls `rescan` in dry-run mode and shows the preview panel
("Elon Musk would match **47** videos we already hold — 12 as a guest, 35 mentioned. Sample:
…") with **Create matches** / **Adjust aliases** buttons. Nothing is written to `appearances`
until that button is pressed.

### 5.2 `/personalities/<slug>` — the detail page

Breadcrumb `Dashboard / Personalities / <name>`, then a header block mirroring
`channel_detail.html`: thumbnail, name, aliases rendered as `.topic-tag`s, a link to the owned
channel when there is one, and the monitored badge.

**Four `.card`s across the top**, following the labelling discipline that page established
(each card says where its number comes from, because a queue number was once read as an
inventory):

| Card | Value | Sub |
|---|---|---|
| Confirmed | count | appearances you have checked |
| To review | count, `.status-warning` when > 0 | detected, waiting on you |
| As a guest | count | the ones worth watching |
| Last seen | date | newest video they appear in |

**Left column — Appearances.** A `.panel` with filter chips (`All` / `To review` / `Confirmed` /
`Guest` / `Mentioned`) and a dense table: Video (thumbnail + title, a real `<a>` to the existing
`/videos/<youtube_video_id>` route), Channel (a real `<a>` to `/channels/<uuid>`), Published,
Role badge, Confidence rendered as a percentage, **Why** (the stored `matched_text`, truncated
with the full string in a `title=`), Source, and per-row `Confirm` / `Reject` buttons on
unconfirmed rows. Sortable by Published and Confidence; paginated at 50.

The "Why" column is the one that makes the review loop fast. A row reading
`"…this episode is brought to you by …"` is dismissible without opening the video.

**Right column — three panels.**

1. **Settings** — name, slug (editable, warns that existing links break), aliases textarea,
   domain tags, priority, monitored toggle, notes, thumbnail URL, owned-channel picker.
   Saving after an alias change offers **Preview matches** before **Rescan now**.
2. **Add an appearance by hand** — a YouTube URL or video id plus a role select. If the video
   is not in the library, the error names that and links to the existing Enroll Video flow
   rather than pretending to succeed.
3. **Info** — created, last updated, last scanned, matcher version, and a plain-English line
   for the deferred capability: *"We only spot this person in videos we already hold. Searching
   YouTube for them by name is not built yet."* Stating the boundary on the page is what stops
   the guide-v1.0.0 failure in MISTAKES.md #2, where a design intention was published as
   shipped reality.

### 5.3 Slug in the page URL, uuid in the API

`/channels/<uuid>` is the existing convention and this deviates from it deliberately: a
personality page is a URL Matt will paste to himself and keep, and `/personalities/elon-musk`
survives a database rebuild and reads correctly in a bookmark bar, where a uuid does neither.
The API stays uuid-keyed like everything else; the page resolves via
`GET /api/v1/personalities/by-slug/<slug>`.

---

## 6. The matcher

New module `src/admin/matching/appearances.py`. **Pure and I/O-free**, in the same spirit as
`api/categories.py`: it takes a video's title, description and channel id, plus the list of
personalities, and returns proposed appearance rows. All database work lives in the caller.
That is what makes the rule table testable without a database — and the rules are the part most
likely to need correcting after Matt sees real output.

`MATCHER_VERSION = 1` is a module constant, bumped whenever a rule changes.

### 6.1 Normalising before matching

Both sides — the text and every alias — go through the same normalisation: Unicode NFKD, strip
combining marks (so `Beyoncé` and `Beyonce` are one thing), casefold, collapse whitespace,
and normalise the quote characters YouTube titles are full of (`’` → `'`).

Matching is **word-boundary only**, never substring. `Tim` must not match inside `Timothy`, and
`Ben` must not match inside `Benjamin`. A trailing possessive is allowed (`Elon Musk's`), as is
surrounding punctuation (`(Elon Musk)`, `| Elon Musk |`). An `@handle` alias matches only with
its `@` present, so `@elonmusk` does not fire on the word `elonmusk` inside a URL slug.

### 6.2 Cleaning the text before matching — two subtractions that matter

**Channel boilerplate.** Nearly every channel appends the same footer to every description:
subscribe links, social handles, a standing "Follow Lex: twitter.com/lexfridman". Matched
naively, that footer produces one appearance row per upload, forever. So: for each channel,
compute the longest common suffix and prefix shared by a sample of its recent descriptions
(20 is plenty), and strip it before matching. Text that appears on essentially every video of a
channel is boilerplate, not news.

**Sponsor reads.** Descriptions carry large sponsor blocks, and sponsor blocks name people.
Any window of text within 200 characters of `sponsor`, `sponsored by`, `brought to you by`,
`promo code`, `use code`, `% off`, `affiliate`, `this episode is supported by` is marked as a
sponsor region. A name found only inside a sponsor region **produces no row at all** — not a
low-confidence row, none. A sponsor read is not weak evidence of an appearance; it is evidence
of an advertisement.

### 6.3 The rules, and what each is worth

Applied in order; a video/personality pair keeps its **highest-scoring** signal.

| # | Signal | `source` | Role | Confidence |
|---|---|---|---|---|
| 1 | `personalities.channel_id` equals the video's `channel_id` | `channel-owner` | `host` | 0.98 |
| 2 | Full name in the title, immediately after a **guest marker**: `w/`, `with`, `ft.`, `ft`, `feat.`, `featuring`, `guest:`, `joins`, `sits down with`, `interview with`, `in conversation with`, `Ep. N —` | `title-pattern` | `guest` | 0.90 |
| 3 | Full name in the title with **no** marker and **no** distancing marker | `title-pattern` | `mentioned` | 0.60 |
| 4 | Full name in the title with a **distancing marker**: `reacting to`, `reaction`, `responds to`, `response to`, `debunking`, `destroys`, `exposes`, `my thoughts on`, `why … is wrong`, `explains why` | `title-pattern` | `mentioned` | 0.55 |
| 5 | Full name in a **guest-bio region** of the description: within 150 chars of `guest:`, `today's guest`, `follow <name>`, `<name> is the`, `<name>'s links`, `about <name>` | `description` | `guest` | 0.70 |
| 6 | Full name in the description body, outside boilerplate and sponsor regions | `description` | `mentioned` | 0.45 |
| 7 | A **single-token** alias anywhere, having passed the rare-token gate (§6.5) | as found | `mentioned` | 0.40 max |
| 8 | Any match falling inside a sponsor region or channel boilerplate | — | — | **no row** |

**Rule 1 is the only way `host` is ever assigned.** No text pattern produces `host`. "Hosted by
Elon Musk" in a description is Rule 6. Ownership of the channel is a fact we hold; who hosted a
given episode is a guess, and the two must not be recorded the same way.

**Corroboration.** If two independent signals both score ≥ 0.45 for the same pair, the final
confidence is `best + 0.10`, capped at **0.95**, and `signal_count` records how many. The cap
exists so that only a human ever reaches 1.00 — a machine-derived certainty and a checked fact
must not be the same number.

**Thresholds.**

| Band | What happens |
|---|---|
| **< 0.45** | Nothing is written. The pair is not an appearance and not a to-do. |
| **0.45 – 0.74** | Row written as `suggested`. Shows under "To review". Ranks at the discounted weight. |
| **≥ 0.75** | Row written as `suggested`, shown first in "To review", ranks at the discounted weight. |
| **Never** | The matcher writes `confirmed`. Only a human does. |

The bands mean 0.75 is a *sort order and a display grouping*, not a licence to skip the human.
Given ~5,000 videos, most rows will never be reviewed, which is fine — a discounted suggested
row already does the Inbox-ranking job Matt asked for.

### 6.4 Writing the results — the upsert

```sql
INSERT INTO appearances (personality_id, video_id, youtube_video_id, role,
                         confidence, source, matched_text, signal_count,
                         matcher_version, status)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'suggested')
ON CONFLICT (personality_id, video_id) DO UPDATE
SET role         = CASE
                     WHEN appearances.role = 'host' THEN 'host'
                     WHEN EXCLUDED.role  = 'host' THEN 'host'
                     WHEN appearances.role = 'guest' OR EXCLUDED.role = 'guest' THEN 'guest'
                     ELSE 'mentioned'
                   END,
    confidence      = GREATEST(appearances.confidence, EXCLUDED.confidence),
    source          = CASE WHEN EXCLUDED.confidence > appearances.confidence
                           THEN EXCLUDED.source ELSE appearances.source END,
    matched_text    = CASE WHEN EXCLUDED.confidence > appearances.confidence
                           THEN EXCLUDED.matched_text ELSE appearances.matched_text END,
    signal_count    = GREATEST(appearances.signal_count, EXCLUDED.signal_count),
    matcher_version = EXCLUDED.matcher_version
WHERE appearances.status = 'suggested';
```

The `WHERE appearances.status = 'suggested'` on the update is the whole safety property: a
`confirmed` row and a `rejected` tombstone are both untouched by any number of rescans. Role
only ever climbs the ladder. Confidence only ever climbs.

### 6.5 The false-positive problem, concretely

This is the part that decides whether the feature is useful or noise, so it gets its own rules
rather than a hand-wave.

**Common first names.** "Elon" is safe because almost nobody else is called Elon. "Chris",
"John", "Mike", "Sarah", "Dave", "Tom" are not — a single-token alias like that will match
hundreds of unrelated videos. Rule: a **single-token alias** is admitted only if it passes a
rare-token gate — at least 5 characters, not present in a bundled list of the ~300 most common
English given names, and not an ordinary English word. If it fails the gate the alias is still
stored, but it can never score above 0.40 on its own and therefore never crosses the 0.45 write
threshold without a second corroborating signal. Multi-token names (`Elon Musk`) skip the gate
entirely; two tokens is most of the discriminating power.

The gate is also surfaced in the UI: adding `Chris` shows *"Single first names match a lot of
unrelated videos — this alias will only count when something else also points at this person."*

**A name in a sponsor read.** Handled by subtraction, §6.2 — no row at all. This is the single
biggest source of description false positives.

**A name in the channel's standing footer.** Handled by boilerplate stripping, §6.2. Without
it, one "Follow Lex" line in a footer produces an appearance on every video that channel has
ever published.

**"with" vs "featuring" vs a passing reference.** Rules 2, 5 and 6 are the answer, and the gap
between them is deliberate: `w/` and `featuring` in a *title* are strong (0.90) because a title
is short and every word in it was chosen. The same name in the description body is weak (0.45)
because descriptions are long and full of links, timestamps, back-catalogue plugs and reading
lists. A name in the title *without* a marker (Rule 3, 0.60) is genuinely ambiguous —
"Elon Musk's new Tesla" is about him, not with him — so it lands as `mentioned` and gets
promoted to `guest` only if the description independently agrees.

**Reaction and commentary videos.** Rule 4. "Reacting to Elon Musk's announcement" is a title
where the person is the *subject* and definitively not present. Left unhandled, commentary
channels would produce a stream of high-confidence phantom guest spots.

**Two people, one name.** Not solved, and deliberately so. If two tracked personalities ever
share a name or alias, the alias-collision check (the GIN index in §3.1) refuses the second one
at creation time with a 409 naming the existing holder. Disambiguation by context is a real
problem and a later one; refusing the ambiguity is honest and costs nothing today.

### 6.6 When it runs

Three triggers, all reading the same work queue predicate:

```sql
WHERE appearances_scanned_at IS NULL
   OR appearances_matcher_version < <MATCHER_VERSION>
```

1. **On ingest** — after a `pipeline_items` row reaches a terminal indexed state, scan it. One
   video, a few milliseconds, no external calls.
2. **On demand** — the rescan endpoints in §4.4, for one personality or all.
3. **On a sweep** — a small periodic pass over unscanned rows, so a video that landed while the
   matcher was down is picked up without anyone noticing it was missed. This is the property
   MISTAKES.md #1 was about: the thing that must never happen is silence that looks like
   success. The sweep's last-run time and backlog count go on the existing
   `GET /api/v1/status` document so a stalled matcher is visible where every other stall
   already is.

---

## 7. Backfill

**What has to be scanned.** The register holds ~1,150 rows today and is expected to hold
~5,400 once the register-of-record conversion lands. Every one of them needs a first scan.

**Script:** `scripts/backfill_appearances.py`, modelled on `scripts/backfill_embeddings.py`,
which the codebase already describes as *"resumable BY CONSTRUCTION (its work queue is the DB
predicate `embedding = NONE`)"*. Same property here — the queue is the predicate in §6.6, so
the script can be killed and restarted at any point with no checkpoint file and no double work.

Flags: `--dry-run` (default), `--limit N`, `--personality <slug>`, `--page-size 500`,
`--since <date>`. Output: created / promoted / unchanged / suppressed-by-tombstone /
skipped-no-description, plus a per-personality breakdown and 20 sample matches.

**What it costs.**

- **Zero external API calls.** Titles and descriptions are already columns in Postgres. The
  project's mandatory 2-second inter-call delay governs calls leaving the 10.0.0.x network and
  does not apply. There is no YouTube traffic, no rate-limit exposure, and no risk of
  re-triggering the IP block that hit this network on 2026-08-13.
- **Zero spend.** No LLM is involved. The `llm` value in `appearances.source` is reserved for a
  possible later pass and is unused by this design.
- **Runtime:** ~11 pages of 500 rows, one SELECT and one batched INSERT per page, with pure
  Python regex work in between over short strings. Expect low single-digit minutes. That is an
  estimate from the shape of the work, not a measurement — the honest number comes out of the
  first `--dry-run`, and the implementing session should record it rather than inheriting this
  sentence.
- **Memory:** flat. Personalities (dozens) load once; videos stream a page at a time.

**A real limitation to state up front.** Many existing rows have no description: GAPS.md #7 and
issue #27 both record that metadata fetching failed silently for a stretch, and issue #45 has
all 4,458 videos carrying an empty uploader. Those rows can only be matched on their titles, so
the backfill will under-detect on the older corpus. This is not a reason to wait — it is the
reason `appearances_matcher_version` exists. When issue #27's description backfill lands, bump
the version and the whole corpus re-scans on the same predicate, at the same cost, without
touching a single human decision. The backfill report counts `skipped-no-description` explicitly
so the size of that shortfall is a visible number rather than an invisible absence.

**Nothing in the backfill auto-confirms.** Every row it writes is `suggested`. The dry run tells
Matt how many rows a real run would create *before* any of them exist.

---

## 8. Testing

Two files. Failure cases first — the happy path is the easy part and it is not where this
feature will break.

### 8.1 `tests/python/test_appearance_matcher.py` — pure, no I/O

Matches the shape of `tests/python/test_categories.py`: the matcher is the piece most likely to
need correcting after Matt sees real output, and it must be correctable without a database.

**Failure cases**

1. `test_common_first_name_alone_never_crosses_the_write_threshold` — alias `Chris` against
   `"Chris explains the market"` scores ≤ 0.40 and produces no row.
2. `test_single_token_alias_can_cross_only_with_corroboration` — `Elon` in the title plus a
   guest-bio hit in the description reaches the threshold; either alone does not.
3. `test_sponsor_read_produces_no_appearance` — `"…brought to you by AG1. Use code ELON for 20% off"`
   yields nothing, not a low-confidence row.
4. `test_channel_boilerplate_footer_is_stripped_before_matching` — a `"Follow Lex Fridman"`
   footer shared by 20 descriptions matches on none of them, while a genuine in-body mention on
   a different channel still matches.
5. `test_reaction_title_is_mentioned_not_guest` — `"Reacting to Elon Musk's Tesla announcement"`
   → `mentioned`, never `guest`.
6. `test_about_title_is_mentioned_not_guest` — `"Why Elon Musk is wrong about AI"`.
7. `test_substring_of_a_longer_name_does_not_match` — alias `Tim` against `"Timothy Ferriss"`,
   alias `Ben` against `"Benjamin Netanyahu"`: zero matches.
8. `test_possessive_and_punctuation_forms_still_match` — `Elon Musk's`, `(Elon Musk)`,
   `| ELON MUSK |`, `Elon Musk:`.
9. `test_accents_and_smart_quotes_are_normalised` — `Beyoncé`/`Beyonce`, `’`/`'`.
10. `test_handle_alias_requires_the_at_sign` — `@elonmusk` does not fire on a bare `elonmusk`
    inside a URL.
11. `test_host_is_only_ever_assigned_from_channel_ownership` — `"Hosted by Elon Musk"` in a
    description never yields `host`.
12. `test_corroboration_adds_ten_points_and_caps_at_0_95` — the machine never reaches 1.00.
13. `test_role_ladder_promotes_and_never_demotes` — `mentioned` then `guest` ends at `guest`;
    `guest` then `mentioned` stays `guest`.
14. `test_null_description_yields_title_only_evidence` — no crash, and the result is flagged as
    description-less so the backfill can count it (the issue #27 interaction).

**Happy path**

15. `test_guest_marker_in_title_scores_0_90_as_guest` — `"Ep. 400 — w/ Elon Musk"`.
16. `test_channel_owner_is_host_at_0_98_on_their_own_upload`.
17. `test_guest_bio_block_in_description_scores_0_70`.

### 8.2 `tests/python/test_personalities_api.py` — route level

Same construction as `tests/python/test_search_route_admin.py`: a bare Flask app with the
blueprint registered and the cursor faked. These test the *contract*, not the SQL.

**Failure cases**

18. `test_manual_appearance_for_an_unknown_video_is_404_and_writes_nothing` — the no-fifth-store
    guarantee. The most important test in the file.
19. `test_duplicate_slug_is_409_with_the_existing_id` — never a silently suffixed slug.
20. `test_duplicate_alias_across_personalities_is_409_naming_the_holder`.
21. `test_priority_outside_1_to_10_is_400_before_the_database`.
22. `test_confidence_outside_0_to_1_is_rejected`.
23. `test_delete_of_a_suggested_appearance_leaves_a_rejected_tombstone` and returns
    `{"action": "rejected"}`.
24. `test_delete_of_a_manual_appearance_removes_the_row` and returns `{"action": "deleted"}`.
25. `test_personality_delete_without_confirm_is_409_and_reports_both_counts`.
26. `test_rescan_defaults_to_dry_run_and_writes_nothing`.
27. `test_manual_add_upgrades_an_existing_suggestion_rather_than_409`.

**Happy path**

28. `test_list_returns_appearance_counts_without_a_second_call`.
29. `test_appearances_are_returned_newest_published_first`.

### 8.3 `tests/python/test_appearance_rescan.py` — the re-run guarantees

30. `test_rejected_pair_is_never_recreated_by_a_rescan` — the tombstone holds.
31. `test_confirmed_row_survives_a_matcher_version_bump` — human judgment is never re-derived.
32. `test_rescan_is_idempotent` — running twice at the same matcher version changes nothing.
33. `test_backfill_resumes_from_the_scan_predicate` — kill after page 2, restart, no double work
    and no skipped rows.

### 8.4 Two tests that need a real Postgres — and are not optional

MISTAKES.md #7 is exactly this failure: the video-tags feature shipped with green unit tests and
the first live write was rejected, because the tests mocked the datastore and could not see a
schema-enforced rejection. The prevention rule adopted then was that a change writing a new
field ships with its schema definition in the same unit of work **and the live write is verified
end to end before the feature is called done.**

34. `test_migration_005_is_idempotent` — apply `005` twice to a scratch database; the second run
    changes nothing and errors on nothing.
35. `test_first_live_appearance_write_round_trips` — insert one personality and one appearance
    against a real Postgres, read them back, exercise the §6.4 upsert twice, and assert the
    `CHECK` constraints actually reject `priority = 11`, `confidence = 87`, and
    `role = 'cohost'`.

These are marked `@pytest.mark.integration` and skipped when no database is reachable — **but a
skipped test is not a passed test.** The implementing session runs both against Banner before
calling the work done, and says so.

---

## 9. Explicitly not in this release

- **Active YouTube search by name.** Searching YouTube for "Elon Musk interview" and enrolling
  what comes back. Deferred by Matt's instruction. It is a different feature with different
  costs: it makes external calls (so the 2-second rule and the anti-bot surface that IP-blocked
  this network on 2026-08-13 both apply), it needs a relevance filter far stricter than this
  one, and it can enrol content from channels nobody vetted. The schema here supports it with
  no change — such an appearance would simply be `source='manual'` or a new source value on a
  video enrolled through the existing single-video path.
- **LLM-assisted role classification.** `source='llm'` is reserved in the CHECK constraint and
  unused. Worth revisiting only after Matt has seen how the text rules actually perform, and it
  would need the buy-vs-build conversation about cost per video across ~5,400 rows.
- **Transcript-body matching.** Only title and description are read. Transcripts would find
  every passing name-drop in a two-hour podcast, which is a different and much noisier question.
- **Giving the `guest_monitor` ingestion mode meaning.** That enum value exists in
  `001_pipeline_schema.sql` and currently means "never ingest" — `src/transcript-service/channel_source.py:20`
  excludes those channels from discovery entirely. This feature is the prerequisite for making
  it mean what it says, but wiring it is separate work.
- **Building the review Inbox page itself.** No such page exists today; the nearest live thing
  is `pipeline_items` in `discovered` status, listed by
  `GET /api/v1/pipeline/items?status=discovered` and shown on the channel detail page. This
  design adds the ranking signal (`video_appearance_rank`), one new `sort=personality` option on
  that existing endpoint, and a `personalities` array on each item in the response. The default
  ordering is unchanged, so nothing existing shifts. Whenever the Inbox is built, it sorts
  correctly for free.

---

## 10. Open questions for Matt

**1. Should a person's own channel uploads create appearance rows at all?**
Lex Fridman owns a channel we follow, so every one of his ~800 uploads would get a `host` row.
That is a lot of rows that tell you nothing new.
*Recommendation: yes, create them, but weighted at 0.2 in the ranking (as specified in §3.1).*
The rows are what makes "show me everything we hold for this person" answerable in one query,
and the low weight stops them from burying a genuine guest spot elsewhere. **Say no and I drop
Rule 1 entirely — the channel link alone then answers the "everything we hold" question.**

**2. Starting confidence thresholds: write at 0.45, prioritise at 0.75.**
These are judgement calls, not measurements.
*Recommendation: accept them as a starting point and tune after the first dry run, which
reports how many rows each band would produce before anything is written.* Changing them later
costs one constant and one rescan.

**3. What does "Reject" mean — this video, or this person on this channel?**
If Matt rejects the same false positive twenty times on one commentary channel, a per-video
tombstone is tedious.
*Recommendation: per-video only for now.* It is the honest meaning of the button, and a
per-channel mute is cheap to add later once we can see whether the tedium is real.

**4. Which personalities go in first?**
*Recommendation: seed the owner of each of the 52 tracked channels (so every channel has a named
person behind it), plus a list Matt dictates of people we track but do not follow — Elon Musk
being the stated example.* The seed script writes personalities only; appearances come from the
§7 dry run so Matt sees the volume before committing.

**5. Should detecting a tracked person on a followed channel change anything about ingestion?**
Today it changes ranking only. It could also, for example, promote a `discovered` video straight
to `queued`.
*Recommendation: no, not in this release.* Detection reads title and description, both of which
are only available after a video is already in the register — so nothing new gets ingested
either way, and letting a text heuristic auto-queue work is a bigger change than it looks.

---

## 11. Build order

1. Migration `005`, applied to Banner, verified idempotent and verified rejecting bad values
   (tests 34 and 35). **This is the gate** — MISTAKES.md #7 says a schema change and its live
   write land together or the feature is not done.
2. The matcher module and its pure tests (§8.1). No database, no UI, fastest feedback.
3. The API blueprint and its route tests (§8.2, §8.3), plus the `/api/v1` index entry and the
   consumer-guide section in the same commit.
4. The two pages, plus the two `base.html` nav links.
5. Seed personalities, run the backfill `--dry-run`, show Matt the numbers, then run it for real.
6. `sort=personality` on `GET /api/v1/pipeline/items` and the `personalities` array on its rows.
7. Regenerate `ROADMAP.md` with `python3 scripts/roadmap-sync.py` in the same commit as the
   issue that tracks this work.
