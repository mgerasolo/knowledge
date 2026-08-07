# Transcript Quality Diagnostic Report

**Date:** 2026-03-31
**Database:** SurrealDB at 10.0.0.33:5040 (knowledge/transcripts)
**Corpus:** 83,528 segments across 1,011 videos
**Method:** 100 random segments sampled across 5 content domains, analyzed by GPT-4o-mini, then validated with full-database term counts

---

## Executive Summary

**32% of sampled segments contain at least one speech-to-text error.** The error rate varies dramatically by content domain -- AI/coding content has an 80% error rate while motivational content is nearly clean. The most damaging errors are **product name substitutions** (Claude Code, ChatGPT, OpenClaw) which directly corrupt the most searchable terms in the corpus.

**Recommendation:** A **seed dictionary + LLM correction pipeline** is needed. A simple find-and-replace dictionary handles the high-volume product name errors (covering ~70% of impactful errors), but medical/scientific terms and contextual errors need LLM-assisted correction.

---

## Overall Statistics

| Metric | Value |
|--------|-------|
| Total segments in database | 83,528 |
| Total videos | 1,011 |
| Segments sampled for analysis | 100 |
| Clean segments (no errors) | 68 (68%) |
| Segments with 1+ errors | 32 (32%) |
| Total individual errors found | 37 |
| Average segment length | ~480 characters |

## Error Rate by Content Domain

| Domain | Error Rate | Segments with Errors | Notes |
|--------|-----------|---------------------|-------|
| **AI/Coding** | **80%** | 16/20 | Product names consistently mangled |
| **Health/Science** | **55%** | 11/20 | Medical terminology truncated or phonetically garbled |
| **Politics/Culture** | **15%** | 3/20 | Mostly encoding artifacts on non-English words |
| **Business/Finance** | **10%** | 2/20 | Occasional name errors |
| **Mindset/Motivation** | **0%** | 0/20 | Simple vocabulary, rarely technical |

**Key insight:** Error rate correlates directly with technical vocabulary density. The more jargon-heavy the content, the worse the transcription.

---

## Top Error Patterns (Database-Wide Counts)

### Tier 1: High-Volume Product Name Errors

These are the most damaging errors because they corrupt the exact terms users would search for.

| Error Form | Correct Form | Occurrences | Impact |
|-----------|-------------|-------------|--------|
| `cloud code` (lowercase) | Claude Code | **504** | Invisible to "Claude Code" search |
| `open claw` / `Open Claw` | OpenClaw | **535** | Splits search results |
| `chat GBT` / `chat gbt` | ChatGPT | **145** | Invisible to ChatGPT search |
| `Cloud Code` (capitalized) | Claude Code | **133** | Partial match only |
| `Chad GPT` | ChatGPT | **60** | Completely wrong name |
| `clawbot` | ClawdBot | **15** | Drops the "d" |
| `anthropic` (lowercase) | Anthropic | **156** | Case-sensitivity issue |

**Total product name errors: ~1,548 segments affected** (1.9% of corpus, but concentrated in the most valuable AI content)

### Tier 2: Medical/Scientific Term Errors

| Error Form | Correct Form | Occurrences | Notes |
|-----------|-------------|-------------|-------|
| `Vegas nerve` | vagus nerve | **42** | Classic homophone substitution |
| `vegus` | vagus | **6** | Phonetic misspelling |
| `paretic` | parasympathetic | rare | Truncation |
| `sleep AP` | sleep apnea | rare | Truncation |
| `hypercchloric` | hypercaloric | rare | Garbled |

### Tier 3: Encoding Artifacts

| Pattern | Occurrences | Example |
|---------|-------------|---------|
| `Â` character | **3,422 segments (4.1%)** | `60Â°` instead of `60°` |
| `Ã` character | **45 segments** | `FÃ¼hrerbunker` instead of `Fuhrerbunker` |

These are UTF-8 encoding errors, not STT errors. Likely introduced during transcript extraction or database ingestion.

### Tier 4: Speech Disfluencies (Not Errors Per Se)

| Pattern | Occurrences | % of Corpus |
|---------|-------------|-------------|
| `uh` filler | **13,208** | 15.8% |
| `um` filler | **9,242** | 11.1% |
| `like` (filler usage) | **35,998** | 43.1% |
| `you know` | **7,953** | 9.5% |
| `the the` (stutter) | **3,900** | 4.7% |

These aren't technically errors -- they're faithful transcription of spoken disfluencies. However, they add noise for RAG retrieval. Cleaning them could improve embedding quality.

---

## Sample Corrections Found

### AI/Coding Domain (worst affected)

| Segment Context | Error | Correction | Confidence |
|----------------|-------|------------|------------|
| "...the minute that cloud code finished, it was just a bunch of errors..." | `cloud code` | `Claude Code` | High |
| "...They were not possible with Chad GPT..." | `Chad GPT` | `ChatGPT` | High |
| "...go to your open claw and say..." | `open claw` | `OpenClaw` | High |
| "...spin this up... T-Mox... green little footer..." | `T-Mox` | `tmux` | Medium |
| "...agents.mnd file..." | `agents.mnd` | `agents.md` | High |
| "...chat GBT..." | `chat GBT` | `ChatGPT` | High |
| "...heruristic..." | `heruristic` | `heuristic` | High |
| "...npm rundev..." | `npmi` | `npm i` | Medium |

### Health/Science Domain

| Segment Context | Error | Correction | Confidence |
|----------------|-------|------------|------------|
| "...hacking the Vegas nerve..." | `Vegas nerve` | `vagus nerve` | High |
| "...edamame..." appeared as | `edetamame` | `edamame` | High |
| "...sleep AP..." | `sleep AP` | `sleep apnea` | High |
| "...60Â°ree..." | `60Â°ree` | `60-degree` | High |

### Business/Finance Domain

| Error | Correction | Confidence |
|-------|------------|------------|
| `Black Rockck` | `BlackRock` | High |
| `Jim Ran` | `Jim Rohn` | Medium |

---

## Punctuation and Formatting Notes

| Feature | Coverage |
|---------|----------|
| Periods present | 95.4% of segments |
| Commas present | 88.3% of segments |
| Question marks | 37.3% of segments |
| Exclamation marks | 0.1% of segments |

The transcripts generally have punctuation (YouTube auto-captions include it), but capitalization is inconsistent and paragraph breaks are absent.

---

## Correction Effort Recommendation

### Phase 1: Seed Dictionary (Low effort, high impact)

A simple find-and-replace dictionary handles the highest-volume errors. Estimated coverage: **~1,600 segments fixed**.

```yaml
# seed-corrections.yaml
product_names:
  "cloud code": "Claude Code"
  "Cloud Code": "Claude Code"
  "open claw": "OpenClaw"
  "Open Claw": "OpenClaw"
  "chat GBT": "ChatGPT"
  "chat gbt": "ChatGPT"
  "Chad GPT": "ChatGPT"
  "clawbot": "ClawdBot"
  "Clawbot": "ClawdBot"

medical_terms:
  "Vegas nerve": "vagus nerve"
  "vegus nerve": "vagus nerve"
  "vegus": "vagus"

people:
  "Jim Ran": "Jim Rohn"
```

**Effort:** 1-2 hours to build, test, and apply.
**Risk:** Low -- these are unambiguous substitutions.

### Phase 2: Encoding Cleanup (Low effort, medium impact)

Fix the 3,422 segments with UTF-8 encoding artifacts. This is a character-level fix, not NLP.

**Effort:** 30 minutes.
**Impact:** 4.1% of corpus cleaned.

### Phase 3: LLM-Assisted Correction (Medium effort, medium impact)

For domain-specific terms (medical, technical) that can't be handled by dictionary, run segments through GPT-4o-mini with domain context. Focus on health-science content first (55% error rate).

**Effort:** 4-8 hours for pipeline + review.
**Risk:** Medium -- needs human spot-checking to avoid over-correction.

### Phase 4: Disfluency Cleaning (Optional, low priority)

Strip filler words (`um`, `uh`, `the the`) to improve embedding quality. This affects 15-43% of segments but the impact on RAG quality is uncertain.

**Effort:** 2 hours.
**Risk:** Could remove meaningful hesitations in interview content.

---

## Key Takeaway

The transcript corpus is **usable but noisy**. The single biggest problem is product name corruption -- `Claude Code` appears as `cloud code` in 504 segments, making those segments invisible to anyone searching for Claude Code content. A seed dictionary costing 1-2 hours of work would fix the majority of high-impact errors. The long tail of medical/scientific errors needs a more sophisticated approach but affects a smaller portion of the corpus.

**Priority order:** Seed dictionary > Encoding cleanup > LLM correction > Disfluency cleaning.
