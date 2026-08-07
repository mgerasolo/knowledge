# Research: Open-Source User Preference Profiling Systems

**Date:** 2026-01-29
**Researcher:** Claude Opus 4.5
**Purpose:** Identify open-source projects for building per-user interest profiles based on behavioral signals (watch history, topic searches, time spent, channels followed, tag weighting) for a knowledge platform ingesting YouTube expert channel transcripts.

---

## Executive Summary

### Key Findings

1. **Microsoft Recommenders** (~18k stars) is the most comprehensive open-source recommendation toolkit, with production-ready implementations of 30+ algorithms including sequential user preference modeling, news article recommendation with long/short-term user interest modeling, and deep learning approaches for implicit feedback.

2. **Gorse** (~9.2k stars, Go) is the most production-ready self-hosted recommendation engine, offering REST APIs, AutoML, distributed prediction, and real-time user profile building from interaction feedback -- closest to a "drop-in" solution for our use case.

3. **LightFM** (~4.9k stars, Python) is the strongest candidate for hybrid content + collaborative filtering, uniquely designed to incorporate both user and item metadata (topics, tags, categories) into matrix factorization -- directly applicable to matching user profiles against transcript content features.

4. **RecBole** (~4.1k stars, Python) provides the broadest research framework with 100+ algorithms spanning knowledge-based, sequential, and context-aware recommendation -- the best choice if we want to experiment with multiple approaches including knowledge graph integration.

5. **The emerging LLM-powered approach** (Microsoft RecAI, open-recommender, PURE framework) represents a paradigm shift where LLMs build and maintain natural-language user profiles from behavioral data -- highly relevant for a transcript-based knowledge platform where content is already text-rich.

---

## Tier 1: Highest Relevance to Our Use Case

These projects most directly address building user interest profiles from behavioral signals on content/knowledge platforms.

---

### 1. Microsoft Recommenders (recommenders-team/recommenders)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/recommenders-team/recommenders |
| **Stars** | ~18,000 |
| **Language** | Python |
| **License** | MIT |
| **Last Activity** | Actively maintained (2025 releases) |
| **Maintenance** | Excellent -- LF AI & Data Foundation project, Microsoft-backed |

**What it does:**
The most starred open-source recommendation project on GitHub. Provides best-practice implementations of 30+ algorithms spanning collaborative filtering, content-based, deep learning, and hybrid approaches. Includes complete Jupyter notebook examples, evaluation utilities, and production deployment guidance.

**Key algorithms for our use case:**
- **SAR (Smart Adaptive Recommendations):** Learns personalized recommendations from user transaction history -- directly applicable to "what users watched" data
- **NRMS/NAML/LSTUR:** Neural news recommendation with long-term and short-term user interest modeling -- conceptually very close to our transcript/topic recommendation problem
- **xDeepFM/Wide&Deep:** Deep learning models that combine user features, item features, and context for ranking
- **Sequential models (SASRec, SSE-PT):** Capture both long and short-term user preferences using attention mechanisms

**How it applies to our use case:**
This is the most directly applicable framework. The news recommendation algorithms (NRMS, NAML, LSTUR) model user interests from reading history in almost exactly the way we need for transcript consumption history. SAR builds personalized profiles from interaction logs. The framework provides complete pipelines from data ingestion through evaluation, and every algorithm comes with a working notebook example.

**Limitations:**
Research-focused toolkit rather than production server. You would need to wrap selected algorithms in your own API layer. No built-in REST API or user management.

---

### 2. Gorse (gorse-io/gorse)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/gorse-io/gorse |
| **Stars** | ~9,200 |
| **Language** | Go |
| **License** | Apache-2.0 |
| **Last Activity** | Active (Dec 2025 commits across multiple repos) |
| **Maintenance** | Good -- active development on v0.5 with LLM integration |

**What it does:**
A self-hosted, production-ready recommendation engine with REST APIs, GUI dashboard, AutoML model selection, and distributed architecture. Supports multiple data stores (PostgreSQL, MySQL, MongoDB, Redis). Automatically trains models from user interaction data and serves real-time recommendations.

**Key features for our use case:**
- **RESTful API:** Insert users, items, and interactions via API; get recommendations back
- **Auto user profiling:** Automatically builds user preference models from feedback (positive/negative interactions)
- **Item labels/categories:** Supports item metadata for content-based filtering
- **AutoML:** Automatically selects the best model configuration
- **LLM rankers (v0.5):** New support for LLM-based ranking and multimodal content via embeddings
- **Online evaluation:** Built-in A/B testing and performance monitoring

**How it applies to our use case:**
Gorse is the closest to a turnkey solution. We could:
1. Insert YouTube transcripts as items with topic/tag labels
2. Insert user watch events, search queries, and time-spent as interaction feedback
3. Gorse automatically builds per-user preference models and serves recommendations
4. The REST API integrates directly with a Node.js/Express backend
5. PostgreSQL support aligns with our existing database infrastructure

**Limitations:**
Written in Go (not Python/Node), so extending the core algorithms requires Go expertise. Content-based features are limited to labels/categories -- it does not do deep NLP analysis of transcript text. Community is smaller than Python-ecosystem alternatives.

---

### 3. LightFM (lyst/lightfm)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/lyst/lightfm |
| **Stars** | ~4,900 |
| **Language** | Python (Cython) |
| **License** | Apache-2.0 |
| **Last Activity** | Latest release v1.17; development has slowed but library is stable and production-proven |
| **Maintenance** | Maintenance mode -- stable but limited new features |

**What it does:**
A hybrid recommendation algorithm that combines collaborative filtering with content-based features. The key innovation is representing each user and item as the sum of latent representations of their features, enabling recommendations to generalize to new items (via item features) and new users (via user features).

**Key features for our use case:**
- **Hybrid approach:** Combines user behavior data with item metadata (topics, tags, channels)
- **Feature embeddings:** Represents users and items through their features -- a user who watches AI topics gets an "AI interest" embedding
- **Implicit feedback support:** BPR, WARP, and k-OS WARP loss functions for implicit signals (watches, clicks, time spent)
- **Cold-start handling:** Can recommend to new users based on their feature profile alone (e.g., topics they searched for)
- **Scalable:** Cython-based, multi-core training, production-proven at Lyst and Catalant

**How it applies to our use case:**
LightFM is ideal for our user profiling problem because:
1. User features = topics searched, channels followed, tags weighted
2. Item features = transcript topics, channel, tags, categories
3. Interactions = watch events, time spent (as implicit feedback)
4. The model learns user interest profiles as weighted combinations of topic/tag embeddings
5. Cold-start: New users get recommendations based on their initial topic selections
6. These learned user embeddings ARE the user interest profile

**Limitations:**
Not a server -- it is a library you call from Python. No REST API, no dashboard. Development has slowed (last PyPI update ~2 years ago). Does not do deep text analysis -- you must pre-extract features (topics, tags) from transcripts.

---

### 4. Microsoft RecAI (microsoft/RecAI)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/microsoft/RecAI |
| **Stars** | ~800+ (growing rapidly) |
| **Language** | Python |
| **License** | MIT |
| **Last Activity** | 2024-2025 (active research project) |
| **Maintenance** | Active -- Microsoft Research backed |

**What it does:**
Bridges LLMs and recommender systems. Provides multiple integration strategies: using LLMs as recommendation agents, creating recommendation-oriented language models, augmenting LLMs with domain knowledge, and using LLMs to explain recommendation model decisions.

**Key components for our use case:**
- **InteRecAgent:** Uses an LLM as the "brain" and traditional recommender models as "tools" -- creates conversational, interactive, explainable recommendations
- **Knowledge Plugin:** Injects domain-specific knowledge into LLM prompts without fine-tuning
- **RecLM-emb:** Creates text embeddings optimized for item retrieval from descriptions
- **RecExplainer:** Explains why items were recommended in natural language

**How it applies to our use case:**
This is the most forward-looking approach for a knowledge platform. Since our content is transcript text:
1. LLMs can deeply understand transcript content and user queries
2. The Knowledge Plugin can inject our topic taxonomy without model fine-tuning
3. InteRecAgent enables natural-language exploration ("Show me more advanced topics from this expert")
4. RecExplainer can tell users WHY a transcript was recommended ("Based on your interest in distributed systems, shown by watching 3 talks by Martin Kleppmann...")

**Limitations:**
Research-stage project, not production-hardened. Requires OpenAI API calls (cost). Newer project with smaller community. Would need significant integration work.

---

### 5. open-recommender (bjsi/open-recommender)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/bjsi/open-recommender |
| **Stars** | ~400 (newer project) |
| **Language** | TypeScript |
| **License** | Open source |
| **Last Activity** | 2024 |
| **Maintenance** | Individual developer project |

**What it does:**
An LLM-powered open-source YouTube video recommendation system. Analyzes a user's social media activity (Twitter) to infer interests, then searches YouTube for relevant content, downloads transcripts, and recommends the most relevant clips.

**Key features for our use case:**
- **Interest inference from behavior:** Builds user interest profiles from behavioral signals
- **YouTube transcript analysis:** Already works with YouTube transcripts
- **LLM-powered matching:** Uses GPT-4 to match user interests to content
- **Explainable:** Can explain why content was recommended
- **TypeScript:** Aligns with our Node.js stack

**How it applies to our use case:**
This is architecturally the closest to what we want to build. The pipeline (infer user interests -> analyze transcripts -> match and recommend) is exactly our workflow. The key differences: we would replace Twitter as the signal source with platform behavior (watches, searches, time spent), and we would adapt the LLM prompts for expert knowledge content rather than general YouTube.

**Limitations:**
Small project by a single developer. Low star count. Relies heavily on GPT-4 API (cost at scale). Quality is self-reported at ~50% relevance. Not production-ready.

---

## Tier 2: Strong General-Purpose Recommendation Frameworks

These are well-established frameworks that can be adapted to our use case but require more custom work for user profiling specifically.

---

### 6. RecBole (RUCAIBox/RecBole)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/RUCAIBox/RecBole |
| **Stars** | ~4,100 |
| **Language** | Python (PyTorch) |
| **License** | MIT |
| **Last Activity** | Feb 2025 (PyPI release) |
| **Maintenance** | Active -- academic research group maintains it |

**What it does:**
A unified, comprehensive recommendation framework implementing 100+ algorithms across four categories: General Recommendation, Sequential Recommendation, Context-aware Recommendation, and Knowledge-based Recommendation. Built on PyTorch for research reproducibility.

**Key features for our use case:**
- **Knowledge-based models:** RippleNet, KGAT, KGNN-LS -- use knowledge graphs as side information for recommendations
- **Sequential models:** SASRec, BERT4Rec, GRU4Rec -- capture temporal patterns in user behavior
- **Context-aware models:** Factor in contextual signals (time of day, device, etc.)
- **RecBole 2.0 extensions:** Debiasing, fairness, GNN-based recommendations
- **44 benchmark datasets:** Easy experimentation and evaluation

**How it applies to our use case:**
RecBole is the best choice for experimentation and research. We could:
1. Build a knowledge graph from transcript topics, experts, and channels
2. Use knowledge-based models (RippleNet) to propagate user interests through the topic graph
3. Use sequential models to capture evolving user interests over time
4. Compare 10+ approaches to find the best-performing user modeling strategy

**Limitations:**
Research-focused -- no production deployment tools, no REST API, no serving infrastructure. Steep learning curve. You need to format data into RecBole's specific input format.

---

### 7. Implicit (benfred/implicit)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/benfred/implicit |
| **Stars** | ~3,800 |
| **Language** | Python (Cython/CUDA) |
| **License** | MIT |
| **Last Activity** | Sep 2023 (v0.7.2); issues still active 2025 |
| **Maintenance** | Stable/slowing -- core library is mature |

**What it does:**
Fast implementations of collaborative filtering algorithms specifically designed for implicit feedback datasets (clicks, views, time spent -- not explicit ratings). Supports ALS, BPR, and nearest-neighbor methods with GPU acceleration.

**Key features for our use case:**
- **Implicit feedback focus:** Designed exactly for behavioral signals (watches, clicks, time spent)
- **GPU acceleration:** CUDA kernels for fast training on large datasets
- **ANN integration:** Annoy, NMSLIB, Faiss for fast recommendation serving
- **Proven algorithms:** ALS ("Collaborative Filtering for Implicit Feedback Datasets" paper)

**How it applies to our use case:**
Implicit is the go-to library for learning user preferences from behavioral signals without explicit ratings. Watch events, search clicks, and time-spent-on-transcript are all implicit feedback signals. The library would learn user latent factor vectors that represent their interest profile.

**Limitations:**
Pure collaborative filtering -- no content features, no text analysis, no knowledge graphs. Users must have interaction history (cold-start problem). Library only, not a service.

---

### 8. TensorFlow Recommenders (tensorflow/recommenders)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/tensorflow/recommenders |
| **Stars** | ~1,800+ |
| **Language** | Python (TensorFlow) |
| **License** | Apache-2.0 |
| **Last Activity** | 2024-2025 |
| **Maintenance** | Google-maintained |

**What it does:**
TensorFlow library for building flexible recommender models with a focus on the two-tower retrieval architecture. Supports multi-task learning, content features, and context-aware recommendations.

**Key features for our use case:**
- **Two-tower architecture:** Separately models user preferences and item attributes, then matches them
- **Rich feature support:** User features, item features, and contextual features all integrated
- **Multi-task learning:** Jointly optimize retrieval and ranking objectives
- **DCN (Deep & Cross Network):** Automatically learns feature interactions
- **Scalable:** Production-grade TensorFlow infrastructure

**How it applies to our use case:**
The two-tower model is a natural fit:
- Query tower: encodes user preferences (topics watched, channels followed, search history)
- Candidate tower: encodes transcript features (topic, channel, tags, content embedding)
- The model learns to match users to relevant transcripts
- Supports both implicit feedback and content features simultaneously

**Limitations:**
Requires TensorFlow ecosystem (heavier dependency). More complex to set up than simpler libraries. Python-only.

---

### 9. Cornac (PreferredAI/cornac)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/PreferredAI/cornac |
| **Stars** | ~1,000 |
| **Language** | Python |
| **License** | Apache-2.0 |
| **Last Activity** | 2024-2025 (v2.3.5) |
| **Maintenance** | Active -- Preferred.AI academic group, ACM RecSys recommended |

**What it does:**
A comparative framework for multimodal recommender systems. Specializes in models that leverage auxiliary data: item text descriptions, images, social networks, and knowledge graphs.

**Key features for our use case:**
- **Text-aware models:** Models that use item textual descriptions (transcripts) as features
- **Graph-aware models:** Models that use item relationship graphs (topic hierarchies, expert networks)
- **A/B testing extension (Cornac-AB):** Built-in online evaluation support
- **ACM RecSys endorsed:** Trustworthy evaluation framework

**How it applies to our use case:**
Cornac's text-aware models can directly use transcript content as item features alongside user interaction data. The graph-aware models could leverage our topic taxonomy. The A/B testing extension is valuable for iterating on recommendation quality.

**Limitations:**
Research-oriented. Smaller community than top-tier projects. Limited production deployment support.

---

### 10. Surprise (NicolasHug/Surprise)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/NicolasHug/Surprise |
| **Stars** | ~6,700 |
| **Language** | Python |
| **License** | BSD 3-Clause |
| **Last Activity** | 2025 (maintenance PRs for numpy 2 compatibility) |
| **Maintenance** | Maintenance-only since 2019 |

**What it does:**
A scikit-learn-inspired library for building and analyzing recommender systems. Provides clean implementations of SVD, SVD++, NMF, KNN-based algorithms with built-in cross-validation and evaluation tools.

**Key features for our use case:**
- **Clean API:** scikit-learn-like interface, easy to learn
- **Evaluation tools:** Robust cross-validation and metric computation
- **Well-documented:** Extensive documentation with mathematical details

**How it applies to our use case:**
Good for prototyping and baseline evaluation. Could serve as a starting point for user preference modeling using matrix factorization.

**Limitations:**
Does NOT support implicit feedback (explicit ratings only). Does NOT support content-based features. Maintenance-only mode. These are significant limitations for our use case where signals are primarily implicit.

---

### 11. LibRecommender (massquantity/LibRecommender)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/massquantity/LibRecommender |
| **Stars** | ~450 |
| **Language** | Python |
| **License** | MIT |
| **Last Activity** | 2024-2025 |
| **Maintenance** | Active |

**What it does:**
An end-to-end recommender system with both training and serving modules. Implements modern deep learning algorithms (DIN, DeepFM, LightGCN) and supports hybrid collaborative + content-based approaches.

**Key features for our use case:**
- **End-to-end pipeline:** Data preprocessing -> training -> evaluation -> serving
- **Hybrid features:** Supports user features, item features, and interaction data simultaneously
- **Deep Interest Network (DIN):** Captures user interest diversity and temporal evolution
- **YouTubeRanking model:** Implements the YouTube recommendation paper's architecture
- **Cold-start support:** Can recommend for new users/items using features
- **Serving module:** Built-in model serving for production deployment

**How it applies to our use case:**
LibRecommender's DIN (Deep Interest Network) model is specifically designed to model diverse and evolving user interests -- exactly what we need. The YouTubeRanking implementation is architecturally similar to what YouTube actually uses. The end-to-end pipeline with serving support reduces integration effort.

**Limitations:**
Smaller community (450 stars). TensorFlow dependency. Documentation is less extensive than larger projects.

---

### 12. LensKit (lenskit/lkpy)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/lenskit/lkpy |
| **Stars** | ~300 (but well-established in academic community) |
| **Language** | Python (with Rust acceleration) |
| **License** | MIT |
| **Last Activity** | 2025.6.2 release (very active) |
| **Maintenance** | Excellent -- major 2025 redesign, Rust acceleration |

**What it does:**
A recommendation toolkit focused on research reproducibility and evaluation. The 2025 redesign introduces new modular APIs, Rust-based acceleration, and plans for content-based and knowledge-based recommenders.

**Key features for our use case:**
- **Modular architecture:** Swap similarity functions, neighborhood methods, etc.
- **Research-grade evaluation:** Industry-standard evaluation pipelines
- **Active 2025 development:** New content-based features coming in upcoming releases
- **User modeling research ties:** Used in ACM UMAP conference research

**How it applies to our use case:**
Best for evaluation and benchmarking. Could be used to rigorously compare different user modeling approaches. The upcoming content-based features will increase relevance.

**Limitations:**
Fewer algorithms than RecBole or Microsoft Recommenders. Currently focused on collaborative filtering (content-based coming soon). Lower star count.

---

## Tier 3: Supporting / Complementary Tools

These are not recommendation engines per se, but would complement our user profiling system.

---

### 13. Haystack (deepset-ai/haystack)

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/deepset-ai/haystack |
| **Stars** | ~39,000+ |
| **Language** | Python |
| **License** | Apache-2.0 |
| **Last Activity** | Very active (2025-2026) |
| **Maintenance** | Excellent -- backed by deepset, large community |

**What it does:**
An AI orchestration framework for building RAG, semantic search, and question answering systems. Connects LLMs, vector databases, and document processing into production-ready pipelines.

**How it applies to our use case:**
Not a recommendation engine, but could serve as the content understanding layer. We could use Haystack to:
1. Process and semantically index YouTube transcripts
2. Build topic extraction pipelines
3. Create semantic search over transcript content
4. Generate content embeddings that feed into our recommendation system

---

### 14. gauravchak/user_preference_modeling

| Field | Detail |
|-------|--------|
| **GitHub** | https://github.com/gauravchak/user_preference_modeling |
| **Stars** | Small (educational) |
| **Language** | Python |
| **Last Activity** | 2024 |

**What it does:**
A focused educational repository demonstrating multiple ways to model user preferences in recommender systems. Covers embedding-based preference modeling, attention-based user interest modeling, and multi-interest extraction.

**How it applies to our use case:**
Excellent reference code for implementing user preference modules. Not a framework to adopt wholesale, but contains clean implementations of the exact modeling patterns we need (user interest embeddings, attention over history, multi-interest extraction).

---

## Comparative Matrix

| Project | Stars | Language | User Profiling | Content Features | Implicit Feedback | Knowledge Graph | Production-Ready | Our Use Case Fit |
|---------|-------|----------|---------------|-----------------|-------------------|----------------|-----------------|-----------------|
| **MS Recommenders** | 18k | Python | Excellent | Yes | Yes | No | Moderate | **Excellent** |
| **Gorse** | 9.2k | Go | Good | Labels only | Yes | No | **Excellent** | **Excellent** |
| **LightFM** | 4.9k | Python | Good | **Yes - core feature** | Yes | No | Good (library) | **Excellent** |
| **RecAI** | 800+ | Python | **LLM-powered** | Yes (text) | Indirect | Via plugin | Research | **Very Good** |
| **open-recommender** | 400 | TypeScript | LLM-powered | Yes (transcripts) | Indirect | No | Prototype | **Very Good** |
| **RecBole** | 4.1k | Python | Research | Some | Yes | **Yes** | Research | Very Good |
| **Implicit** | 3.8k | Python | CF only | **No** | **Yes - core** | No | Good (library) | Good |
| **TFRS** | 1.8k | Python | Two-tower | Yes | Yes | No | Good | Good |
| **Cornac** | 1k | Python | Multimodal | Yes (text, image) | Yes | Graph | Research | Good |
| **Surprise** | 6.7k | Python | Basic | No | **No** | No | Good (library) | Limited |
| **LibRecommender** | 450 | Python | DIN/YouTube | Yes | Yes | No | Good (E2E) | Good |
| **LensKit** | 300 | Python | Research | Coming soon | Limited | No | Research | Moderate |

---

## Recommended Architecture for Our Knowledge Platform

Based on this research, here is a recommended approach combining multiple projects:

### Phase 1: MVP (Quickest path to user profiles)
**Primary:** Gorse
- Deploy as a service alongside our existing PostgreSQL
- Feed user interactions (watches, searches, time-on-page) via REST API
- Tag transcripts with topics/channels/expert labels
- Get personalized recommendations immediately via API
- Fits our Node.js/Express backend via REST

### Phase 2: Enhanced Content Matching
**Add:** LightFM (Python microservice)
- Build hybrid user-item profiles using transcript topic features
- User features: accumulated topic interests, channel preferences, search patterns
- Item features: transcript topics, tags, difficulty level, channel
- Train periodically, export user interest vectors as the "user profile"

### Phase 3: Deep Understanding
**Add:** LLM-based profiling (RecAI patterns / custom)
- Use LLMs to analyze user behavior patterns and generate natural-language user profiles
- "This user is interested in advanced distributed systems, particularly consensus algorithms, and follows practitioners over academics"
- Use Haystack for transcript semantic analysis and topic extraction
- Use RecAI patterns for explainable, conversational recommendations

### Phase 4: Knowledge Graph Integration
**Add:** RecBole knowledge-based models
- Build a knowledge graph: Topics -> Subtopics -> Experts -> Channels -> Transcripts
- User preferences propagate through the graph (RippleNet pattern)
- Enables discovery: "Users interested in X also discover related area Y"

---

## Research Papers Worth Reading

1. **"Collaborative Filtering for Implicit Feedback Datasets"** (Hu, Koren, Volinsky, 2008) -- Foundation for implicit feedback recommendation
2. **"BPR: Bayesian Personalized Ranking from Implicit Feedback"** (Rendle et al., 2009) -- Key algorithm used in LightFM and Implicit
3. **"Deep Neural Networks for YouTube Recommendations"** (Covington et al., 2016) -- YouTube's actual recommendation architecture
4. **"RippleNet: Propagating User Preferences on the Knowledge Graph"** (Wang et al., 2018) -- Knowledge graph preference propagation
5. **"LLM-based User Profile Management for Recommender System (PURE)"** (Bang et al., 2025) -- Cutting-edge LLM user profiling
6. **"LettinGo: Explore User Profile Generation for Recommendation System"** (KDD 2025) -- Adaptive LLM-based profile generation

---

## Sources

- [Microsoft Recommenders](https://github.com/recommenders-team/recommenders)
- [Gorse](https://github.com/gorse-io/gorse)
- [LightFM](https://github.com/lyst/lightfm)
- [Microsoft RecAI](https://github.com/microsoft/RecAI)
- [open-recommender](https://github.com/bjsi/open-recommender)
- [RecBole](https://github.com/RUCAIBox/RecBole)
- [Implicit](https://github.com/benfred/implicit)
- [TensorFlow Recommenders](https://github.com/tensorflow/recommenders)
- [Cornac](https://github.com/PreferredAI/cornac)
- [Surprise](https://github.com/NicolasHug/Surprise)
- [LibRecommender](https://github.com/massquantity/LibRecommender)
- [LensKit](https://github.com/lenskit/lkpy)
- [Haystack](https://github.com/deepset-ai/haystack)
- [user_preference_modeling](https://github.com/gauravchak/user_preference_modeling)
- [PURE LLM User Profile Paper](https://arxiv.org/abs/2502.14541)
- [LettinGo KDD 2025](https://arxiv.org/html/2506.18309)
- [Awesome-Recsys Papers](https://github.com/ceo21ckim/Awesome-Recsys)
- [List of Recommender Systems](https://github.com/grahamjenson/list_of_recommender_systems)
- [GitHub Topic: content-based-recommendation](https://github.com/topics/content-based-recommendation)
- [GitHub Topic: knowledge-graph-for-recommendation](https://github.com/topics/knowledge-graph-for-recommendation)
- [GitHub Topic: user-profiling](https://github.com/topics/user-profiling)
