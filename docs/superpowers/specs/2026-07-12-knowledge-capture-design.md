# Knowledge Capture (Raw Step) — Design Spec

> **Status:** DRAFT — pending your review/approval (brainstorming was interrupted before final sign-off)
> **Date:** 2026-07-12
> **Author:** Matt (via Claude brainstorming session)
> **Scope of THIS spec:** the raw *capture* step only. Processing/structuring is explicitly deferred.
> **Changelog:** 2026-07-12 — §5 recommended app updated **Voice Record Pro → Just Press Record** (primary),
> VRP now free fallback; Speakr upload endpoint confirmed (`POST /api/v1/recordings/upload`); meeting-capture
> verdict added. Backed by [docs/research/ios-voice-capture-2026.md](../../research/ios-voice-capture-2026.md).

---

## 1. Why (mission context)

Build courses + (eventually) animated videos that plant entrepreneurial / agency / positive-mindset
principles — the Carnegie–Hill–Robbins lineage — into **young** audiences (6–10, tweens, teens,
young adults), the same core concepts repackaged per age group. The expert YouTube corpus already in
KnowledgeStack is the **inspiration/source** (clips, quotes, segments); this new component is where
**Matt's own original thinking** gets captured and, later, refined into that content.

The near-term need is narrow and concrete: **start rambling into a recorder now** so raw ideas stop
evaporating, and build the outline to the first couple of courses from real captured material.

## 2. What we're building (this spec)

**Knowledge Capture — the raw step.** A reliable way to capture short (5–20 min) voice rambles from
an iPhone, transcribed **with timestamps**, stored as the **raw stage** of a personal corpus that is
kept separate from the expert corpus. **No processing, extraction, or cross-referencing in this spec** —
just trustworthy capture + storage + transcription.

### In scope
- Capture voice on iOS reliably (survives screen-lock / interruptions / long-ish sessions).
- Timestamped transcript produced automatically.
- A dedicated place for raw captures, separated from expert transcripts.
- A lightweight metadata convention so future restructuring is possible without migration.

### Out of scope (explicitly deferred — future specs)
- Best-line / key-concept extraction; speech-to-text cleanup.
- Quote / topic / concept tagging.
- Cross-referencing raw ideas → expert segments ("clip these 7 Myron minutes").
- Maturity stages beyond `raw` (research → rehearsal → produced).
- Structuring / categorizing / age-audience ordering for courses.
- YouVersion-style highlight-to-promote browse layer (see §8).

## 3. Product placement

New personal-content product line — working name **KnowledgeCapture** — the front of a future
personal-production pipeline ("Studio"). In the school metaphor: the expert videos are *lectures*;
this is Matt's own *notebook / thesis work*. Intended future trajectory (NOT built here): raw captures
flow into **KnowledgeCollege** as their **own namespace**, with Matt as a first-class "speaker,"
cross-linked to expert segments.

## 4. The maturity axis (backbone for later)

Personal content is not one bucket; it moves through stages. We record the axis now but only wire the
first stage:

`raw` → `research` → `rehearsal` → `produced`

Only `raw` is active in this spec. The capture metadata must carry enough identity that later stages
and restructuring tools can be built on top without re-ingesting.

## 5. Capture mechanism — findings & recommendation

**What we verified live (2026-07-12):**
- Speakr genuinely has an in-browser recorder (PWA, iOS-aware, session-persistence, timestamped). ✅
- The **canonical `/lecture` sub-path URL is broken** (root-absolute asset/API paths escape the
  Traefik prefix). Use the **root domain** instead: **https://transcripts.nextlevelguild.com/** ✅
- In-app iOS recording **worked** — captured clips saved to the **server** (`/data/uploads/recordings/…`,
  ~1 MB for 59 s). Nothing is lost on capture. ✅
- Transcription **failed** — but NOT due to capture, format, or size. Real cause: **OpenAI
  `429 insufficient_quota`** (org credit balance empty). Speakr **mislabels** this as "File Too Large /
  enable chunking," which sent us down a false trail. ❌→fix below.

**Capture-path options considered:**
| Path | Reliability (long/locked sessions) | Notes |
|------|-----------------------------------|-------|
| Speakr in-app recorder (PWA) | Risk: iOS Safari suspends mic on lock/background | Nicest UX; works foreground; unproven for multi-hour |
| **Native Voice Memos → upload to Speakr** | **Bulletproof** (native background audio) | One upload step (automatable via iOS Shortcut); `.m4a` is a known-good format for Speakr |
| iOS Shortcut → Speakr `/recordings/upload` API | Best UX + reliability | Small upfront build |

**DECISION (resolved by test, 2026-07-12): Voice Memos → upload is the primary capture path.**
The lock-screen test **failed**: recording in Speakr's in-app recorder, the screen locked at 38 s, the
mic was suspended, and although the UI *appeared* to resume on unlock, only the first 38 s reached the
server. This is the iOS Safari/WebKit background-mic limitation — not fixable in-browser. The in-app
recorder is therefore usable **only** for short, deliberate, screen-on captures; it is NOT reliable for
real-world rambling (driving, pocketed, locked).

**Primary path: a native iOS recorder → upload to Speakr** (WhisperX transcribes with timestamps).
Native apps hold the background-audio entitlement → they survive lock, app-switches, calls, and long
sessions. Web/PWA cannot (confirmed by WebKit bug #226620 + 2026 sources — see below).

**App choice (UPDATED by deeper research 2026-07-12 — see [ios-voice-capture-2026.md](../../research/ios-voice-capture-2026.md)):**
- **Just Press Record** — **$4.99 one-time** (no subscription). *New leading candidate.* Confirmed
  background/lock recording, **unlimited length**, and the richest hands-free triggers on iOS
  (Siri / Action Button / Lock Screen / Control Center / Widget / **URL scheme** / Shortcuts) — decisive
  for "start rambling while driving." Stores to **iCloud Drive** (feeds the drop-folder path for free),
  share-sheet export (feeds the Shortcut path), zero data collection.
- **Voice Record Pro** — **free** (IAP only removes the ad banner). *Now the free fallback.* Unlimited
  background recording, exports to Drive/Dropbox/iCloud/**FTP/WebDAV/"post to any web script."** Downsides:
  weak hands-free triggers, dated ad-supported UI, and 2026 **lock-screen** reliability is unverified.
- **Wave** — background recording + records VoIP calls & virtual meetings (would double as the
  "auto-capture meetings" source), BUT **$11.67/mo subscription** past 30 free min → out for a
  cost-conscious personal tool.
- **VoiceScriber** — ruled out: **90-min per-recording cap** kills long rambles; weekly/lifetime pricing.
- **Recorder Plus** — free with auto-iCloud backup + FTP/WebDAV, but transcription is consumable-credit
  gated; secondary at best.
- **Apple Voice Memos** — free and works, BUT a 2026 source flags its background recording as
  *not fully reliable*; keep as a last-resort fallback.
- Avoid Otter free tier (30-min/conversation cap kills long rambles).

**Into Speakr (endpoint confirmed 2026-07-12):** Speakr shipped a real **Upload API** in v0.8.15-alpha —
`POST /api/v1/recordings/upload`, `multipart/form-data`, `Authorization: Bearer <token>`, field `file`
(required) plus optional `notes` / `language` / `tag_ids[]` / `min_speakers` / `max_speakers` /
`file_last_modified`; returns `202` and queues transcription. Interactive Swagger at `/api/v1/docs`.
- **Primary path:** an **iOS Shortcut** ("Get Contents of URL" → POST, Request Body = **Form**, `file` =
  shared audio, headers carry the Bearer token) fired from the share sheet / Siri, filed into `Raw Captures`
  via `tag_ids`. iOS Shortcuts *does* support multipart (Form body + file field) — confirmed.
- **Zero-tap alternative:** a synced drop-folder + a server-side watcher on Banner that POSTs new files to
  the same endpoint (also a reusable "drop any audio → KnowledgeStack" lane, incl. meeting recordings).
  If Speakr's **native watch-folder** (v0.8.15) can see a path on Banner, this collapses to just syncing
  the folder — no custom POST script. Recorders that speak **FTP/WebDAV** (Voice Record Pro, Recorder Plus)
  can write there directly, sidestepping the awkward iCloud→Linux leg.

**Meetings (free):** no reliable free *iOS* path for platform-call audio; use a free **desktop system-audio
recorder** (Meetily or Meeting Transcriber, both MIT) → export audio → same Speakr ingest lane.

**Sources:** full report + citations in [docs/research/ios-voice-capture-2026.md](../../research/ios-voice-capture-2026.md)
(Speakr API docs; Apple Shortcuts/CarPlay guides; Zapier 2026 recorder roundup; app store listings).
Web/PWA capture remains structurally ruled out (WebKit #226620); wake-lock is foreground-only.

## 6. Transcription backend (must be fixed for capture to be usable)

**Immediate fix (done by you):** added $15 credit to the **NextLevelFoundry** OpenAI org. Since
`insufficient_quota` is org-level, this re-enables every key on the org. **Also enable auto-recharge**
— a silent quota-out is what killed the video ingestion pipeline in May.

**Confirm it works:** hit **retry ↻** on a failed recording in Speakr (or ask Claude to re-queue it).

**Preferred wiring (your choice):** route Speakr transcription through the internal **LiteLLM proxy**
(`10.0.0.27:2764`) instead of `api.openai.com` directly, for cost/quota monitoring. This uses the
`LiteLLM-Helicarrier` key on the NextLevelFoundry org.
- Requires: a transcription model in the LiteLLM config (`/opt/stacks/litellm/litellm-config.yaml` on
  Helicarrier) + repointing Speakr's `TRANSCRIPTION_BASE_URL` / connector / model / key to the proxy.
- Self-hosted WhisperX ruled out: Jarvis is AMD Strix Halo (no CUDA). Mac Studio is a possible future
  Metal/whisper.cpp host.

## 7. Metadata & separation convention (the one thing to get right now)

Each ramble = one Speakr recording (a **fragment**) with:
- **Folder:** top-level `Raw Captures`, per-project subfolders (e.g., `Kids Course – Mindset`).
- **Tags:** `source:personal`, `stage:raw`, `project:<name>`.
- **Title:** short, human ("agency – kids intro, take 2").
- **Note (optional):** one line for supersession breadcrumbs ("↩ better version of this morning's idea").
- **Order:** Speakr's `created_at` preserves chronology for free — the backbone future
  reorder/merge/supersede tooling hangs on.

This keeps raw personal musings **out of the expert transcript pool** and gives future tooling enough
identity (fragment id + order + title + note + tags) to restructure without re-ingesting.

## 8. Deferred capability worth recording: YouVersion-style browse/annotate

Model a future browse layer on the YouVersion Bible app: scroll captures, **highlight a line →
"capture this as a key point," tag, colorize, flag.** That highlight-to-promote gesture is the ideal
bridge from raw capture into the extraction/structuring phase (a highlight becomes a candidate
quote/key-point). Future spec, not now.

## 9. Open decisions for you (blocking final approval)
1. **Capture path** — ✅ RESOLVED (2026-07-12): **native recorder → upload** (in-app PWA recorder failed the
   lock-screen test — mic suspended at 38 s, only pre-lock audio survived). Recommended app now
   **Just Press Record** ($4.99 one-time; free fallback = Voice Record Pro). Remaining sub-decision: build
   the iOS Shortcut for one-tap/Siri multipart upload (recommended), or drop-folder watcher, or upload manually for now?
2. **Transcription wiring** — direct OpenAI (works now with credit) vs reroute via LiteLLM (monitoring).
3. **Name** — `KnowledgeCapture` OK, or prefer `KnowledgeStudio`/other?
4. **Separation** — Folders + tags (recommended) vs a fully separate Speakr space.

## 10. Bugs found (sidebars, not blocking this spec)
- **Speakr mislabels OpenAI `429 insufficient_quota` as "File Too Large."** Misleading; cost us time.
- **Speakr `/lecture` sub-path is broken** (root-absolute asset/API paths). Use root domain, or fix
  base-path config / give Speakr its own subdomain.

---

### Next step after approval
Per the brainstorming flow, once you approve this design + resolve §9, the next skill is **writing-plans**
to turn it into an implementation plan (small: mostly config + one lock-screen test + optional iOS Shortcut).
