# KnowledgeStack Header Standard

Every web-facing part of KnowledgeStack presents as one central app with a
shared two-tier header (Matt directive 2026-08-14).

## The two tiers

| Tier | Contents | Height |
|---|---|---|
| **1 — the app** | `KnowledgeStack` brand (links to the hub `/`) + every part: Enroll, Lecture, Ingest, Transcript. Current part highlighted with a light background + cyan underline. | 46px |
| **2 — the part** | Pages within the current part, plus direct action items (e.g. Enroll's `+ Add Channel`, `+ Enroll Video` deep links `?add=1` / `?enroll=1`). | 48px |

## Rules

- **Font:** Roboto Condensed (Google Fonts), both tiers. Body text stays on the
  system stack.
- **Colors:** RGB only per `matt-design-preferences.md` #1. Tier 1 background
  `rgb(7, 12, 24)`, tier 2 `rgb(30, 41, 59)`, brand/current accents
  `rgb(56, 189, 248)`.
- **Part names are the product sub-names** — Enroll, Lecture, Ingest,
  Transcript — never internal service names ("admin-api") or host/domain names.
- **Tier-1 part links are absolute paths** on the unified domain
  (`https://knowledge.nextlevelfoundry.com/<part>/`). Tier-2 links use the
  request-aware `url_prefix` so the same app works at any mount point.
- **The hub (landing page) carries tier 1 only** — it has no "part pages".
- **Lecture is third-party (Speakr)** — we cannot inject this header without a
  wrapper (iframe shell or proxy injection). Tracked as an open idea; until
  then Lecture participates via tier-1 links from the parts we control.

## Canonical implementation

`src/admin/templates/base.html` (Enroll) is the reference — copy its
`.nav-tier1` / `.nav` blocks when giving another part the header. If a third
copy appears, extract a shared include instead.
