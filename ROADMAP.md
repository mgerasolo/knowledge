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
> Generated 2026-08-14 00:24 EDT from 24 issues.

**24 open · 3 in flight · 3 awaiting your decision · 0 closed**

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

⚓ **KnowledgeStack** — IN PROGRESS · 3 decisions waiting on you · 3 in flight  
├─❓ **Capabilities the product assumes but does not have** — 6 open  
│  ├─❓ Generate embeddings for the corpus so meaning-based search becomes possible ([#29](https://github.com/mgerasolo/knowledge/issues/29)) — _high_  
│  ├─❓ Decide whether topic and entity tagging stays on the roadmap - it was never built ([#31](https://github.com/mgerasolo/knowledge/issues/31)) — _medium_  
│  ├─⬜ CRITICAL: 0 of 327,402 segments have embeddings — semantic search has nothing to search ([#44](https://github.com/mgerasolo/knowledge/issues/44)) — _critical_  
│  ├─⬜ Ship the meaning-based search endpoint - today it is a stub returning 501 ([#30](https://github.com/mgerasolo/knowledge/issues/30)) — _high_  
│  ├─⬜ Single-video enrollment — ingest one video (guest appearances) without enrolling the whole channel ([#46](https://github.com/mgerasolo/knowledge/issues/46)) — _medium_  
│  └─⬜ Professor spike (Gen 1) — talk-to-a-personality RAG chat with cited video clips ([#16](https://github.com/mgerasolo/knowledge/issues/16)) — _unset_  
├─🔄 **Ingestion reliability — keeping transcripts arriving** — 7 open  
│  ├─🔄 Make YouTube's per-channel feed the primary way we find new videos, with the scraper as fallback ([#19](https://github.com/mgerasolo/knowledge/issues/19)) — _medium_  
│  ├─⏳ Install a JavaScript runtime so yt-dlp works normally, instead of our two override flags ([#22](https://github.com/mgerasolo/knowledge/issues/22)) — _medium_  
│  ├─⏳ Nothing checks that yt-dlp itself is present and working ([#23](https://github.com/mgerasolo/knowledge/issues/23)) — _medium_  
│  ├─⬜ Check busy channels more often than dormant ones instead of one schedule for all 52 ([#20](https://github.com/mgerasolo/knowledge/issues/20)) — _medium_  
│  ├─⬜ A YouTube rate-limit block should stop the whole batch, not just pause one worker ([#21](https://github.com/mgerasolo/knowledge/issues/21)) — _medium_  
│  ├─📌 A non-US proxy exit would hit YouTube's consent page and look like a mystery outage ([#25](https://github.com/mgerasolo/knowledge/issues/25)) — _low_  
│  └─📌 The one-queue-at-a-time guard does not cover the backfill queue running right now ([#34](https://github.com/mgerasolo/knowledge/issues/34)) — _low_  
├─🔄 **Corpus quality — trusting what is already stored** — 8 open  
│  ├─❓ Four places each track what we have ingested, and they drift apart unnoticed ([#18](https://github.com/mgerasolo/knowledge/issues/18)) — _high_  
│  ├─🔄 Video length, view counts and chapters are captured but never reach the search library ([#17](https://github.com/mgerasolo/knowledge/issues/17)) — _medium_  
│  ├─⬜ 3 Myron Golden transcripts on disk are missing from the search library; 44 videos are stored under two channel folder names ([#4](https://github.com/mgerasolo/knowledge/issues/4)) — _high_  
│  ├─⬜ All 4,458 videos have empty uploader — video metadata backfill not applied ([#45](https://github.com/mgerasolo/knowledge/issues/45)) — _high_  
│  ├─⬜ We never notice when a video in the library is deleted, made private or age-restricted ([#24](https://github.com/mgerasolo/knowledge/issues/24)) — _medium_  
│  ├─⬜ Backfill the publish dates and descriptions lost while metadata fetching was silently failing ([#27](https://github.com/mgerasolo/knowledge/issues/27)) — _medium_  
│  ├─⬜ Confirm the 14 quarantined date-less transcripts were re-fetched, then clear the quarantine ([#28](https://github.com/mgerasolo/knowledge/issues/28)) — _medium_  
│  └─📌 Shorts are ingested indiscriminately and dilute search results ([#26](https://github.com/mgerasolo/knowledge/issues/26)) — _low_  
├─🔄 **The backfill programme — how deep we go** — 2 open  
│  ├─🔄 Ingest Jordan B Peterson's 18 livestreams ([#33](https://github.com/mgerasolo/knowledge/issues/33)) — _low_  
│  └─⬜ Plan stage 2 - the deep livestream archives that stage 1 deliberately capped ([#32](https://github.com/mgerasolo/knowledge/issues/32)) — _medium_  
└─⬜ **Tooling and process — how we keep ourselves honest** — 1 open  
   └─⬜ Nothing runs the consumer guide's weekly re-verification we promised ([#35](https://github.com/mgerasolo/knowledge/issues/35)) — _medium_  

👍 done and verified · ✅ ran, not yet verified · 🔄 in progress · ⬜ not started · ❓ needs a decision from you · ⏳ waiting on an external system · 📌 future enhancement
