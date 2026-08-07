# iOS Voice Capture → Speakr — Research Report (2026-07-12)

> **Goal:** Reliably capture Matt's own 5–20 min (up to multi-hour) voice rambles on iPhone —
> often while driving, pocketed, or screen-locked — with clear on-device recording confirmation
> (timer/waveform), then auto-ingest into self-hosted Speakr (`https://transcripts.nextlevelguild.com`)
> for timestamped transcription.
>
> **Settled premise (not re-litigated):** a web app / PWA **cannot** record through iOS
> screen-lock/background (WebKit bug #226620); native apps hold the background-audio entitlement and
> can. So the solution is a **native recorder → into Speakr**. This report picks the app + the ingest path.

---

## TL;DR — Recommended stack

| Layer | Pick | Why |
|-------|------|-----|
| **Recorder app** | **Just Press Record** ($4.99 one-time) | Confirmed background/lock recording, **unlimited length**, the richest hands-free triggers (Siri / Action Button / Lock Screen / Control Center / Widget / URL scheme / Shortcuts), share-sheet + iCloud Drive export, zero data collection, actively maintained. Best fit for "start rambling while driving." |
| **Free fallback recorder** | **Voice Record Pro** (free; IAP only removes the ad banner) | Unlimited background recording, records to m4a/mp3/wav, and exports to Dropbox/Drive/iCloud/S3/**FTP/WebDAV/"Post to any web script."** No cost, but weaker hands-free triggers and 2026 lock-screen reliability is unverified. |
| **Into Speakr (primary)** | **iOS Shortcut → multipart POST** to `POST /api/v1/recordings/upload` with a Bearer token, fired from the share sheet / Siri | One tap (or one phrase) from any recorder that exposes a share sheet. Speakr queues transcription immediately (HTTP 202). |
| **Into Speakr (zero-tap alt)** | **Synced drop-folder + server watcher** on Banner | Recorder saves to iCloud Drive / Nextcloud → Banner syncs → a watch script POSTs new files to the same upload API. Also becomes a reusable "drop any audio → KnowledgeStack" lane (incl. meeting recordings). |
| **Meetings (Zoom/Meet), free** | **Desktop system-audio recorder** (Meetily or Meeting Transcriber, both MIT/free) → export audio → same Speakr ingest lane | No good *free* iOS-native path for platform-call audio; capture system audio on the laptop instead, then reuse the drop-folder. |

**This changes the draft spec §5**, which currently leads with Voice Record Pro. Recommendation is now
**Just Press Record as primary**, Voice Record Pro as the free fallback. Rationale below.

---

## 1. Native iOS voice recorders — comparison (researched 2026-07-12)

| App | Price / model | Per-recording length | Background / screen-lock | Export / ingest options | Built-in transcription | Hands-free start |
|-----|---------------|----------------------|--------------------------|-------------------------|------------------------|------------------|
| **Just Press Record** | **$4.99 one-time** (no sub) | **Unlimited** | **Yes** — "record discreetly in the background," pause/resume | Share sheet (audio + text), **iCloud Drive / Files app**, print, USB; **URL scheme** | On-device, 30+ languages, editable, punctuation | **Best:** Siri, Action Button, Lock Screen, Control Center, Widget, 3D-Touch, URL scheme, Shortcuts |
| **Voice Record Pro** | **Free** (IAP only removes ad banner) | **Unlimited** (device space) | Background record; **lock-screen reliability not confirmed in 2026 sources** | Dropbox, Google Drive, OneDrive, Box, iCloud, **Amazon S3, custom FTP, WebDAV, "Post to any web-based script,"** email/SMS, local WiFi web server | None | Weak (no first-class Siri/Action Button) |
| **VoiceScriber AI** | Free trial → **$5.99/week or $49.99 lifetime** | **90 min cap per recording** ⚠ | Yes — continues on lock/app-switch; calls pause & resume | Share sheet (audio + text) one-tap | On-device, 100+ languages | Home-screen widget only |
| **Recorder Plus** | Free + IAP (edit $4.99/yr; **transcription is consumable, $4.99 / 20 hrs**) | Hours | Yes — record & playback in background | **Auto-backup to iCloud Drive folder**, plus FTP, WebDAV, Dropbox, Google Drive, Box | Consumable cloud service | Weak |
| **Wave (AI Note Taker)** | Free **30 min/month**; Pro **$11.67/mo** (annual) | Unlimited (Pro) | Yes | PDF / OneNote / email export, cross-device cloud sync | Cloud AI + summaries, speaker labels | Siri / Action Button; **also records phone calls (built-in dialer) & virtual meetings (bots/desktop)** |
| **Apple Voice Memos** | Free (built-in) | Unlimited | Yes, but a 2026 source flags background reliability as not fully dependable | Share sheet, iCloud | On-device (iOS 18+) | Action Button / Siri |

### Why Just Press Record over Voice Record Pro (the spec's current lead)

The deciding use case is *"an idea arrives while driving — start capturing without looking at the phone,
and trust it keeps recording locked/pocketed for as long as I ramble."* That rewards two things above all:
**(a) confirmed background/lock recording** and **(b) frictionless hands-free start.**

- **Just Press Record** nails both: background recording is an advertised, long-standing feature, and it
  exposes *every* Apple trigger surface — Siri phrase, Action Button, Lock Screen, Control Center, Widget,
  **and a URL scheme** (so a CarPlay "on connect" automation or a one-word Siri command can start it). It's
  a **$4.99 one-time** purchase, stores to **iCloud Drive** (feeds the drop-folder path for free), and the
  developer collects **zero** data. Its own on-device transcript is redundant with Speakr but harmless.
- **Voice Record Pro** is genuinely excellent *value* (free, unlimited, huge export list including a
  "post to any web script" hook that can in principle hit Speakr directly). But its hands-free story is
  thin, its UI is dated/ad-supported, and no 2026 source confirms rock-solid **locked-screen** capture.
  Keep it as the **free fallback** — especially if the "post to web script" export can be shaped into a
  multipart POST to Speakr (worth a spike; may not support Bearer headers cleanly).
- **VoiceScriber** and **Recorder Plus** are ruled out as primary: VoiceScriber caps recordings at
  **90 min** (kills a long ramble) and is subscription/expensive; Recorder Plus gates transcription behind
  consumable credits (irrelevant since Speakr transcribes, but the auto-iCLoud backup is a nice pattern).
- **Wave** is the standout **only** if you want it to double as a phone-call/meeting recorder — but it's a
  **$11.67/mo subscription** past 30 free minutes, so it's out for a cost-conscious personal tool.

---

## 2. Auto-ingest into self-hosted Speakr

Speakr shipped a first-class **Upload API** in **v0.8.15-alpha (2026-03-18)** — this is what makes clean
automation possible. Both ingest patterns below hit the same endpoint.

### Speakr upload endpoint (confirmed from official docs)

```
POST /api/v1/recordings/upload            # multipart/form-data
Authorization: Bearer <SPEAKR_API_TOKEN>  # or  X-API-Token: <token>
```

| Field | Req? | Notes |
|-------|------|-------|
| `file` | **yes** | the audio file (m4a/mp3/wav/etc.) |
| `notes` | no | free text — good for supersession breadcrumbs |
| `language` | no | ISO 639-1 hint (e.g. `en`) |
| `tag_ids[0]`, `tag_ids[1]`… | no | attach existing tag IDs (e.g. a "Raw Captures" tag) |
| `min_speakers` / `max_speakers` | no | diarization hints (1/1 for solo rambles) |
| `file_last_modified` | no | client mtime in ms epoch (preserves true capture time) |
| `keep_audio_only` | no | strip audio from video uploads |

Returns **`202 Accepted`** with recording metadata, status `PENDING`; transcription is queued
immediately. Tokens are created in **Account Settings → API Tokens** (choose "No expiration" for a
long-lived automation token). Interactive Swagger lives at **`/api/v1/docs`** on the instance — use it to
confirm field names against the exact deployed version before wiring the Shortcut.

> ⚠ **Note field names, not `title`/`meeting_date`.** The v0.8.15 *release notes* mention optional
> `title` and `meeting_date` form fields, but the published API reference lists only the fields above.
> Verify against your instance's `/api/v1/docs`; if `title` isn't accepted, pass the human title in
> `notes` and let Speakr AI-title the recording (or rename after).

### Pattern A (primary) — iOS Shortcut → multipart POST

iOS Shortcuts **can** do multipart uploads: the **Get Contents of URL** action supports
`POST/PUT/PATCH/DELETE`, custom **Headers**, and a **Request Body of type "Form"** — and *"to make a
multipart HTTP request, choose Form as the request body type and add files as field values"*
(Apple + Matthew Cassinelli's action reference confirm this). Recipe:

1. **Trigger:** Share sheet (`Receive audio from Share Sheet`) — or Siri phrase / Action Button.
2. `URL` → `https://transcripts.nextlevelguild.com/api/v1/recordings/upload`
3. `Get Contents of URL`:
   - Method: **POST**
   - Headers: `Authorization` = `Bearer <token>` *(store the token in a Shortcut variable or a
     Data-Jar/Keychain entry — do not hard-code in a shared shortcut)*
   - Request Body: **Form**
     - `file` → the **Shortcut Input** (the shared audio file) — added as a *file* field
     - `notes` → e.g. `stage:raw project:kids-mindset` (or ask-for-input)
     - `language` → `en`
4. Show/parse the `202` response for a confirmation.

One tap from the recorder's share sheet; Siri-triggerable ("Hey Siri, send to Speakr"); works with **any**
recorder that exposes a share sheet (Just Press Record, Voice Record Pro, VoiceScriber, Voice Memos).

**2026 gotchas / limits:**
- Store the Bearer token **outside** the shortcut body if you ever share/export it (credential hygiene).
- Large multi-hour files: the upload runs foreground while the Shortcut is open; very large files can be
  slow on cellular. Prefer WiFi for hour-plus captures, or use Pattern B.
- Shortcuts' multipart action is reliable but has minimal error UI — add a "Show Result" / notification
  step so a failed upload (e.g. 401/413) is visible, not silent.
- Speakr transcription still depends on the OpenAI-org credit fix (see spec §6) — a 202 means *queued*,
  not *transcribed*.

### Pattern B (zero-tap) — synced drop-folder + server watcher on Banner

1. Recorder writes to a synced folder: **Just Press Record → iCloud Drive**, or Recorder Plus → its
   auto-iCloud folder, or any app → a **Nextcloud** folder via the Nextcloud iOS app / Files provider.
2. **Banner** subscribes to that folder (Nextcloud client, `rclone` on a timer, or iCloud via a Mac relay).
3. A tiny **watch script** (`inotifywait` / Python `watchdog`) fires on new `*.m4a`, POSTs it to
   `/api/v1/recordings/upload` with the Bearer token + `tag_ids` for "Raw Captures," then moves the file
   to a `processed/` dir.

Fully hands-off after recording; also doubles as the generic "drop any audio (incl. meeting exports) →
KnowledgeStack" lane. Trade-off: more moving parts (sync client + watcher + de-dupe), and iCloud→Linux
sync is the awkward leg (Nextcloud or an FTP/WebDAV target the recorder writes to directly — Voice Record
Pro and Recorder Plus both speak FTP/WebDAV — sidesteps iCloud entirely).

> **Speakr also has native "watch folders"** (the v0.8.15 notes mention watch-folder auto-tagging +
> API-triggered processing). If Speakr can watch a path on Banner directly, Pattern B collapses to
> "sync the folder to where Speakr can see it" — no custom POST script. Confirm this in the deployed
> Speakr config; it's the cleanest option if available.

---

## 3. Free meeting auto-capture (Zoom / Meet / Jitsi) — verdict

**Verdict: Yes, but on the desktop, not on iOS — and it slots into the same Speakr ingest lane.**

- **Zoom's free plan has no native transcription** (needs paid Workplace/Pro+), and as of **2026-05-18**
  Zoom no longer lets free users save/download live captions. Most "free" third-party tools are trials or
  minute-capped (Otter, Tactiq 10/mo, etc.).
- The clean *free* pattern is a **system-audio recorder on the laptop** — it captures the same audio stream
  that reaches your speakers, so **no bot joins the call** and it works across Zoom/Meet/Teams/Jitsi
  identically:
  - **Meetily** — MIT, open-source, on-device Whisper/Parakeet, macOS + Windows (308k+ downloads).
  - **Meeting Transcriber** (`pasrom/meeting-transcriber`) — MIT, macOS, on-device WhisperKit/Parakeet,
    dual-track diarization, exports Markdown; auto-records detected Teams/Zoom/Webex calls.
  - **RecordMeeting** — Chrome extension, records in-tab (no bot), works on free accounts, exports MP4/MP3.
- **Both self-hosted recorders can export the raw audio**, which you then push through **Pattern A/B** into
  Speakr — so a meeting becomes just another audio drop. (They also transcribe locally, but Speakr keeping
  the canonical transcript is fine.)
- **iOS-only meeting capture:** for *in-person* meetings, Just Press Record / VoiceScriber capture ambient
  mic audio fine. For *platform calls* on the phone there is no reliable free way to grab the remote
  party's system audio — use the laptop. (Wave *can* record iPhone calls via a built-in dialer, but it's a
  paid subscription and out of scope for "won't pay.")

**Recommendation:** don't force meetings onto iOS. Use a free desktop system-audio recorder → export
audio → Speakr drop-folder. One ingest lane serves both rambles and meetings.

---

## 4. Hands-free start while driving (Siri) + safety

**It works and is well-supported in 2026** via Apple's **App Intents** framework (the same system behind
the Action Button, Widgets, and Shortcuts):

- **Just Press Record** registers Siri actions and a **URL scheme**, so you can:
  - Say **"Hey Siri, [your phrase]"** — rename the shortcut to a natural phrase ("start a brain dump").
  - Add it to the **Action Button** for a physical one-press start.
  - Build a **CarPlay automation**: Shortcuts → **Automation → Create Personal Automation → CarPlay →
    Connects → Run Immediately** (toggle "Ask Before Running" off / "Don't Ask") → *Start recording*. Now
    plugging into the car can auto-arm capture; a matching **Disconnects** automation can stop + trigger
    the Speakr upload.
- A **"Brain Dump Mode"** chained shortcut can, from one phrase: set a Focus/DND, start the recording, and
  (on stop) POST to Speakr — the Hedy and Driversnote guides both demonstrate this exact CarPlay + Siri
  pattern.

**Safety notes:**
- Prefer **voice ("Hey Siri") or the CarPlay-connect automation** over any on-screen tap — the whole point
  is eyes-on-road, hands-on-wheel.
- Set automations to **"Run Immediately / Don't Ask"** so there's no confirmation tap while driving.
- Siri may require an **unlock** if the shortcut must *open* an app; a background-only action (start
  recording via App Intent, no UI) avoids the unlock prompt — Just Press Record's URL-scheme/App-Intent
  start is designed for this.
- Confirm capture by **audio cue**, not by looking: add a "Play Sound" / spoken "recording started" step to
  the shortcut so you get eyes-free confirmation the mic is live.
- Don't review/scrub transcripts while moving — that's a post-drive task.

---

## Sources

- Apple — *Request your first API in Shortcuts* (POST/Form/File, multipart): https://support.apple.com/guide/shortcuts/request-your-first-api-apd58d46713f/ios
- Apple — *Use Siri in your car (CarPlay / Siri Eyes Free)*: https://support.apple.com/guide/iphone/use-siri-in-your-car-iph0aa8c80e6/ios
- Matthew Cassinelli — *Get Contents of URL* action ("choose Form … add files as field values" = multipart): https://matthewcassinelli.com/actions/get-contents-of-url/
- Steve Simkins — *API Calls in iOS Shortcuts* (2026): https://stevedylan.dev/posts/api-calls-in-ios-shortcuts/
- HeyDingus — *Uploading files to a CDN via Shortcuts* (worked multipart recipe): https://heydingus.net/blog/2021/6/shortcuts-tips-uploading-images-to-imagekit-for-blogging
- Speakr — *API Tokens* (Bearer / X-API-Token): https://murtaza-nasir.github.io/speakr/user-guide/api-tokens/
- Speakr — *API Reference* (`POST /api/v1/recordings/upload`, field list, 202): https://murtaza-nasir.github.io/speakr/user-guide/api-reference/
- Speakr — *v0.8.15-alpha release* (Upload API, watch-folder auto-processing): https://github.com/murtaza-nasir/speakr/releases/tag/v0.8.15-alpha
- Speakr — *Feature request: upload api* (#169, context/history): https://github.com/murtaza-nasir/speakr/issues/169
- Just Press Record — App Store ($4.99 one-time, unlimited, background, Siri/URL scheme): https://apps.apple.com/us/app/just-press-record/id1033342465
- Just Press Record — developer page (background recording, iCloud sync, hands-free Siri): https://www.openplanetsoftware.com/just-press-record/
- Just Press Record vs VoiceToNotes — 2026 review ($4.99 one-time, iCloud only): https://voicetonotes.ai/blog/just-press-record-vs-voicetonotes-review/
- Voice Record Pro — App Store (free, unlimited, FTP/WebDAV/"post to web script"): https://apps.apple.com/us/app/voice-record-pro/id546983235
- Voice Record Pro — pricing/features overview: https://smallusefultips.com/is-voice-record-pro-free/
- VoiceScriber — App Store (90-min cap, background, on-device): https://apps.apple.com/us/app/voicescriber-ai-offline-notes/id6736586779
- VoiceScriber — pricing ($5.99/wk or $49.99 lifetime): https://voicescriber.com/pricing
- Recorder Plus — iCloud auto-backup + FTP/WebDAV + consumable transcription: https://recorderplus.com/?ht_kb=transcribe-service
- Wave — pricing (free 30 min/mo; Pro $11.67/mo) & phone-call/meeting recording: https://wave.co/pricing , https://wave.co/use-cases/phone-call-recorder-iphone
- Zapier — *6 best iPhone voice recording apps in 2026*: https://zapier.com/blog/best-iphone-voice-recorder/
- Granola — *How to transcribe a Zoom meeting for free (2026)* (Zoom free-plan limits, caption save removed 2026-05-18): https://www.granola.ai/blog/how-to-transcribe-a-zoom-meeting-for-free-5-methods-that-actually-work-in-2026
- Meetily — bot-free, on-device meeting recorder (MIT): https://meetily.ai/bot-free
- Meeting Transcriber (`pasrom/meeting-transcriber`) — MIT, on-device, exports Markdown: https://github.com/pasrom/meeting-transcriber
- RecordMeeting — in-tab (no-bot) free meeting recorder, exports MP4/MP3: https://recordmeeting.com/meeting-recorder
- Hedy AI — Siri Shortcuts hands-free / CarPlay pattern (2026): https://www.hedy.ai/post/hedy-siri-shortcuts-hands-free-meetings/
- Driversnote — CarPlay "Connects → Run Immediately" personal-automation recipe: https://driversnote.helpscoutdocs.com/article/151-use-driversnote-with-carplay-and-siri
- WebKit #226620 — background mic suspension on iOS (structural web/PWA limitation; premise): https://bugs.webkit.org/show_bug.cgi?id=226620

_Primary research via Exa (docker-mcp-gateway). Compiled 2026-07-12._
