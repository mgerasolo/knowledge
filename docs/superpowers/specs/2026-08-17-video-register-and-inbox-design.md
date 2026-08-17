# Video Register + Review Inbox — Design

**Date:** 2026-08-17
**Status:** awaiting Matt's review
**Anchor:** a review Inbox for hand-picked channels, landing on a single register of record instead of a fifth private store.

---

## 1. The problem

Matt asked for an Inbox: one ongoing queue of new videos on channels we follow but do not
auto-ingest, so that a channel like Lex Fridman's can be curated rather than swallowed
whole. Building that page on the current plumbing would have produced a page that looks
correct and ingests nothing.

Measured on the live system, 2026-08-17. Four stores, four answers to "how many videos do
we have":

| Store | Count | How it was read |
|---|---|---|
| Transcript files on the share | 5,393 files across 61 channel folders | `find /mnt/foundry_resources/transcripts -type f \| wc -l` |
| SurrealDB — what search reads | 5,337 videos / 405,090 segments | `SELECT count() FROM video GROUP ALL` via knowledge-embedding |
| `video_list.json` inside the transcript service | 5,955 known / 5,252 fetched | read from `Config.STATE_DIR` in knowledge-transcript-service |
| Postgres `pipeline_items` — what Enroll shows | 1,150 rows | `SELECT status, count(*)` in knowledge-postgres |

Supporting facts, all verified the same day:

- **The queue the worker drains is the JSON file, not the database.**
  `fetcher.get_pending()` filters `video_list.json`; `claim_pipeline_item()` exists in
  `src/db/schema/001_pipeline_schema.sql` and has zero callers anywhere in `src/`,
  `scripts/` or `deploy/`.
- **So Enroll's ingest and skip buttons write to a store nothing reads.** Only 1 row in
  `pipeline_items` moved in the seven days to 2026-08-17.
- **No channel is in hand-pick mode.** 52 channels, all active: 51 `new_only`, 1 `all`,
  0 `selected`. Nothing is waiting for review today because nothing can be.
- **The repo's schema no longer matches the live database.** Live `pipeline_status`
  carries `skipped`, `segmenting`, `transcribed`, `indexed_speakr`, `indexed_surreal`;
  the repo's schema file has none of them.
- **`pipeline_items` has no `updated_at` column.** `api/channels.py` line 778 sets it,
  so the channel-page Skip button raises. The Pipeline page's Skip does not set it and
  works. This is the failure mode in miniature.

**The pattern, which matters more than any single defect:** every feature was built with
its own store and its own writer. Fetching owns files, search owns the index, the web app
owns the database. Each is internally correct; none is responsible for the whole, so no
component can answer "is this video actually done?" — only "is it done in my copy?" Every
significant failure this project has had is that shape: the pipeline running empty for two
weeks while health checks reported healthy, semantic search believed shipped but stubbed
(GAPS #1), the docs naming a vector database that was never deployed (GAPS #3), metadata
written null by one ingest path and not the other (GAPS #7).

## 2. Decisions already taken

Matt, 2026-08-16 and 2026-08-17:

| Decision | Choice |
|---|---|
| How picking a video actually ingests it | One queue in the database |
| What counts as "new since last audit" | Per-video: undecided until acted on, plus a "skip everything remaining" |
| The Inbox shape | One list across all hand-picked channels, not per channel |
| Ranking | Higher-probability items in their own section at the top |
| Guest and domain extraction | As soon as possible — parse title and description, mark each name guest or topic per how the text describes it |
| Sequencing | Do the unification work this build needs; file issues for the rest |
| Personalities page | Designed in parallel by another session |
| Reaching beyond followed channels | Passive now; active YouTube search deferred |

## 3. Scope of THIS build

**In:** the register (§4), the import (§5), the worker cutover (§6), the reconciliation
check (§7), the Inbox page (§8).

**Out, each with an issue filed:** guest and domain extraction · personalities and
appearances · active YouTube search by name · rebuilding the search index from transcript
files · the wider repo-vs-live schema drift beyond the columns this build touches.

**Deliberately included even though it is not the Inbox:** the `updated_at` column and the
schema-drift correction for `pipeline_status`. Both are inside the table this build makes
authoritative; leaving them would mean shipping a register with a known-broken write path.

## 4. The register

`pipeline_items` becomes the register of record: one row per video, every service reading
and writing it. The name stays — renaming a live table adds risk this build does not need
— but the comment on the table is updated to say what it now is.

`src/db/schema/004_video_register.sql`, additive and idempotent, in the style of 002/003:

```sql
-- The repo's schema drifted from the live database: these five statuses exist on
-- Banner and in no schema file, so anyone reading the repo to understand the
-- system gets it wrong. Idempotent, so this is safe against the live database.
-- ALTER TYPE ... ADD VALUE cannot run inside a transaction block; apply this
-- file with autocommit, as 002 already required.
ALTER TYPE pipeline_status ADD VALUE IF NOT EXISTS 'skipped';
ALTER TYPE pipeline_status ADD VALUE IF NOT EXISTS 'segmenting';
ALTER TYPE pipeline_status ADD VALUE IF NOT EXISTS 'transcribed';
ALTER TYPE pipeline_status ADD VALUE IF NOT EXISTS 'indexed_speakr';
ALTER TYPE pipeline_status ADD VALUE IF NOT EXISTS 'indexed_surreal';

-- api/channels.py has been writing this column since #76. It does not exist, so
-- the channel-page Skip button has been raising for as long as it has shipped.
ALTER TABLE pipeline_items ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE TRIGGER pipeline_items_updated_at
    BEFORE UPDATE ON pipeline_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Who decided, and when. Distinct from discovered_at (when we found it) and
-- queued_at (when work began): a human's decision is its own fact, and without
-- it "why is this not in the inbox any more" has no answer.
ALTER TABLE pipeline_items ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
ALTER TABLE pipeline_items ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(100);

-- How this row got here. 'import' exists so the one-time migration from
-- video_list.json is distinguishable forever from what discovery found.
ALTER TABLE pipeline_items ADD COLUMN IF NOT EXISTS source VARCHAR(30);

-- Per-video domain. The channel already has one; a channel like Lex Fridman's
-- spans several, which is the entire reason this build exists. Filled by the
-- extraction build; nullable until then, and never silently defaulted to the
-- channel's, because a guessed domain is worse than a blank one.
ALTER TABLE pipeline_items ADD COLUMN IF NOT EXISTS domain VARCHAR(50);

-- The RSS feed already carries these; they cost no extra request and they are
-- what makes an inbox row judgeable at a glance.
ALTER TABLE pipeline_items ADD COLUMN IF NOT EXISTS view_count BIGINT;
ALTER TABLE pipeline_items ADD COLUMN IF NOT EXISTS like_count BIGINT;

-- video | live | short. Channels carry include_videos/lives/shorts flags, so the
-- kind must be on the row for those flags to mean anything after discovery.
ALTER TABLE pipeline_items ADD COLUMN IF NOT EXISTS content_kind VARCHAR(10);

-- The link from the register to the artifact on the share. Without it, "does
-- this row have a transcript" is a filesystem guess from a title.
ALTER TABLE pipeline_items ADD COLUMN IF NOT EXISTS transcript_path TEXT;

-- The inbox's only hot query: discovered rows, newest first.
CREATE INDEX IF NOT EXISTS idx_pipeline_inbox
    ON pipeline_items (status, published_at DESC)
    WHERE status = 'discovered';

COMMENT ON TABLE pipeline_items IS
    'The video register of record: one row per video, every service reads and '
    'writes here. Superseded video_list.json 2026-08-17.';
```

## 5. The import

`scripts/import_video_list_to_register.py`. Reads `video_list.json` and
`fetch_state.json` from the transcript service and upserts every entry into the register.

**Status mapping**, from the file's own records:

| In the file | Register status |
|---|---|
| `fetch_state.fetched` AND a SurrealDB record exists | `indexed_surreal` |
| `fetch_state.fetched` AND no SurrealDB record | `transcribed` |
| `fetch_state.failed` | `failed` |
| `fetch_state.skipped` | `skipped` |
| `pipeline_status: "discovered"` | `discovered` |
| anything else, including no status | `queued` |

**Rules:**

- **Keyed on `youtube_video_id`**, which already carries a unique constraint, so the
  import is an upsert and re-running it changes nothing.
- **The file wins on lifecycle status**, because it is the copy that has actually been
  running. One exception: a row already at `indexed_surreal` in Postgres is never moved
  backwards, since that is a stronger claim than the file can make.
- **`channel_id` resolved by matching the entry's `channel_handle` to
  `channels.youtube_handle`.** Unmatched leaves it null, which the column has allowed
  since 002 — a video whose channel we no longer follow is still a real video.
- **`source = 'import'`** on every row it touches.
- **Dry run is the default.** It prints the counts it would write per status and the
  before/after register total, and writes nothing. `--commit` is required to write.

**Expected outcome:** register grows from 1,150 to roughly 5,955 rows. That number is
printed by the dry run and confirmed before committing rather than assumed here.

## 6. The worker cutover

`fetcher.get_pending()` stops reading the JSON file and claims from the register using
`claim_pipeline_item()` — the function that has existed unused since the schema was
written.

- **Claim:** one row at `queued`, oldest `queued_at` first, setting `claimed_by`,
  `claimed_at` and `status = 'downloading'`. The existing 15-minute stale-claim release
  already handles a worker that dies mid-item.
- **Success:** `transcribed`, `transcript_path` set; then `indexed_surreal` once the
  embedding service confirms. Each is a separate write, so a crash between them is
  visible rather than invisible.
- **Failure:** `failed`, with `last_error` and `error_stage`.
- **Blocked:** the claim is released back to `queued` and the row is NOT marked failed.
  This preserves the behaviour the `TranscriptBlocked` docstring exists to protect — a
  429 is a statement about our IP address, never about the video, and recording it as a
  permanent failure would blacklist videos that have perfectly good captions.
- **Postgres unreachable:** the worker stops claiming and says so loudly. It does NOT
  fall back to the JSON file. A silent fallback is precisely how the pipeline ran empty
  for two weeks while reporting healthy.

**Dual-write for one release.** The worker keeps updating the JSON state files while
reading only from the register, and the reconciliation check (§7) compares them. If they
agree for a full release, the JSON write is deleted. This buys a rollback path without
letting the two stores drift unobserved, which is the failure the whole build exists to
end.

### 6.1 There is a second claimer, and it is not in this repository

**Amended 2026-08-17 after the seam audit.** §1 said `claim_pipeline_item()` has zero
callers, which is true of this repository and was the wrong conclusion to draw from it.
Something has been claiming rows:

```
 claimed_by       | count | last_done                     | last_claim
------------------+-------+-------------------------------+------------------------------
 n8n-orchestrator |  1139 | 2026-08-15 16:35:20.205261+00 | 2026-08-15 16:35:14.02545+00
                  |    12 |                               |
```

An n8n workflow, held outside this repository, wrote 1,139 of the 1,151 rows and stopped
on 2026-08-15 — roughly two days before this spec. So the real picture is not "one live
queue and one dead mirror" but **two independent ingestion paths that have never known
about each other**: the n8n workflow tracking its work in Postgres, and the transcript
service tracking its own in JSON. That is a stronger statement of the same defect, and it
is why the count gap is 4,800 rather than zero.

Consequences for this build, all mandatory:

- **Find that workflow and decide its fate BEFORE the cutover.** Two claimers against one
  table will fight over the same rows. Tracked as issue #107.
- **The 1,139 claimed rows are not a stale-claim problem.** All but one sit at a terminal
  status (1,089 `indexed_surreal`, 49 `failed`); the single `downloading` row has been
  held since April and the existing stale-claim release handles it. The problem is the
  existence of a second writer, not the rows it left.
- **The import (§5) must not assume the register is empty of real outcomes.** Its
  never-downgrade-an-indexed-row rule already covers this, and that rule is now
  load-bearing rather than defensive.
- **A workflow that is not in the repository cannot be reasoned about from the
  repository.** Whatever survives the cutover gets checked in here or replaced.

## 7. The reconciliation check

`scripts/reconcile_stores.py`, also exposed at `GET /api/v1/reconciliation` so the
dashboard can show it. One question, four numbers:

- register rows claiming `indexed_surreal` with **no SurrealDB record**
- register rows claiming a transcript with **no file on the share**
- transcript files on the share with **no register row**
- SurrealDB records with **no register row**

Exits non-zero when any is non-zero. This single check would have caught every failure
listed in §1, and it is the reason this build is worth more than the page it delivers.

## 8. The Inbox

**Route:** `/inbox` in Enroll, added to the second-tier nav after Control.
**Data:** `GET /api/v1/inbox` — register rows at `discovered`, joined to channels.

**Ranking.** Rows split into two blocks: **Most relevant** pinned at the top, then
everything else, both newest-first within the block. In this build a row is "most
relevant" when its channel's `relevance_score` is 8 or higher. The score is one SQL
expression written so the personalities build adds a single term to it — a match on a
monitored personality — rather than rewriting the query.

**Columns:** thumbnail · channel · title · published · length · views · content kind.
Domain and guest columns are defined now and render blank until the extraction build
fills them, so that build ships without touching this page.

**Filters:** channel · domain · content kind · published date range · title text.

**Actions:**

| Action | Effect |
|---|---|
| Ingest | `queued`, `queued_at` and `reviewed_at`/`reviewed_by` set |
| Skip | `skipped`, `reviewed_at`/`reviewed_by` set |
| Skip everything remaining | skips **only what the current filter matches**, never the whole table |
| Undo | returns a skipped row to `discovered`, clearing the review fields |

Skip-remaining shows the exact count it will affect and requires a second click to
confirm. It is not gated behind the deletion protocol because it destroys nothing — the
rows remain and Undo restores them — but a bulk action that silently took a different
number than it displayed would be the same class of surprise.

**Empty state.** No channel is in hand-pick mode today, so the first thing anyone sees is
an empty page. It reads: *"No channels are set to hand-pick yet — the inbox fills up when
a channel is set to let you choose which videos to keep,"* with a link to the channel list
filtered to candidates. Anything less and the page looks broken on day one.

**Links.** Every row links to the video detail page with a full URL, and separately to
YouTube. Right-click and open in a new tab works on both.

## 9. Failure cases, before the happy path

| Case | Required behaviour |
|---|---|
| Zero hand-pick channels | The explanatory empty state, not a blank table |
| Discovered video whose channel was removed | Row still lists, channel shown as removed |
| Two sessions ingest the same video | The unique constraint plus the claim function make the second a no-op, not duplicate work |
| Skip-remaining with a filter applied | Only the filtered set; count shown and confirmed first |
| Import run twice | Identical result; no duplicate rows, no status churn |
| Import run while the worker is live | Import happens with the worker stopped; the cutover follows the import |
| Postgres unreachable mid-run | Worker halts and reports; never silently resumes from the JSON file |
| A row is `queued` but its channel was set back to auto | The row stays queued; a channel setting change never retroactively rewrites decisions already made |

## 10. Testing

Failure cases first, per the table above.

- `test_import_is_idempotent` — run twice against a fixture, assert identical rows
- `test_import_never_downgrades_indexed` — a Postgres row at `indexed_surreal` and a file
  entry at `queued` stays indexed
- `test_import_status_mapping` — one case per row of the §5 table
- `test_import_unmatched_handle_leaves_channel_null`
- `test_claim_is_exclusive` — two concurrent claims return different rows
- `test_blocked_releases_claim_without_failing` — the 429 path leaves the row `queued`
- `test_worker_halts_when_register_unreachable` — asserts no JSON fallback
- `test_skip_remaining_respects_filter` — a filtered skip leaves unfiltered rows alone
- `test_skip_then_undo_restores_discovered`
- `test_inbox_empty_state_when_no_selected_channels`
- `test_reconciliation_detects_each_drift_class` — one case per §7 number

Real data only: fixtures are captured from the live `video_list.json`, not fabricated.

## 11. Rollout

1. Apply migration 004 to Banner. Verify the columns and enum values exist.
2. Run the import in dry-run. **Matt sees the counts before anything is written.**
3. Stop the worker. Run the import with `--commit`. Verify the register total.
4. Run the reconciliation check and record the four numbers as the starting baseline.
5. Deploy the worker cutover. Start the worker. Confirm it claims from the register by
   watching a row move `queued → downloading → transcribed → indexed_surreal`.
6. Deploy the Inbox page.
7. Set one channel to hand-pick, run discovery, confirm rows land in the Inbox.
8. Codex review gate before any of this is called ready for Matt's verification.

Nothing is reported done until it is visible on `https://knowledge.nextlevelfoundry.com/enroll/inbox`
with real rows in it.

## 12. Open questions

1. **Which channels become hand-pick?** The Inbox stays empty until at least one is
   switched. Recommendation: Matt picks two or three interview-led channels to start, and
   the page's empty state links straight to that setting.
2. **What happens to the 539 rows currently queued in the file?** Recommendation: they
   import as `queued` and drain normally. They were already approved for ingestion under
   the old behaviour, and re-litigating them would put 539 items into an inbox meant for
   new decisions.
