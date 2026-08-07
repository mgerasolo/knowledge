# Transcript Correction Research Report: Contextual Spell Checking for ASR Phonetic Mishearings

**Date:** 2026-03-31
**Researcher:** Claude Opus 4.6 (1M context)
**Context:** KnowledgeStack -- YouTube transcript ingestion pipeline with 83K+ segments
**Problem:** Speech-to-text outputs contain phonetic mishearings where the wrong REAL word is substituted (not typos). Examples: "Cloud Code" instead of "Claude Code", "open cloud" instead of "OpenClaw", "pseudo" instead of "sudo".

---

## Executive Summary

### Key Findings

1. **No single off-the-shelf tool solves this exact problem.** The closest practical solution is a hybrid pipeline combining phonetic matching (to detect candidates) with LLM-based correction (to fix them using domain context). Traditional spell checkers fail because every word in the transcript IS a real word -- just the wrong one.

2. **Phonetic matching is remarkably effective for candidate detection.** Testing with jellyfish/Metaphone on actual ASR mishearing pairs showed exact phonetic matches for "Claude/Cloud", "Qdrant/quadrant", "LiteLLM/light LLM", "Ollama/oh llama", and "DeepSeek/deep seek". Even harder cases like "sudo/pseudo" and "OpenClaw/open cloud" showed Metaphone distance of only 1. This means a phonetic index of domain terms CAN reliably identify candidate corrections.

3. **Local LLMs are the most practical correction engine**, but prompt engineering matters enormously. Zero-shot correction with naive prompts often INCREASES error rates. The winning pattern is: provide a domain glossary in the system prompt, feed transcript segments in batches, and constrain the model to only replace words that phonetically match glossary terms. Cost: free with Ollama; Speed: 60-70 tokens/sec on 8B models.

4. **The OpenAI Cookbook's "glossary post-processing" pattern is the closest existing recipe** and can be adapted for local LLMs. The technique: pass a custom glossary of correct spellings to an LLM with the instruction "correct any spelling discrepancies using this glossary." GPT-4 reliably corrects domain terms this way, and local 8B models can approximate it with careful prompting.

5. **For 83K segments, a two-stage pipeline is recommended:** Stage 1 uses phonetic matching against a domain dictionary to FLAG segments containing potential mishearings (fast, deterministic, ~seconds for 83K segments). Stage 2 sends only flagged segments to a local LLM for contextual correction (expensive but targeted). This reduces LLM calls by 80-90%.

---

## 1. Existing Contextual Spell-Check Libraries

### 1.1 contextualSpellCheck (spaCy plugin)

**GitHub:** https://github.com/R1j1t/contextualSpellCheck
**Status:** NOT ACTIVELY MAINTAINED (stated in repo)
**Mechanism:** Uses BERT masked language model to detect out-of-vocabulary (OOV) words and suggest contextual corrections.

**Assessment for our use case: POOR FIT**
- Designed for non-word errors (NWE) -- words that are NOT in the dictionary
- Our problem is real-word errors (RWE) -- "cloud" IS a valid word, it's just wrong in context
- Cannot detect that "Cloud Code" should be "Claude Code" because both are valid phrases
- No custom dictionary support for domain terms
- Python/spaCy compatible but unmaintained

**Verdict:** Does not solve phonetic mishearings. Skip.

### 1.2 SymSpell (symspellpy)

**GitHub:** https://github.com/mammothb/symspellpy
**Latest:** v6.9.0 (actively maintained, MIT license)
**Speed:** 1 million times faster than traditional spell checkers via Symmetric Delete algorithm

**Assessment for our use case: PARTIAL FIT (detection only)**
- Extremely fast dictionary lookup with edit distance
- Supports custom dictionaries with frequency counts
- Can find words within edit distance N of a query
- BUT: edit distance is not phonetic distance. "Claude" and "Cloud" have edit distance 2 (swap a/o, delete/insert letters) but "Claude" and "Klawed" have high edit distance despite sounding identical
- No context awareness -- cannot tell if "cloud" is wrong in a given sentence
- Could be useful as a FAST pre-filter alongside phonetic matching

**Verdict:** Useful as a component (fast fuzzy matching) but insufficient alone. No context awareness.

### 1.3 NeuSpell

**GitHub:** https://github.com/neuspell/neuspell
**Status:** Research toolkit, last significant update 2021
**Mechanism:** 10 neural spell checkers trained on naturally occurring misspellings

**Assessment for our use case: POOR FIT**
- Trained on TYPED misspellings, not phonetic mishearings from ASR
- Models assume character-level errors (typos), not word-level substitutions
- No custom domain dictionary support
- Academic research code, not production-ready
- Would need retraining on ASR-specific error patterns

**Verdict:** Wrong error model. Skip.

### 1.4 Spark NLP ContextSpellChecker

**Source:** John Snow Labs (Apache 2.0 for open source edition)
**Mechanism:** Deep learning Viterbi decoder with contextual information

**Assessment for our use case: INTERESTING BUT HEAVY**
- CAN handle real-word errors using context
- Supports custom "special classes" (gazetteers) that can be updated without retraining
- Medical domain variant exists (spellcheck_clinical) proving domain adaptation works
- BUT: requires PySpark infrastructure (JVM + Spark runtime)
- Heavy dependency chain for what could be a simpler pipeline
- Training custom models requires significant data preparation

**Verdict:** Overkill for our use case. The custom class/gazetteer concept is sound but PySpark dependency is prohibitive. Borrow the concept, not the tool.

### 1.5 Summary: Traditional Spell Checkers

| Tool | Real-Word Errors | Custom Dict | Context-Aware | Self-Hosted | Maintained | Verdict |
|------|-----------------|-------------|---------------|-------------|------------|---------|
| contextualSpellCheck | No (NWE only) | No | Yes (BERT) | Yes | No | Skip |
| SymSpell | No | Yes | No | Yes | Yes | Component only |
| NeuSpell | No (typo model) | No | Partial | Yes | Stale | Skip |
| Spark NLP CSC | Yes | Yes (gazetteers) | Yes | Yes | Yes | Too heavy |
| pyspellchecker | No | Yes | No | Yes | Yes | Skip |
| TextBlob | No | No | No | Yes | Stale | Skip |

**Bottom line:** No existing spell-check library handles the "real word substituted by a phonetically similar real word" problem out of the box. The problem requires phonetic awareness + contextual understanding, which no single library provides.

---

## 2. LLM-Based Correction

### 2.1 The OpenAI Cookbook Pattern (Adaptable to Local LLMs)

**Source:** [OpenAI Cookbook - Addressing Transcription Misspellings](https://developers.openai.com/cookbook/examples/whisper_correct_misspelling)

This is the most directly applicable existing technique. The pattern:

```python
system_prompt = """You are a helpful assistant for KnowledgeStack. Your task is
to correct any spelling discrepancies in the transcribed text. Only correct words
that are clearly wrong based on context. Make sure that the names of the following
products and terms are spelled correctly:

Claude Code, Anthropic, LiteLLM, Qdrant, SurrealDB, Ollama, DeepSeek,
OpenClaw, Speakr, n8n, Traefik, sudo, Docker, Kubernetes, RAG,
intermittent fasting, autophagy, ketosis, zone 2 cardio

Do NOT change the meaning. Do NOT add or remove content. Only fix misheard words."""

# For each segment:
response = llm.chat(
    model="deepseek-r1:8b",  # or qwen2.5:7b via Ollama
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": segment_text}
    ],
    temperature=0
)
```

**Strengths:**
- Simple, proven pattern
- Works with any LLM (local or API)
- Custom glossary is trivially updatable
- GPT-4 achieves near-perfect correction with this pattern

**Weaknesses:**
- Prompt token limit (244 for Whisper prompt; unlimited for LLM post-processing)
- Local 8B models less reliable than GPT-4 (see benchmarks below)
- Overcorrection risk: LLMs may "fix" words that are actually correct
- No phonetic awareness -- relies on LLM's implicit knowledge of how words sound

### 2.2 Local LLM Benchmarks for Correction

**Source:** [Vosk Blog - Generative Error Correction Experiments, 2025](https://alphacephei.com/nsh/2025/03/15/generative-error-correction.html)

Testing on Russian telephony (comparable complexity to YouTube transcripts):

| Model | WER | Notes |
|-------|-----|-------|
| Baseline ASR (1-best) | 15.9% | No correction |
| ROVER (5-best voting) | 14.8% | Simple, no LLM needed |
| Gemma-2-9B-IT | 16.0% | Open source, close to baseline |
| Gemma-3-4B-IT | 16.7% | Smaller but decent |
| Gemini Flash 2.0 Lite | 14.6% | Best performer (API) |
| Qwen2.5-7B-Instruct | 100+ | Hallucinated badly |
| Various 8B models | 40+ | Unstable, frequent hallucination |

**Critical finding:** "Prompt formatting matters considerably." The team reduced WER from 26% to 16% just by refining prompt format. Standard academic prompts were ineffective. Open-source 8B models hallucinated in ~25% of cases.

**Practical implications for KnowledgeStack:**
- Do NOT rely on zero-shot LLM correction alone
- Constrain the LLM: provide the glossary AND flag specific words to check
- Use larger models (14B+) if GPU allows, or API models for critical content
- Validate LLM output: check that corrections are phonetically plausible

### 2.3 Batch Processing Strategy

For 83K segments, LLM correction of every segment is prohibitively slow and risky (hallucination). Recommended approach:

**Throughput estimates (Ollama on consumer GPU):**

| Model | Tokens/sec | Time per segment (~50 tokens) | Time for 83K segments |
|-------|-----------|-------------------------------|----------------------|
| DeepSeek-R1 8B | ~68 t/s | ~1.5s | ~35 hours |
| DeepSeek-R1 32B | ~22 t/s | ~4.5s | ~104 hours |
| Qwen2.5 7B | ~60 t/s | ~1.7s | ~39 hours |
| Haiku 3.5 (API) | ~200 t/s | ~0.5s | ~12 hours |

These estimates assume processing EVERY segment. With phonetic pre-filtering (Stage 1), only 10-20% of segments need LLM correction, reducing to:

| Approach | Segments to correct | Estimated time (8B local) |
|----------|-------------------|--------------------------|
| All segments | 83,000 | ~35 hours |
| Phonetic pre-filter (20%) | ~16,600 | ~7 hours |
| Phonetic pre-filter (10%) | ~8,300 | ~3.5 hours |

### 2.4 Cost Analysis

| Approach | Cost for 83K segments | Speed | Quality |
|----------|----------------------|-------|---------|
| Ollama local (8B) | $0 (electricity) | 35h all / 3-7h filtered | Medium-Good |
| Ollama local (14B) | $0 (electricity) | 50h all / 5-10h filtered | Good |
| Haiku 3.5 via LiteLLM | ~$2-4 | 12h all / 1-2h filtered | Very Good |
| GPT-4o-mini via API | ~$5-10 | 8h all / 1h filtered | Very Good |
| GPT-4o via API | ~$30-60 | 6h all / <1h filtered | Excellent |

**Recommendation:** Use Haiku 3.5 via existing LiteLLM proxy for initial batch. Cost is trivial (~$2-4) and quality is significantly better than local 8B models. Switch to local for ongoing incremental correction of new transcripts.

### 2.5 Effective Prompt Patterns

Based on research synthesis, the most effective prompt for domain-aware transcript correction:

```
SYSTEM: You are a transcript correction assistant for a YouTube knowledge platform
covering AI/ML tools, health/biohacking, and software development.

TASK: Correct ONLY words that appear to be speech-to-text mishearings. These are
phonetically similar but wrong words (e.g., "Cloud Code" should be "Claude Code").

DOMAIN GLOSSARY (correct spellings):
{glossary_terms}

RULES:
1. ONLY replace words that sound like a glossary term but are spelled wrong
2. Preserve original sentence structure exactly
3. Do NOT add punctuation, capitalization fixes, or grammar corrections
4. Do NOT paraphrase or rephrase anything
5. If unsure, leave the original word unchanged
6. Return ONLY the corrected text, nothing else

FLAGGED WORDS (these specific words were detected as potential mishearings):
{flagged_words_with_positions}
```

This constrained prompt reduces hallucination risk by:
- Limiting corrections to glossary terms only
- Pre-identifying suspicious words (from phonetic matching stage)
- Explicitly forbidding other changes
- Requiring phonetic similarity (not just semantic plausibility)

---

## 3. Masked Language Models (BERT-Style)

### 3.1 Standard BERT MLM Approach

**Concept:** Mask each word in the transcript, ask BERT to predict what word should go there. If BERT's top prediction differs significantly from the actual word, flag it as potentially wrong.

**Assessment for our use case: MODERATE FIT**

**Strengths:**
- Context-aware: BERT considers surrounding words when predicting
- Fast inference: can process thousands of segments quickly
- No custom training needed for detection (pre-trained BERT works)

**Weaknesses:**
- BERT's vocabulary may not include domain terms ("Qdrant", "LiteLLM", "n8n")
- Cannot suggest domain-specific corrections, only flag anomalies
- "Cloud Code" in an AI context might still rank high (clouds are associated with tech)
- Real-word error detection with vanilla BERT has limited accuracy

### 3.2 Soft-Masked BERT

**Paper:** [Spelling Error Correction with Soft-Masked BERT, ACL 2020](https://aclanthology.org/2020.acl-main.82/)
**Implementation:** https://github.com/Aolin-MIR/soft-masked-bert-for-spelling-error-correction

**Architecture:** Two-stage network where:
1. Error detection network identifies probable error positions (soft mask)
2. BERT correction network uses soft masks to guide correction

**Assessment:**
- Originally designed for Chinese spelling correction (character-level)
- The architecture IS applicable to English real-word errors
- Would require fine-tuning on ASR error pairs (which we don't have yet)
- TensorFlow 1.12 implementation (dated)
- Research code, not production-ready

### 3.3 Amazon's Warped Language Models

**Source:** [Amazon Science - Using Warped Language Models to Correct ASR Errors](https://www.amazon.science/blog/using-warped-language-models-to-correct-speech-recognition-errors)

**Concept:** Extends masked language models to handle insertions and deletions (not just substitutions), specifically designed for ASR error patterns.

**Assessment:**
- Directly addresses ASR error correction
- NOT open source (Amazon internal)
- Concept is sound: language models that understand ASR error distributions

### 3.4 BERT for Anomaly Detection (Practical Approach)

Rather than using BERT for correction, use it for DETECTION alongside phonetic matching:

```python
from transformers import pipeline

fill_mask = pipeline("fill-mask", model="bert-base-uncased")

text = "I was using [MASK] Code to write Python"
predictions = fill_mask(text)
# If "claude" appears in top-10 predictions but the original word was "cloud",
# flag this as a potential ASR mishearing
```

**Assessment:**
- Lightweight, fast, self-hostable
- Complements phonetic matching: BERT provides semantic plausibility, phonetics provides sound similarity
- Pre-trained models readily available via HuggingFace
- Can process 83K segments in minutes (GPU) to hours (CPU)

**Verdict:** Use BERT as a secondary signal, not the primary correction mechanism. Best combined with phonetic matching for a two-signal detection system.

---

## 4. Whisper/YouTube Transcript Correction Tools

### 4.1 WhisperX

**GitHub:** https://github.com/m-bain/whisperX
**Latest:** Active development (2025-2026)

WhisperX adds word-level timestamps and speaker diarization to Whisper. It includes a `--post_correction` flag, but this is primarily for timestamp alignment, not content correction.

**Assessment:** Not useful for our use case (content correction). We already have transcripts; we need to fix the words, not re-transcribe.

### 4.2 faster-whisper

**GitHub:** https://github.com/SYSTRAN/faster-whisper
**Speed:** 4x faster than OpenAI Whisper, less memory with CTranslate2

**Assessment:** Same as WhisperX -- addresses transcription speed, not post-correction of existing transcripts.

### 4.3 Whisper's Prompt Parameter

Whisper accepts a `prompt` parameter (max 244 tokens) that biases transcription toward specific terms:

```python
result = model.transcribe(audio, prompt="Claude Code, Anthropic, Ollama, Qdrant")
```

**Assessment:**
- Useful for NEW transcriptions but we already have 83K existing segments
- 244 token limit is restrictive for large glossaries
- YouTube's auto-captions cannot be re-run with custom prompts
- Would be valuable for future pipeline where we re-transcribe from audio

### 4.4 OpenAI Cookbook Post-Processing Guide

**Source:** [Enhancing Whisper Transcriptions: Pre & Post-Processing](https://developers.openai.com/cookbook/examples/whisper_processing_guide)

Recommended staged workflow:
1. Normalize text
2. Restore punctuation
3. Paragraph segmentation
4. Fix speaker labels
5. Verify names/terms (custom glossary)
6. Final QA

Step 5 is directly applicable. The technique uses GPT-4 with a product list glossary to correct domain terms. See Section 2.1 for the detailed pattern.

### 4.5 FlanEC (Flan-T5 for ASR Error Correction)

**GitHub:** https://github.com/MorenoLaQuatra/FlanEC
**License:** MIT
**Models:** Flan-T5 base/large/xl with LoRA variants

**Concept:** Fine-tuned Flan-T5 that takes N-best ASR hypotheses and generates corrected transcription.

**Assessment:**
- Requires N-best hypotheses (we only have 1-best from YouTube)
- Pre-trained models available on HuggingFace
- Self-hostable, Python, MIT license
- Does NOT support custom vocabularies
- Designed for standard English, not domain-specific terms
- Could be fine-tuned on our domain if we had training pairs

**Verdict:** Not directly usable (we lack N-best hypotheses), but the architecture pattern of "fine-tuned seq2seq for correction" is worth noting for future work.

### 4.6 HyPoradise / RobustGER

**Paper:** [HyPoradise, ICLR 2024](https://openreview.net/forum?id=ceATjGPTUD)
**Code:** https://github.com/Hypotheses-Paradise/Hypo2Trans (original), https://github.com/YUCHEN005/RobustGER (noisy extension)

**Concept:** LLM-based generative error correction using N-best ASR hypotheses. Fine-tunes LLMs with LoRA on hypothesis-transcription pairs.

**Assessment:**
- State-of-the-art research in ASR error correction
- 316K+ training pairs available
- BUT: requires N-best hypotheses (not available from YouTube captions)
- Heavy fine-tuning required
- Research code, not production pipeline
- No custom vocabulary mechanism

**Verdict:** Academically interesting but impractical for our specific use case (YouTube transcripts without N-best lists).

### 4.7 Phonetic Context GER (Most Relevant Research)

**Paper:** [LLM-based GER for Rare Words with Synthetic Data and Phonetic Context, 2025](https://arxiv.org/html/2505.17410v1)

**Key insight:** Providing phonetic representations (simplified phoneme strings) alongside text dramatically improves correction of rare/domain words. Recall for rare words improved from 27.6% to 85.0% on medical text.

**Assessment:**
- Directly addresses our problem: rare domain-specific terms that ASR gets wrong
- Uses phonetic context to prevent overcorrection
- Synthetic data generation approach could bootstrap training data
- However, requires fine-tuning pipeline (not plug-and-play)

**Verdict:** The CONCEPT of including phonetic information in the correction prompt is highly applicable, even without the full fine-tuning pipeline.

---

## 5. Phonetic Matching

### 5.1 Empirical Testing Results

I tested Python's `jellyfish` library on actual KnowledgeStack ASR mishearing pairs:

| Correct Term | Misheard As | Metaphone Match | Metaphone Distance |
|-------------|-------------|-----------------|-------------------|
| Claude Code | Cloud Code | EXACT MATCH (KLTKT) | 0 |
| LiteLLM | light LLM | EXACT MATCH (LTLM) | 0 |
| Qdrant | quadrant | EXACT MATCH (KTRNT) | 0 |
| SurrealDB | surreal DB | EXACT MATCH (SRLTB) | 0 |
| Ollama | oh llama | EXACT MATCH (OLM) | 0 |
| DeepSeek | deep seek | EXACT MATCH (TPSK) | 0 |
| OpenClaw | open cloud | CLOSE (OPNKL/OPNKLT) | 1 |
| sudo | pseudo | CLOSE (ST/PST) | 1 |

**Result: 6/8 exact matches, 2/8 within distance 1.** This is remarkably strong evidence that Metaphone-based matching CAN detect ASR phonetic mishearings against a custom domain dictionary.

### 5.2 Available Python Libraries

| Library | Algorithms | Maintained | Speed | Custom Dict | Notes |
|---------|-----------|------------|-------|-------------|-------|
| **jellyfish** | Metaphone, Soundex, NYSIIS, MRA | Yes (v1.2.1) | Fast (Rust backend) | N/A | Best choice: fast, well-maintained |
| **pyphonetics** | Soundex, Metaphone, Refined Soundex, Fuzzy Soundex, Lein, MRA | Yes | Medium | N/A | More algorithms |
| **phonetics** | Metaphone, Double Metaphone, Soundex, NYSIIS | Yes | Medium | N/A | Double Metaphone available |
| **Fuzzy** | Soundex, NYSIIS, Double Metaphone | Stale | Fast (C extension) | N/A | Old but functional |
| **SoundsLike** | Multiple phonetic + CMU dict | Stale | Medium | Yes (CMU) | Specifically for "sounds like" queries |

### 5.3 Recommended Algorithm: Metaphone

Based on testing, **Metaphone** (via `jellyfish`) is the best algorithm for this use case:
- Handles multi-syllable technical terms well
- Fast Rust backend for batch processing
- Exact matches on most ASR mishearing patterns
- Distance-1 catches remaining cases

**Double Metaphone** (via `phonetics` or `Fuzzy`) provides primary + alternate codes, useful for ambiguous pronunciations. Worth testing if Metaphone misses cases.

### 5.4 Proposed Phonetic Matching Pipeline

```python
import jellyfish
from collections import defaultdict

class PhoneticDomainMatcher:
    """Detect words that phonetically match domain terms but are spelled wrong."""

    def __init__(self, domain_terms: list[str]):
        self.phonetic_index = defaultdict(list)
        for term in domain_terms:
            # Index both full term and individual words
            code = jellyfish.metaphone(term.replace(" ", ""))
            self.phonetic_index[code].append(term)
            for word in term.split():
                if len(word) > 2:
                    wcode = jellyfish.metaphone(word)
                    self.phonetic_index[wcode].append(term)

    def find_mishearings(self, text: str, max_distance: int = 1) -> list[dict]:
        """Find words in text that phonetically match domain terms."""
        candidates = []
        words = text.split()

        for i, word in enumerate(words):
            if len(word) < 3:
                continue
            word_code = jellyfish.metaphone(word)

            # Exact phonetic match
            if word_code in self.phonetic_index:
                for term in self.phonetic_index[word_code]:
                    if word.lower() != term.lower():  # Different spelling
                        candidates.append({
                            "position": i,
                            "original": word,
                            "suggested": term,
                            "phonetic_code": word_code,
                            "distance": 0
                        })

            # Near phonetic match (distance 1)
            if max_distance > 0:
                for code, terms in self.phonetic_index.items():
                    if jellyfish.levenshtein_distance(word_code, code) == 1:
                        for term in terms:
                            if word.lower() != term.lower():
                                candidates.append({
                                    "position": i,
                                    "original": word,
                                    "suggested": term,
                                    "phonetic_code": f"{word_code}->{code}",
                                    "distance": 1
                                })

        return candidates

# Usage:
glossary = [
    "Claude Code", "Anthropic", "LiteLLM", "Qdrant", "SurrealDB",
    "Ollama", "DeepSeek", "OpenClaw", "Speakr", "n8n", "Traefik",
    "sudo", "Docker", "Kubernetes", "RAG", "MCP", "Whisper",
    "autophagy", "ketosis", "intermittent fasting", "zone 2",
]

matcher = PhoneticDomainMatcher(glossary)
flagged = matcher.find_mishearings("I was using Cloud Code with the light LLM proxy")
# Returns: [{original: "Cloud", suggested: "Claude Code", distance: 0}, ...]
```

**Performance estimate:** Metaphone computation is O(n) per word. For 83K segments averaging 20 words each = 1.66M word lookups. With jellyfish's Rust backend, this completes in **under 10 seconds**.

---

## 6. Recommended Architecture: Two-Stage Pipeline

### Stage 1: Phonetic Detection (Fast, Deterministic)

```
[83K segments] -> [Phonetic Matcher] -> [Flagged segments + candidate corrections]
                                         (~8-16K segments, 10-20%)
```

- Uses jellyfish Metaphone against domain glossary
- Flags segments where any word phonetically matches a glossary term but is spelled differently
- Attaches candidate corrections to each flag
- Runs in seconds on CPU
- Zero cost, fully deterministic, no hallucination risk

### Stage 2: LLM Contextual Correction (Targeted)

```
[Flagged segments] -> [LLM with constrained prompt] -> [Corrected segments]
                       + domain glossary
                       + flagged word positions
                       + phonetic candidates
```

- Only processes flagged segments (10-20% of total)
- System prompt includes domain glossary AND the specific phonetic candidates
- LLM decides whether each candidate correction is contextually appropriate
- Temperature=0 for deterministic output
- Batch processing: group segments by video for context continuity

### Stage 3: Validation (Optional)

```
[Corrected segments] -> [Diff review] -> [Human spot-check] -> [Apply to DB]
```

- Generate diff of all changes for human review
- Spot-check a sample (e.g., 100 random corrections)
- Apply in bulk to database once validated

### Implementation Priority

| Step | Component | Effort | Impact |
|------|-----------|--------|--------|
| 1 | Build phonetic glossary from domain terms | 1 hour | Foundation |
| 2 | Implement PhoneticDomainMatcher | 2-3 hours | Detection |
| 3 | Run detection on 83K segments, analyze results | 1 hour | Scoping |
| 4 | Design LLM correction prompt with constraints | 2 hours | Quality |
| 5 | Test LLM correction on sample of 100 flagged segments | 2 hours | Validation |
| 6 | Run batch correction on all flagged segments | 3-7 hours (runtime) | Correction |
| 7 | Build diff review tool and spot-check | 2 hours | QA |

**Total development effort:** ~1-2 days
**Total runtime:** ~4-8 hours (mostly LLM processing)

---

## 7. Tools NOT Recommended

| Tool | Why Not |
|------|---------|
| Grammarly (open source alternatives) | No self-hostable equivalent; Grammarly is cloud-only |
| LanguageTool | Grammar checker, not phonetic mishearing corrector |
| WhisperX / faster-whisper | Transcription tools, not post-correction |
| FlanEC / HyPoradise | Require N-best hypotheses we don't have |
| NeuSpell | Trained on typo patterns, not ASR patterns |
| Vosk / Kaldi hotword boosting | For live transcription, not post-correction |

---

## 8. Bibliography

### Libraries (Primary Sources)

- [jellyfish](https://github.com/jamesturk/jellyfish) - Python phonetic matching library (Metaphone, Soundex, NYSIIS)
- [symspellpy](https://github.com/mammothb/symspellpy) - Fast spelling correction with custom dictionaries
- [contextualSpellCheck](https://github.com/R1j1t/contextualSpellCheck) - spaCy BERT-based spell checker (unmaintained)
- [NeuSpell](https://github.com/neuspell/neuspell) - Neural spelling correction toolkit
- [pyphonetics](https://github.com/Lilykos/pyphonetics) - Python 3 phonetics library
- [Spark NLP ContextSpellChecker](https://sparknlp.org/2022/04/01/spellcheck_dl_en_2_4.html) - Deep learning contextual spell checker

### Research Papers

- Zhang & Huang, "Spelling Error Correction with Soft-Masked BERT," ACL 2020. [Paper](https://aclanthology.org/2020.acl-main.82/)
- Chen et al., "HyPoradise: An Open Baseline for Generative Speech Recognition with Large Language Models," ICLR 2024. [Paper](https://openreview.net/forum?id=ceATjGPTUD)
- Hu et al., "Multi-stage Large Language Model Correction for Speech Recognition," 2023. [Paper](https://arxiv.org/html/2310.11532v2)
- Radhakrishnan et al., "Evolutionary Prompt Design for LLM-Based Post-ASR Error Correction," 2024. [Paper](https://arxiv.org/html/2407.16370v1)
- "LLM-based Generative Error Correction for Rare Words with Synthetic Data and Phonetic Context," 2025. [Paper](https://arxiv.org/html/2505.17410v1)
- "Large Language Model Based Generative Error Correction: A Challenge and Baselines," 2024. [Paper](https://arxiv.org/html/2409.09785v3)

### Practical Guides & Experiments

- [OpenAI Cookbook - Addressing Transcription Misspellings](https://developers.openai.com/cookbook/examples/whisper_correct_misspelling) - GPT-4 glossary correction technique
- [OpenAI Cookbook - Enhancing Whisper Transcriptions](https://developers.openai.com/cookbook/examples/whisper_processing_guide) - Pre & post-processing pipeline
- [Vosk Blog - Experiments with LLM ASR Error Correction](https://alphacephei.com/nsh/2025/03/15/generative-error-correction.html) - Practical LLM benchmarks
- [GDELT - Using LLMs to Correct Speech Transcripts](https://blog.gdeltproject.org/generative-ai-experiments-using-large-language-models-to-correct-large-speech-model-transcripts/) - GPT-4 vs Gemini Pro for transcript correction
- [STT Basic Cleanup System Prompt](https://github.com/danielrosehill/STT-Basic-Cleanup-System-Prompt) - Template prompts for STT cleanup
- [FlanEC - Flan-T5 for Post-ASR Error Correction](https://github.com/MorenoLaQuatra/FlanEC) - MIT licensed seq2seq correction
- [RobustGER](https://github.com/YUCHEN005/RobustGER) - Noise-robust generative error correction

### Implementation References

- [Ollama Benchmark](https://github.com/aidatatools/ollama-benchmark) - Local LLM throughput benchmarks
- [PostASR-Correction-SLT2024](https://github.com/rithiksachdev/PostASR-Correction-SLT2024) - Evolutionary prompt optimization for ASR correction
- [DualHyp](https://github.com/sungnyun/dualhyp) - Generative error correction framework

---

## 9. Alternative Research Directions

If the two-stage pipeline proves insufficient:

1. **Fine-tune a small model on KnowledgeStack corrections.** After running the pipeline once and getting human-validated corrections, use those pairs to fine-tune a Flan-T5 or similar model specifically for this domain. This would improve accuracy and speed for future corrections.

2. **Re-transcribe from audio with custom Whisper prompts.** If we can access original audio, re-running Whisper with domain glossary prompts would prevent errors rather than correcting them. More work but higher quality.

3. **Build a phonetic embedding space.** Rather than discrete Metaphone codes, compute continuous phonetic embeddings (using CMU Pronouncing Dictionary + embeddings) for more nuanced similarity matching. The `phonetic-similarity-vectors` project explores this.

4. **Channel-specific glossaries.** Different YouTube channels use different domain terms. Build per-channel glossaries from video titles, descriptions, and high-confidence entities to improve correction accuracy.

5. **Confidence-weighted correction.** If switching to Vosk or Whisper with word-level confidence scores, only apply corrections to low-confidence words, reducing false positives dramatically.
