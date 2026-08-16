# KnowledgeStack Roadmap

> **This file is generated. Do not hand-edit it** — except inside the
> hand-written block below, which survives every regeneration.
>
> Regenerate with `python3 scripts/roadmap-sync.py`
>
> The GitHub issue tracker is the source of truth. If this file and an
> issue disagree, the issue is right and this file is stale. Fix the
> issue and re-run — never patch this file by hand.
>
> Generated 2026-08-16 13:55 EDT from 36 issues.

**31 open · 2 in flight · 4 awaiting your decision · 5 closed**

<!-- HAND-WRITTEN:START -->

## Direction

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

<!-- HAND-WRITTEN:END -->

## Where everything stands

⚓ **KnowledgeStack** — IN PROGRESS · 4 decisions waiting on you · 2 in flight  
├─❓ **Capabilities the product assumes but does not have** — 10 open  
│  ├─❓ Generate embeddings for the corpus so meaning-based search becomes possible ([#29](https://github.com/mgerasolo/knowledge/issues/29)) — _high_  
│  ├─❓ Decide whether topic and entity tagging stays on the roadmap - it was never built ([#31](https://github.com/mgerasolo/knowledge/issues/31)) — _medium_  
│  ├─❓ Dynamic domains for host/interviewer channels — classify per video, not per channel ([#91](https://github.com/mgerasolo/knowledge/issues/91)) — _medium_  
│  ├─⬜ CRITICAL: 0 of 327,402 segments have embeddings — semantic search has nothing to search ([#44](https://github.com/mgerasolo/knowledge/issues/44)) — _critical_  
│  ├─⬜ Ship the meaning-based search endpoint - today it is a stub returning 501 ([#30](https://github.com/mgerasolo/knowledge/issues/30)) — _high_  
│  ├─⬜ SurrealDB OOM-killed 3x on 2026-08-14 at ~4GB container limit during embedding backfill ([#73](https://github.com/mgerasolo/knowledge/issues/73)) — _high_  
│  ├─⬜ Livestream VODs ingest with all-zero segment timestamps — citations cannot deep-link ([#72](https://github.com/mgerasolo/knowledge/issues/72)) — _medium_  
│  ├─⬜ Professor spike (Gen 1) — talk-to-a-personality RAG chat with cited video clips ([#16](https://github.com/mgerasolo/knowledge/issues/16)) — _unset_  
│  ├─⬜ Professor Gen 1 requirements: 8 adversarial-review findings logged from spike (not fixed in spike) ([#79](https://github.com/mgerasolo/knowledge/issues/79)) — _unset_  
│  ├─⬜ Keyword search slowed to ~15-20s per query — segment scans now haul 6KB embedding vectors ([#97](https://github.com/mgerasolo/knowledge/issues/97)) — _unset_  
│  └─👍 Single-video enrollment — ingest one video (guest appearances) without enrolling the whole channel ([#46](https://github.com/mgerasolo/knowledge/issues/46)) — _medium · closed 2026-08-14_  
├─🔄 **Ingestion reliability — keeping transcripts arriving** — 6 open  
│  ├─🔄 Make YouTube's per-channel feed the primary way we find new videos, with the scraper as fallback ([#19](https://github.com/mgerasolo/knowledge/issues/19)) — _medium_  
│  ├─⬜ Publish dates still land empty on the standing backfill path — 94% of its queue has no source date ([#57](https://github.com/mgerasolo/knowledge/issues/57)) — _high_  
│  ├─⬜ Check busy channels more often than dormant ones instead of one schedule for all 52 ([#20](https://github.com/mgerasolo/knowledge/issues/20)) — _medium_  
│  ├─⬜ A YouTube rate-limit block should stop the whole batch, not just pause one worker ([#21](https://github.com/mgerasolo/knowledge/issues/21)) — _medium_  
│  ├─📌 A non-US proxy exit would hit YouTube's consent page and look like a mystery outage ([#25](https://github.com/mgerasolo/knowledge/issues/25)) — _low_  
│  ├─📌 The one-queue-at-a-time guard does not cover the backfill queue running right now ([#34](https://github.com/mgerasolo/knowledge/issues/34)) — _low_  
│  ├─👍 Install a JavaScript runtime so yt-dlp works normally, instead of our two override flags ([#22](https://github.com/mgerasolo/knowledge/issues/22)) — _medium · closed 2026-08-14_  
│  └─👍 Nothing checks that yt-dlp itself is present and working ([#23](https://github.com/mgerasolo/knowledge/issues/23)) — _medium · closed 2026-08-14_  
├─❓ **Corpus quality — trusting what is already stored** — 8 open  
│  ├─❓ Four places each track what we have ingested, and they drift apart unnoticed ([#18](https://github.com/mgerasolo/knowledge/issues/18)) — _high_  
│  ├─⬜ 3 Myron Golden transcripts on disk are missing from the search library; 44 videos are stored under two channel folder names ([#4](https://github.com/mgerasolo/knowledge/issues/4)) — _high_  
│  ├─⬜ All 4,458 videos have empty uploader — video metadata backfill not applied ([#45](https://github.com/mgerasolo/knowledge/issues/45)) — _high_  
│  ├─⬜ Repair and backfill incomplete video metadata ([#71](https://github.com/mgerasolo/knowledge/issues/71)) — _high_  
│  ├─⬜ We never notice when a video in the library is deleted, made private or age-restricted ([#24](https://github.com/mgerasolo/knowledge/issues/24)) — _medium_  
│  ├─⬜ Backfill the publish dates and descriptions lost while metadata fetching was silently failing ([#27](https://github.com/mgerasolo/knowledge/issues/27)) — _medium_  
│  ├─⬜ Confirm the 14 quarantined date-less transcripts were re-fetched, then clear the quarantine ([#28](https://github.com/mgerasolo/knowledge/issues/28)) — _medium_  
│  ├─📌 Shorts are ingested indiscriminately and dilute search results ([#26](https://github.com/mgerasolo/knowledge/issues/26)) — _low_  
│  └─👍 Video length, view counts and chapters are captured but never reach the search library ([#17](https://github.com/mgerasolo/knowledge/issues/17)) — _medium · closed 2026-08-14_  
├─🔄 **The backfill programme — how deep we go** — 2 open  
│  ├─🔄 Ingest Jordan B Peterson's 18 livestreams ([#33](https://github.com/mgerasolo/knowledge/issues/33)) — _low_  
│  └─⬜ Plan stage 2 - the deep livestream archives that stage 1 deliberately capped ([#32](https://github.com/mgerasolo/knowledge/issues/32)) — _medium_  
└─⬜ **Tooling and process — how we keep ourselves honest** — 5 open  
   ├─⬜ Block conflict markers from commits and CI ([#67](https://github.com/mgerasolo/knowledge/issues/67)) — _high_  
   ├─⬜ Test schema-writing changes against real SurrealDB schema ([#68](https://github.com/mgerasolo/knowledge/issues/68)) — _high_  
   ├─⬜ Prevent secrets from appearing in diagnostic output ([#69](https://github.com/mgerasolo/knowledge/issues/69)) — _high_  
   ├─⬜ Nothing runs the consumer guide's weekly re-verification we promised ([#35](https://github.com/mgerasolo/knowledge/issues/35)) — _medium_  
   ├─⬜ Formalize the consumer API compatibility contract ([#70](https://github.com/mgerasolo/knowledge/issues/70)) — _medium_  
   └─👍 Standing discovery ignores dashboard channel settings — engine runs off a hard-coded list in config.py ([#81](https://github.com/mgerasolo/knowledge/issues/81)) — _high · closed 2026-08-16_  

👍 done and verified · ✅ ran, not yet verified · 🔄 in progress · ⬜ not started · ❓ needs a decision from you · ⏳ waiting on an external system · 📌 future enhancement
