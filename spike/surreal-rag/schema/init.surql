-- ============================================
-- KNOWLEDGE STACK ENHANCED SCHEMA v2
-- SurrealDB - Graph + Vector Hybrid Model
-- ============================================
-- Based on PRODUCT_VISION.md use cases:
-- - Persona agents, group conversations
-- - Visual Hub with timestamps
-- - Per-topic speaker credibility
-- - Cross-project intelligence routing
-- - Signature story detection
-- - Citation/attribution tracking
-- ============================================

-- NAMESPACE & DATABASE
DEFINE NAMESPACE IF NOT EXISTS knowledge;
USE NS knowledge;
DEFINE DATABASE IF NOT EXISTS transcripts;
USE DB transcripts;

-- ============================================
-- CORE ENTITIES (Nodes)
-- ============================================

-- Channels (YouTube channels we follow)
DEFINE TABLE channel SCHEMAFULL;
DEFINE FIELD youtube_handle ON channel TYPE string;
DEFINE FIELD youtube_id ON channel TYPE option<string>;
DEFINE FIELD name ON channel TYPE string;
DEFINE FIELD domain ON channel TYPE string;           -- "religion", "business", "ai-coding", etc.
-- Optional since 2026-08-05: this is an ingestion setting, not observed data,
-- and no writer has ever set it. As a required int it rejected every channel
-- write — silently, because embed_video ignored write results.
DEFINE FIELD lookback_months ON channel TYPE option<int>;
DEFINE FIELD authority_score ON channel TYPE option<int>;    -- 1-10 score
DEFINE FIELD relevance_score ON channel TYPE option<int>;    -- 1-10 score for your context
DEFINE FIELD ingested_at ON channel TYPE datetime;
DEFINE INDEX channel_handle_idx ON channel FIELDS youtube_handle UNIQUE;
DEFINE INDEX channel_domain_idx ON channel FIELDS domain;

-- Speakers (persona entities - hosts, guests, referenced experts)
DEFINE TABLE speaker SCHEMAFULL;
DEFINE FIELD name ON speaker TYPE string;
DEFINE FIELD normalized ON speaker TYPE string;       -- lowercase, standardized
DEFINE FIELD aliases ON speaker TYPE option<array<string>>;  -- alternate names
DEFINE FIELD is_host ON speaker TYPE bool DEFAULT false;     -- hosts a channel
DEFINE FIELD bio ON speaker TYPE option<string>;
DEFINE FIELD profile_url ON speaker TYPE option<string>;     -- social media, website
DEFINE FIELD wikidata_id ON speaker TYPE option<string>;     -- for entity resolution
DEFINE FIELD created_at ON speaker TYPE datetime;
DEFINE INDEX speaker_normalized_idx ON speaker FIELDS normalized UNIQUE;

-- Speaker credibility per domain (per-topic tiers)
DEFINE TABLE speaker_credibility SCHEMAFULL;
DEFINE FIELD speaker ON speaker_credibility TYPE record<speaker>;
DEFINE FIELD domain ON speaker_credibility TYPE string;      -- "business", "ai-coding", etc.
DEFINE FIELD tier ON speaker_credibility TYPE string;        -- "top", "high", "mid", "low", "none"
DEFINE FIELD reasoning ON speaker_credibility TYPE option<string>;
DEFINE FIELD updated_at ON speaker_credibility TYPE datetime;
DEFINE INDEX cred_speaker_domain_idx ON speaker_credibility FIELDS speaker, domain UNIQUE;

-- Videos (individual episodes)
DEFINE TABLE video SCHEMAFULL;
DEFINE FIELD youtube_id ON video TYPE string;
DEFINE FIELD title ON video TYPE string;
DEFINE FIELD description ON video TYPE option<string>;       -- Full video description
DEFINE FIELD published_at ON video TYPE datetime;
DEFINE FIELD duration_seconds ON video TYPE option<float>;
DEFINE FIELD url ON video TYPE string;
DEFINE FIELD thumbnail_url ON video TYPE option<string>;
DEFINE FIELD fetched_at ON video TYPE datetime;              -- when transcript was fetched from YouTube
DEFINE FIELD ingested_at ON video TYPE option<datetime>;     -- when added to our database (for "what's new")
DEFINE FIELD transcript_path ON video TYPE option<string>;
DEFINE FIELD segment_count ON video TYPE option<int>;
-- YouTube metadata written by embedder.embed_video(). These were missing until
-- 2026-08-05: the table is SCHEMAFULL, so every video write was rejected with
-- "no such field exists" while embed_video still reported success. Any field
-- added to the UPSERT in embedder.py MUST be defined here or writes fail silently.
DEFINE FIELD channel_name ON video TYPE option<string>;
DEFINE FIELD uploader ON video TYPE option<string>;
DEFINE FIELD category ON video TYPE option<string>;
DEFINE FIELD chapters ON video TYPE option<array>;           -- [{title, start_time, end_time}, ...]
-- Without this the array can only ever hold NOTHING. SCHEMAFULL applies inside
-- the array too, so a chapter object was rejected key by key — "Found field
-- 'chapters[0].title', but no such field exists" — while an empty array wrote
-- fine. Every video therefore stored [] and the field looked merely unused
-- rather than broken, right up until the first video with real chapters was
-- indexed on 2026-08-14. FLEXIBLE is what lets yt-dlp's chapter objects in
-- without pinning their exact keys.
DEFINE FIELD chapters[*] ON video TYPE object FLEXIBLE;
DEFINE FIELD hashtags ON video TYPE option<array<string>>;
DEFINE FIELD youtube_tags ON video TYPE option<array<string>>;
DEFINE FIELD view_count ON video TYPE option<int>;
DEFINE FIELD like_count ON video TYPE option<int>;
DEFINE FIELD comment_count ON video TYPE option<int>;
-- yt-dlp's live_status: "was_live", "is_live", "is_upcoming", "not_live".
-- Separates a recorded livestream from an uploaded episode of the same length.
DEFINE FIELD live_status ON video TYPE option<string>;
DEFINE FIELD metadata_fetched_at ON video TYPE option<datetime>;
-- False for the ~200 older transcripts stored as plain prose with no [M:SS]
-- markers. Their text is complete; only segment start/end times are meaningless
-- (all zero). Consumers doing timestamp-based deep links must check this.
DEFINE FIELD has_timestamps ON video TYPE option<bool>;
-- Denormalized for query performance
DEFINE FIELD channel_handle ON video TYPE option<string>;
DEFINE FIELD domain ON video TYPE option<string>;
DEFINE INDEX video_youtube_idx ON video FIELDS youtube_id UNIQUE;
DEFINE INDEX video_published_idx ON video FIELDS published_at;
DEFINE INDEX video_ingested_idx ON video FIELDS ingested_at;   -- "what's new in my library"
DEFINE INDEX video_domain_idx ON video FIELDS domain;

-- Segments (chunks of transcript with embeddings and timestamps)
DEFINE TABLE segment SCHEMAFULL;
DEFINE FIELD text ON segment TYPE string;
DEFINE FIELD start_time ON segment TYPE float;              -- seconds from video start (REQUIRED now)
DEFINE FIELD end_time ON segment TYPE float;                -- end of segment
DEFINE FIELD duration ON segment TYPE float;                -- segment duration
DEFINE FIELD chunk_index ON segment TYPE int;
DEFINE FIELD char_start ON segment TYPE option<int>;        -- character offset in full transcript
DEFINE FIELD char_end ON segment TYPE option<int>;
DEFINE FIELD embedding ON segment TYPE option<array<float>>;  -- vector (1536 dim)
DEFINE FIELD requires_visual ON segment TYPE bool DEFAULT false;  -- "as you can see" detected
DEFINE FIELD ingested_at ON segment TYPE datetime;
-- Denormalized for hybrid queries
DEFINE FIELD published_at ON segment TYPE option<datetime>;
DEFINE FIELD domain ON segment TYPE option<string>;
DEFINE FIELD video_youtube_id ON segment TYPE option<string>;
DEFINE INDEX segment_time_idx ON segment FIELDS start_time;
DEFINE INDEX segment_domain_idx ON segment FIELDS domain;
DEFINE INDEX segment_published_idx ON segment FIELDS published_at;

-- Vector index for similarity search (1536 dimensions for text-embedding-3-small)
DEFINE INDEX segment_embedding_idx ON segment
  FIELDS embedding HNSW DIMENSION 1536 DIST COSINE;

-- Topics (extracted concepts)
DEFINE TABLE topic SCHEMAFULL;
DEFINE FIELD name ON topic TYPE string;
DEFINE FIELD normalized ON topic TYPE string;              -- lowercase, standardized
DEFINE FIELD embedding ON topic TYPE option<array<float>>; -- for topic similarity
DEFINE FIELD synonyms ON topic TYPE option<array<string>>;
DEFINE INDEX topic_normalized_idx ON topic FIELDS normalized UNIQUE;

-- Quotes (notable statements for highlight reels)
DEFINE TABLE quote SCHEMAFULL;
DEFINE FIELD text ON quote TYPE string;
DEFINE FIELD speaker ON quote TYPE option<record<speaker>>;
DEFINE FIELD segment ON quote TYPE record<segment>;
DEFINE FIELD significance ON quote TYPE option<string>;    -- why it's notable
DEFINE FIELD viral_score ON quote TYPE option<float>;      -- predicted virality
DEFINE FIELD tags ON quote TYPE option<array<string>>;
DEFINE FIELD created_at ON quote TYPE datetime;

-- Citations (attribution tracking)
DEFINE TABLE citation SCHEMAFULL;
DEFINE FIELD source_segment ON citation TYPE record<segment>;  -- where it was said
DEFINE FIELD original_speaker ON citation TYPE option<record<speaker>>;  -- who originally said it
DEFINE FIELD original_video ON citation TYPE option<record<video>>;      -- original source
DEFINE FIELD citation_type ON citation TYPE string;        -- "firsthand", "secondhand", "paraphrase"
DEFINE FIELD context ON citation TYPE option<string>;
DEFINE FIELD created_at ON citation TYPE datetime;

-- Signature stories (stories told multiple times = core messages)
DEFINE TABLE signature_story SCHEMAFULL;
DEFINE FIELD speaker ON signature_story TYPE record<speaker>;
DEFINE FIELD title ON signature_story TYPE string;         -- story name/summary
DEFINE FIELD description ON signature_story TYPE option<string>;
DEFINE FIELD occurrence_count ON signature_story TYPE int DEFAULT 1;
DEFINE FIELD first_told ON signature_story TYPE option<datetime>;
DEFINE FIELD significance ON signature_story TYPE option<string>;
DEFINE FIELD canonical_segment ON signature_story TYPE option<record<segment>>;  -- best version
DEFINE INDEX story_speaker_idx ON signature_story FIELDS speaker;

-- Visual references (segments requiring visual analysis)
DEFINE TABLE visual_reference SCHEMAFULL;
DEFINE FIELD segment ON visual_reference TYPE record<segment>;
DEFINE FIELD trigger_phrase ON visual_reference TYPE string;   -- "as you can see on screen"
DEFINE FIELD frame_url ON visual_reference TYPE option<string>;
DEFINE FIELD frame_timestamp ON visual_reference TYPE float;   -- exact frame time
DEFINE FIELD ocr_text ON visual_reference TYPE option<string>;
DEFINE FIELD visual_type ON visual_reference TYPE option<string>;  -- "code", "diagram", "slide", etc.
DEFINE FIELD visual_embedding ON visual_reference TYPE option<array<float>>;
DEFINE FIELD processed ON visual_reference TYPE bool DEFAULT false;
DEFINE INDEX visual_segment_idx ON visual_reference FIELDS segment;

-- ============================================
-- CROSS-PROJECT INTELLIGENCE
-- ============================================

-- Projects (your active projects that need intelligence)
DEFINE TABLE project SCHEMAFULL;
DEFINE FIELD name ON project TYPE string;
DEFINE FIELD description ON project TYPE option<string>;
DEFINE FIELD objectives ON project TYPE option<array<string>>;   -- what you're trying to achieve
DEFINE FIELD keywords ON project TYPE option<array<string>>;     -- topics to watch for
DEFINE FIELD active ON project TYPE bool DEFAULT true;
DEFINE FIELD created_at ON project TYPE datetime;
DEFINE INDEX project_name_idx ON project FIELDS name UNIQUE;

-- Golden standards (aggregated best practices with recency)
DEFINE TABLE golden_standard SCHEMAFULL;
DEFINE FIELD topic ON golden_standard TYPE string;             -- "Claude MCP patterns", "n8n best practices"
DEFINE FIELD summary ON golden_standard TYPE string;           -- current best practice
DEFINE FIELD sources ON golden_standard TYPE array<record<segment>>;  -- supporting segments
DEFINE FIELD confidence ON golden_standard TYPE float;         -- 0-1
DEFINE FIELD last_updated ON golden_standard TYPE datetime;
DEFINE FIELD supersedes ON golden_standard TYPE option<record<golden_standard>>;  -- previous version
DEFINE INDEX golden_topic_idx ON golden_standard FIELDS topic;

-- Persona agents (for CrewAI/LangChain integration)
DEFINE TABLE persona_agent SCHEMAFULL;
DEFINE FIELD speaker ON persona_agent TYPE record<speaker>;
DEFINE FIELD agent_name ON persona_agent TYPE string;          -- "MyronGoldenAgent"
DEFINE FIELD system_prompt ON persona_agent TYPE string;       -- generated from their content
DEFINE FIELD expertise_domains ON persona_agent TYPE array<string>;
DEFINE FIELD knowledge_cutoff ON persona_agent TYPE datetime;  -- last ingested content date
DEFINE FIELD segment_count ON persona_agent TYPE int;          -- how much data it's trained on
DEFINE FIELD last_refreshed ON persona_agent TYPE datetime;
DEFINE INDEX persona_speaker_idx ON persona_agent FIELDS speaker UNIQUE;

-- ============================================
-- EDGES (Relationships)
-- ============================================

-- Channel owns Videos
DEFINE TABLE has_video SCHEMAFULL TYPE RELATION
  FROM channel TO video;

-- Video contains Segments
DEFINE TABLE has_segment SCHEMAFULL TYPE RELATION
  FROM video TO segment;
DEFINE FIELD sequence ON has_segment TYPE int;

-- Speaker hosts Channel
DEFINE TABLE hosts SCHEMAFULL TYPE RELATION
  FROM speaker TO channel;

-- Speaker appears in Video
DEFINE TABLE appears_in SCHEMAFULL TYPE RELATION
  FROM speaker TO video;
DEFINE FIELD role ON appears_in TYPE string DEFAULT "guest";  -- "host", "guest", "mentioned"

-- Speaker speaks in Segment
DEFINE TABLE speaks_in SCHEMAFULL TYPE RELATION
  FROM speaker TO segment;

-- Segment mentions Topic
DEFINE TABLE mentions SCHEMAFULL TYPE RELATION
  FROM segment TO topic;
DEFINE FIELD confidence ON mentions TYPE float DEFAULT 1.0;

-- Segment references another Segment (cross-references)
DEFINE TABLE references SCHEMAFULL TYPE RELATION
  FROM segment TO segment;
DEFINE FIELD reference_type ON references TYPE string;  -- "agrees", "contradicts", "extends"

-- SignatureStory appears in Segments
DEFINE TABLE story_occurrence SCHEMAFULL TYPE RELATION
  FROM signature_story TO segment;
DEFINE FIELD similarity_score ON story_occurrence TYPE float;

-- Project matches Segments (daily routing)
DEFINE TABLE project_match SCHEMAFULL TYPE RELATION
  FROM project TO segment;
DEFINE FIELD relevance_score ON project_match TYPE float;
DEFINE FIELD matched_at ON project_match TYPE datetime;
DEFINE FIELD reviewed ON project_match TYPE bool DEFAULT false;

-- ============================================
-- UTILITY FUNCTIONS
-- ============================================

-- Hybrid search: vector + filters + graph in one query
DEFINE FUNCTION fn::hybrid_search($query_embedding: array<float>, $domain: option<string>, $recency_days: option<int>, $limit: int) {
    LET $base_results = (
        SELECT
            id,
            text,
            start_time,
            end_time,
            domain,
            published_at,
            video_youtube_id,
            vector::similarity::cosine(embedding, $query_embedding) AS vector_score
        FROM segment
        WHERE embedding <|50, 100|> $query_embedding
            AND ($domain IS NONE OR domain = $domain)
            AND ($recency_days IS NONE OR published_at > time::now() - duration::from_days($recency_days))
        ORDER BY vector_score DESC
        LIMIT $limit
    );
    RETURN $base_results;
};

-- Get speaker's content with credibility context
DEFINE FUNCTION fn::speaker_content($speaker_normalized: string, $domain: option<string>) {
    LET $spk = (SELECT * FROM speaker WHERE normalized = $speaker_normalized)[0];
    LET $cred = (SELECT * FROM speaker_credibility WHERE speaker = $spk.id AND ($domain IS NONE OR domain = $domain));
    LET $segments = (SELECT * FROM segment WHERE <-speaks_in<-speaker.normalized = $speaker_normalized ORDER BY published_at DESC LIMIT 100);
    RETURN {
        speaker: $spk,
        credibility: $cred,
        recent_segments: $segments
    };
};

-- Get video with all segments and timestamps for Visual Hub
DEFINE FUNCTION fn::video_with_segments($video_id: string) {
    LET $video = (SELECT * FROM video WHERE youtube_id = $video_id)[0];
    LET $segments = (
        SELECT id, text, start_time, end_time, chunk_index, requires_visual
        FROM segment
        WHERE <-has_segment<-video.youtube_id = $video_id
        ORDER BY start_time
    );
    RETURN {
        video: $video,
        segments: $segments,
        segment_count: array::len($segments)
    };
};

-- Ranking formula: recency_weight * tier_multiplier * vector_score
-- (Implement in application layer for flexibility)
