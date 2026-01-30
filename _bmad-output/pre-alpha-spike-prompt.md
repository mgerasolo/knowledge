# Pre-Alpha Spike: Knowledge Ingestion Prototype

## What You're Building

A throwaway prototype to validate assumptions about YouTube transcript ingestion before we invest in formal architecture. This is a learning exercise — the code won't be kept long-term. Optimize for speed and discovery, not quality.

**Project directory:** `/home/mgerasolo/Dev/knowledge/`
**Git branch:** Create a new branch `spike/pre-alpha-ingest` off `main`

## CRITICAL: Code Isolation Rules

**All spike code MUST live in `spike/` directory at the project root.** This prototype is completely isolated from the main codebase. It will be deleted or selectively migrated later.

### Directory Structure (Already Created)

The following directories already exist. **Do NOT create directories or files outside this structure.**

```bash
# These exist — do NOT recreate or restructure them
spike/src/db/
spike/src/qdrant/
spike/src/youtube/
spike/src/embeddings/
spike/samples/
spike/reports/
```

### Complete File Map

Every file you create has exactly one correct location. **If a path isn't in this list, don't create it.**

```
knowledge/
├── spike/                          # <-- ALL your code goes here
│   ├── package.json                # Separate package.json (spike dependencies only)
│   ├── tsconfig.json               # Separate TS config
│   ├── .env                        # Spike-specific env vars (Qdrant URL, PG connection, LiteLLM)
│   ├── findings.md                 # Discovery notes — UPDATE AFTER EVERY MAJOR TASK
│   ├── src/
│   │   ├── ingest.ts               # Main ingestion pipeline
│   │   ├── query.ts                # CLI query tool
│   │   ├── db/
│   │   │   ├── schema.sql          # PostgreSQL schema
│   │   │   └── client.ts           # DB connection
│   │   ├── qdrant/
│   │   │   └── client.ts           # Qdrant connection + operations
│   │   ├── youtube/
│   │   │   └── transcript.ts       # YouTube transcript fetcher
│   │   └── embeddings/
│   │       └── client.ts           # LiteLLM embedding calls
│   ├── samples/                    # Raw API response samples (first 3-5 transcripts)
│   │   └── *.json                  # e.g., sample-huberman-ep1.json
│   └── reports/                    # Batch run reports
│       └── run-YYYY-MM-DD-HHMMSS.json
│
├── _bmad-output/
│   └── analysis/
│       └── pre-alpha-findings.md   # <-- ONLY file you write outside spike/
│                                   #     Cumulative findings report (save after each major task)
│
├── _bmad/                          # BMAD framework (DO NOT TOUCH)
├── package.json                    # Root project (DO NOT MODIFY)
├── CLAUDE.md                       # Project rules (READ THIS FIRST)
└── ...                             # Everything else (DO NOT MODIFY)
```

### Isolation Rules

- **DO NOT modify the root `package.json`** — the spike has its own
- **DO NOT create files outside `spike/`** — the ONE exception is `_bmad-output/analysis/pre-alpha-findings.md`
- **DO NOT import from or reference any files outside `spike/`**
- **DO NOT create files in the root directory** (no `findings.md` at root, no `schema.sql` at root, nothing)
- **The spike runs independently:** `cd spike && npm install && npm run ingest`
- **Add `spike/node_modules/` and `spike/.env` to the root `.gitignore`** if not already ignored
- This code will either be **deleted entirely** or have select pieces **manually migrated** to the production codebase later. Write it knowing that.

## Critical Deployment Rules

- **NEVER deploy containers to localhost or Stark** — containers run on Banner (10.0.0.33)
- **SSH to Banner using hostname only:** `ssh banner` (never `ssh 10.0.0.33`)
- **All URLs use IP, not localhost:** `http://10.0.0.33:PORT` (containers aren't on your machine)
- **Docker/Portainer:** Banner runs Portainer. You can deploy Docker containers via SSH or Portainer API
- **Shared env files:** `/mnt/foundry_project/AppServices/env/` — check for existing PostgreSQL credentials there
- **Port block for knowledge project:** web=3350. Pick nearby ports for services (e.g., Qdrant on 6333/6334)

## Architecture (Already Decided)

| Component | Choice | Notes |
|-----------|--------|-------|
| Runtime | Node.js + TypeScript | Project already has TS configured |
| Vector DB | **Qdrant** (Docker on Banner) | Self-hosted, Rust-based, handles 10M+ vectors |
| Relational DB | **PostgreSQL** (on Banner) | Check if shared AppServices PG exists, or spin up a new one |
| AI Proxy | **LiteLLM** at `http://10.0.0.27:2764` | Already running. Use for embeddings and any AI calls |
| Embeddings | Via LiteLLM proxy | Route embedding requests through LiteLLM |
| Automation | n8n available but **don't use it for this spike** — write native code to learn the pain points |

## What to Build (Scope)

### 1. Infrastructure Setup
- [ ] Deploy **Qdrant** Docker container on Banner (ports 6333 HTTP / 6334 gRPC)
  - Qdrant includes a built-in web dashboard at `http://10.0.0.33:6333/dashboard` — no extra tool needed to browse collections, vectors, and metadata
- [ ] Set up **PostgreSQL** database (reuse existing Banner PG if available, otherwise deploy one)
- [ ] Deploy **CloudBeaver** on Banner for web-based PostgreSQL browsing (no UI is being built, so we need a way to inspect the data):
  ```bash
  ssh banner
  docker run -d \
    --name knowledge-cloudbeaver \
    --restart unless-stopped \
    -p 8978:8978 \
    -v /opt/knowledge/cloudbeaver/workspace:/opt/cloudbeaver/workspace \
    dbeaver/cloudbeaver:latest
  ```
  Access at: `http://10.0.0.33:8978`
  Configure a PostgreSQL connection to the spike database after it's running.
- [ ] Create basic DB schema:
  - `channels` — Capture ALL available metadata from YouTube Data API:
    - id, youtube_channel_id, name, description, custom_url, country
    - subscriber_count, video_count, view_count
    - thumbnail_url, banner_url
    - published_at (channel creation date), created_at (our ingest date)
    - channel_type (expert/platform/curator/hybrid — can be null initially)
    - raw_api_response (JSONB — store the full API response so we don't lose anything)
  - `videos` — Capture ALL available metadata from YouTube Data API:
    - id, channel_id, youtube_video_id, title, description
    - published_at, duration_seconds
    - url, thumbnail_url
    - view_count, like_count, comment_count
    - tags (text array — YouTube's own tags)
    - category_id (YouTube category)
    - default_language, default_audio_language
    - is_short (boolean — duration < 60s)
    - aspect_ratio (text — 'landscape' / 'portrait' / 'square' — derive from thumbnail dimensions or video metadata)
    - is_live_content (boolean — was this a livestream?)
    - transcript_status (pending/fetched/failed/no_transcript)
    - transcript_error (text — why it failed, if it did)
    - raw_api_response (JSONB — store the full API response)
    - created_at, updated_at
  - `transcripts` (id, video_id, full_text, language, source, word_count, char_count, fetched_at)
  - `segments` (id, video_id, transcript_id, text, start_time, end_time, speaker_label, embedding_id, created_at)
  - **Principle: capture everything YouTube gives us.** Storage is cheap, re-fetching 100 videos to grab a field we missed is not. Store the full raw API response in JSONB alongside the parsed columns so nothing is lost.

### 2. YouTube Transcript Fetcher
- [ ] Build a script/service that takes a YouTube video URL or channel URL
- [ ] Fetches the transcript using YouTube's transcript API (try `youtube-transcript` npm package or YouTube Data API v3)
- [ ] Stores raw transcript in PostgreSQL
- [ ] Basic chunking: split transcript into segments (start with simple time-based chunks of ~2-3 minutes; we'll learn if this is good enough or if we need topic-based)
- [ ] Generate embeddings for each segment via LiteLLM and store in Qdrant
- [ ] Link Qdrant vector IDs back to PostgreSQL segment records via metadata

### 3. Batch Channel Ingestion
- [ ] Given a YouTube channel URL, fetch the last 30-50 videos
- [ ] Process each video's transcript through the pipeline
- [ ] Track progress (which videos succeeded, which failed, why)
- [ ] Target: ingest **50-100 videos** across 3-5 different channels

### 4. Basic Query Test
- [ ] Simple CLI or script that takes a text query
- [ ] Converts to embedding via LiteLLM
- [ ] Searches Qdrant for similar segments
- [ ] Returns: video title, channel name, timestamp range, matching text
- [ ] This validates the entire pipeline end-to-end

## Spike Best Practices

These aren't about code quality — they're about maximizing what we learn.

**Idempotency:** Track which videos have been ingested (by YouTube video ID in PostgreSQL). If the script is re-run or crashes halfway through a batch, it skips already-processed videos and picks up where it left off. Don't re-ingest duplicates.

**Pre-flight checks:** Before starting any batch, verify Qdrant and PostgreSQL are reachable. Check LiteLLM `/models` endpoint to confirm an embedding model is available and note its output dimension. Fail fast with clear error messages, not 50 lines into a batch.

**Embedding dimension validation:** Query LiteLLM `/models` to discover the actual embedding model and its vector dimension. Use that dimension when creating the Qdrant collection. A mismatch between embedding size and collection config causes silent failures.

**Shorts and format detection:** Flag each video with:
- `is_short`: duration < 60 seconds
- `aspect_ratio`: landscape / portrait / square — derive from thumbnail dimensions (portrait = Short, landscape = full video typically). YouTube thumbnails for Shorts are 1080x1920 (portrait); regular videos are 1280x720 or similar (landscape). Check the `maxres` or `high` thumbnail dimensions from the API response.
- `is_live_content`: whether it was originally a livestream

Don't skip Shorts — ingest them — but tag them so we can analyze the ratio and decide how to handle them later.

**Raw data samples:** Save the first 3-5 raw transcript API responses (before any processing) to `spike/samples/` as JSON files. We need to visually inspect what YouTube actually returns — timestamp granularity, formatting, edge cases, language detection.

**Structured run report:** After each batch, generate a summary (JSON or markdown) with:
- Videos attempted / succeeded / failed
- Failure reasons (no transcript, API error, rate limit, etc.)
- Average transcript length (chars and word count)
- Average segments per video
- Average embedding time per segment
- Total vectors stored in Qdrant
- Total wall-clock time
- Qdrant collection size (bytes)

Save to `spike/reports/run-YYYY-MM-DD-HHMMSS.json`

**Graceful failure:** If one video fails, log the error and continue to the next video. Don't abort the entire batch. Capture the failure reason in the videos table (transcript_status = 'failed', with error detail).

## What NOT to Build

- No UI / No web server / No API (just scripts and CLI)
- No authentication
- No diarization or speaker identification
- No topic-based chunking (use simple time-based for now)
- No statement classification
- No authority profiles
- No n8n workflows
- No Docker Compose for the app itself (just Qdrant and PG as containers)
- No tests (this is throwaway code)

## Suggested Channel Mix for Testing

Pick 3-5 channels that represent different types:
1. **Expert channel** (solo speaker, deep domain) — e.g., Huberman Lab, 3Blue1Brown, or any solo educational channel
2. **Platform channel** (host + guests) — e.g., Lex Fridman, Joe Rogan, Diary of a CEO
3. **Curator/news channel** (compilations, summaries) — e.g., Fireship, Matt Wolf AI
4. **Short-form heavy** (lots of shorts mixed with long) — to see how shorts vs long-form behaves
5. **High volume** (daily uploads) — to stress-test ingestion speed

## LiteLLM Embedding Details

```bash
# LiteLLM proxy endpoint
BASE_URL=http://10.0.0.27:2764

# To get embeddings, POST to:
# POST http://10.0.0.27:2764/embeddings
# Body: { "model": "text-embedding-3-small", "input": "your text here" }
#
# Check available models:
# GET http://10.0.0.27:2764/models
#
# Try the models endpoint first to see what embedding models are available.
# If text-embedding-3-small isn't available, use whatever embedding model is listed.
```

## Qdrant Setup

```bash
# Deploy Qdrant on Banner
ssh banner
docker run -d \
  --name knowledge-qdrant \
  --restart unless-stopped \
  -p 6333:6333 \
  -p 6334:6334 \
  -v /opt/knowledge/qdrant/storage:/qdrant/storage \
  qdrant/qdrant:latest

# Verify
curl http://10.0.0.33:6333/healthz
```

Create a collection for transcript segments:
```
Collection: knowledge_segments
Vector size: match your embedding model's output dimension (1536 for text-embedding-3-small)
Distance: Cosine
```

## Success Criteria

When you're done, I should be able to:
1. See Qdrant running on Banner with a populated collection
2. See PostgreSQL with channels, videos, transcripts, and segments populated
3. Run a query like "What does [expert] think about [topic]?" and get back relevant transcript segments with timestamps
4. See a log/report of: how many videos attempted, how many succeeded, common failure reasons, average processing time per video

## Discovery Questions to Answer

As you build, keep notes on what you discover:
- Which YouTube transcript method works best? (API, scraping, npm package?)
- How many videos fail to have transcripts available?
- What does the raw transcript data actually look like? (timestamps, formatting, quality)
- How long does it take to process one video end-to-end?
- Does simple time-based chunking produce useful search results, or is it clearly inadequate?
- What embedding model is available via LiteLLM and how fast is it?
- Any rate limiting issues with YouTube APIs?
- How big is the Qdrant collection after 100 videos? (vectors, storage)

Save your findings to `_bmad-output/analysis/pre-alpha-findings.md` when done.

## Deviations & Lessons Learned (REQUIRED)

This spike exists to teach us what reality looks like before we invest in formal architecture. **You MUST actively document the following as you go** — don't wait until the end, capture it in real-time in `spike/findings.md` as you hit things:

### What to Document

**Challenges encountered:**
- What was harder than expected? What took multiple attempts?
- Where did you get stuck and how did you solve it?
- What error messages or gotchas did you run into that future developers should know about?
- What tools, libraries, or APIs behaved differently than their docs suggest?

**Deviations from this prompt:**
- Where did you need to make a different choice than what this prompt specifies? Why?
- What assumptions in this prompt turned out to be wrong?
- What was this prompt missing that you had to figure out on your own?
- Did the suggested architecture (Qdrant, LiteLLM, etc.) work as expected, or did you need workarounds?

**Lessons for the production build:**
- What would you do differently if starting over?
- What architectural patterns worked well and should be kept?
- What patterns failed or were awkward and should be redesigned?
- What surprised you about the data (transcript format, metadata quality, API behavior)?
- What scale/performance concerns emerged that the production system needs to plan for?
- Which of the "What NOT to Build" items did you find yourself wishing you had?

### Format

In `_bmad-output/analysis/pre-alpha-findings.md`, include a structured section:

```markdown
## Challenges
- [Challenge]: [What happened and how it was resolved]

## Deviations from Spike Prompt
- [What changed]: [Why, and what the prompt should have said]

## Lessons for Production
- [Insight]: [Recommendation for the real architecture]

## Assumptions That Were Wrong
- [Assumption]: [Reality]

## If I Started Over
- [What I'd change]: [Why]
```

This feedback is the most valuable output of the entire spike — it directly feeds into our architectural decisions. The code is throwaway; the learnings are permanent.

## Qdrant Features to Explore

Qdrant doesn't have a plugin system — features are built-in. During the spike, explore and document which of these are useful:

- **Hybrid search (BM25 + dense vectors):** Qdrant has built-in BM25 sparse vector support with server-side IDF. Try the Prefetch API to combine semantic + keyword search in one request. Use Reciprocal Rank Fusion (RRF) for merging results.
- **Full-text payload indexing:** You can create a text index on transcript text stored in Qdrant payloads. Uses tokenizers (word, multilingual, prefix). Try `phrase_matching: true`.
- **Named vectors:** Store multiple embeddings per point (e.g., `dense` for semantic, `sparse` for BM25). This is powerful for hybrid search.
- **Payload indexes:** Create keyword, integer, datetime, and text indexes on payload fields (video_id, channel_id, upload_date, etc.) to speed up filtered searches.
- **Collection aliases:** Can atomically swap one collection for another — useful for re-embedding with a different model later.
- **TypeScript client:** Use `@qdrant/js-client-rest` (official, TypeScript-native, uses native fetch). NOT `@qdrant/qdrant-js` which is the umbrella package — the REST client is lighter.

**Don't try to use all of these** — pick what's needed for the basic pipeline. But document which ones seem valuable for the production system.

## PostgreSQL Extensions to Consider

The spike PostgreSQL instance should try these extensions where relevant:

- **pg_trgm** (fuzzy search): Built-in extension for similarity matching on channel names, video titles. Good for autocomplete. `CREATE EXTENSION pg_trgm;`
- **pg_stat_statements** (monitoring): Track slow queries. Essential even for a spike. `CREATE EXTENSION pg_stat_statements;`
- **ParadeDB pg_search** (BM25 full-text): Elasticsearch-quality BM25 search inside PostgreSQL, built on Tantivy (Rust). If available as a Docker image extension, try it for transcript search. This is an alternative to Qdrant's text search. `CREATE EXTENSION pg_search;`
- **TimescaleDB** (time-series): If the spike captures view count snapshots, TimescaleDB provides hypertables with automatic time partitioning and compression. Docker image: `timescale/timescaledb:latest-pg16`. Worth trying if it's easy to set up.

**For the spike, at minimum install:** pg_stat_statements and pg_trgm (both trivial). Try ParadeDB or TimescaleDB only if time permits — document whether they'd be valuable for production.

**Don't install:** pgvector (we're using Qdrant for vectors, not PostgreSQL).

## Environment Notes

- The project already has `package.json` with TypeScript, ESLint, Prettier, Vitest configured
- Node.js project — use npm for packages
- The `.mcp.json` has a Docker MCP gateway at `http://10.0.0.27:2761/sse` — you may be able to use this for Docker operations instead of SSH
- Shared secrets are at `/mnt/foundry_project/AppServices/env/` — check `appservices.env` and `infrastructure.env` for any existing PostgreSQL connection strings
- If no existing PG exists on Banner for this project, spin one up in Docker alongside Qdrant

## Decision Autonomy

**You are expected to make your own decisions.** Don't ask the user minor questions — pick the frameworks, libraries, and approaches yourself. Document what you chose and why in the findings file. The whole point of the spike is to discover what works.

**Ask only if:**
- A deployment rule in CLAUDE.md seems to conflict with what you need to do (e.g., port collision, SSH issues)
- You discover something that fundamentally invalidates the approach (e.g., YouTube API completely blocks transcript access)
- You're about to do something destructive or irreversible outside the spike/ directory

**Never ask about:**
- Which npm package to use — pick one and document your choice
- How to structure the code — it's throwaway, do what makes sense
- Whether to handle an edge case — handle it or don't, document the decision
- Minor architecture choices — that's what the findings file is for

## Incremental Documentation (CRITICAL)

**Do NOT wait until the end to write findings.** Your session will compact as you work, and anything not saved to a file will be lost.

**After completing each major task** (infra setup, first transcript fetch, first batch, query test), immediately:

1. Update `spike/findings.md` with what you learned during that task
2. Update the Deviations/Challenges sections if anything came up
3. Save `_bmad-output/analysis/pre-alpha-findings.md` with a cumulative summary

**Save cadence:**
- After infrastructure setup (Qdrant, PG, CloudBeaver deployed)
- After first successful transcript fetch
- After first batch of 10+ videos
- After first successful query test
- After final batch completion
- Final summary at the end

If you're about to hit compaction, **save your findings immediately** before anything else. The documentation is more valuable than the code.

## One More Thing

This is a spike — move fast, take shortcuts, and document what you learn. The formal architecture will come later informed by what this prototype reveals.
