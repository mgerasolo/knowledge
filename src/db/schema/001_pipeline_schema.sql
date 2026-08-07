-- ============================================
-- KnowledgeEnroll Pipeline Schema
-- PostgreSQL schema for channel management and pipeline state
-- ============================================

-- Pipeline item status enum
CREATE TYPE pipeline_status AS ENUM (
    'discovered',      -- Found in RSS, not yet processed
    'queued',          -- Ready for processing
    'downloading',     -- Fetching transcript
    'uploading',       -- Sending to Speakr
    'transcribing',    -- Speakr processing (WhisperX)
    'embedding',       -- Generating vectors
    'indexing',        -- Writing to SurrealDB
    'indexed_light',   -- Basic indexing done
    'indexed_full',    -- Full enrichment done
    'upgrading',       -- Upgrading from light to full
    'failed'           -- Processing failed
);

-- Ingestion mode enum
CREATE TYPE ingestion_mode AS ENUM (
    'auto',            -- Automatic processing
    'review',          -- Queue for manual review
    'guest_monitor',   -- Only ingest if guest detected
    'paused'           -- Channel paused
);

-- ============================================
-- CHANNELS TABLE
-- Stores monitored YouTube channels
-- ============================================
CREATE TABLE IF NOT EXISTS channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- YouTube identifiers
    youtube_channel_id VARCHAR(24),           -- UC... channel ID
    youtube_handle VARCHAR(100) NOT NULL,     -- @handle or custom URL

    -- Display info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    thumbnail_url TEXT,
    subscriber_count BIGINT,
    video_count INT,

    -- Classification
    domain VARCHAR(50) NOT NULL DEFAULT 'general',  -- ai-tech, business, political, mindset-health, general

    -- Scoring (1-10 scale)
    authority_score INT DEFAULT 5 CHECK (authority_score BETWEEN 1 AND 10),
    relevance_score INT DEFAULT 5 CHECK (relevance_score BETWEEN 1 AND 10),

    -- Ingestion settings
    ingestion_mode ingestion_mode DEFAULT 'auto',
    check_interval_minutes INT DEFAULT 60,
    backlog_depth_days INT DEFAULT 30,         -- How far back to look on first sync
    backlog_max_videos INT DEFAULT 50,         -- Max videos to backfill

    -- State tracking
    rss_url TEXT,                              -- Computed RSS feed URL
    last_checked_at TIMESTAMP WITH TIME ZONE,
    last_video_at TIMESTAMP WITH TIME ZONE,    -- Most recent video we know about
    last_error TEXT,
    consecutive_failures INT DEFAULT 0,

    -- Flags
    is_active BOOLEAN DEFAULT true,
    is_known_exception BOOLEAN DEFAULT false,  -- Expected to be silent (hiatus, etc.)

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system',

    CONSTRAINT channels_youtube_handle_unique UNIQUE (youtube_handle)
);

-- Index for efficient queries
CREATE INDEX idx_channels_active ON channels(is_active) WHERE is_active = true;
CREATE INDEX idx_channels_domain ON channels(domain);
CREATE INDEX idx_channels_last_checked ON channels(last_checked_at);

-- ============================================
-- PIPELINE_ITEMS TABLE
-- Tracks individual video processing state
-- ============================================
CREATE TABLE IF NOT EXISTS pipeline_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- YouTube identifiers (dedup keys)
    youtube_video_id VARCHAR(11) NOT NULL,
    youtube_url TEXT NOT NULL,

    -- Video metadata (from RSS/API)
    title TEXT,
    description TEXT,
    thumbnail_url TEXT,
    published_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INT,

    -- Relationships
    channel_id UUID REFERENCES channels(id) ON DELETE SET NULL,

    -- Processing state
    status pipeline_status DEFAULT 'discovered',
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,

    -- Worker tracking (prevent duplicate processing)
    claimed_by VARCHAR(100),                   -- Worker ID that claimed this item
    claimed_at TIMESTAMP WITH TIME ZONE,

    -- External references
    speakr_recording_id VARCHAR(100),          -- ID in Speakr after upload
    surreal_video_id VARCHAR(100),             -- ID in SurrealDB after indexing

    -- Error tracking
    last_error TEXT,
    error_stage VARCHAR(50),                   -- Which stage failed

    -- Timestamps
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    queued_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Dedup constraint
    CONSTRAINT pipeline_items_youtube_unique UNIQUE (youtube_video_id)
);

-- Indexes for efficient queries
CREATE INDEX idx_pipeline_status ON pipeline_items(status);
CREATE INDEX idx_pipeline_channel ON pipeline_items(channel_id);
CREATE INDEX idx_pipeline_discovered ON pipeline_items(discovered_at DESC);
CREATE INDEX idx_pipeline_claimed ON pipeline_items(claimed_by, claimed_at)
    WHERE status IN ('downloading', 'uploading', 'transcribing', 'embedding', 'indexing');

-- ============================================
-- FAILED_ITEMS VIEW
-- Easy access to items in dead letter queue
-- ============================================
CREATE OR REPLACE VIEW failed_items AS
SELECT
    pi.*,
    c.name as channel_name,
    c.youtube_handle as channel_handle
FROM pipeline_items pi
LEFT JOIN channels c ON pi.channel_id = c.id
WHERE pi.status = 'failed'
ORDER BY pi.discovered_at DESC;

-- ============================================
-- CHANNEL_STATUS VIEW
-- Dashboard view of channel health
-- ============================================
CREATE OR REPLACE VIEW channel_status AS
SELECT
    c.id,
    c.youtube_handle,
    c.name,
    c.domain,
    c.is_active,
    c.ingestion_mode,
    c.last_checked_at,
    c.last_video_at,
    c.consecutive_failures,
    c.is_known_exception,
    COUNT(DISTINCT pi.id) FILTER (WHERE pi.status = 'indexed_full') as indexed_count,
    COUNT(DISTINCT pi.id) FILTER (WHERE pi.status = 'failed') as failed_count,
    COUNT(DISTINCT pi.id) FILTER (WHERE pi.status NOT IN ('indexed_full', 'indexed_light', 'failed')) as pending_count,
    -- Staleness check: 3 weeks without new content
    CASE
        WHEN c.is_known_exception THEN 'exception'
        WHEN c.last_video_at IS NULL THEN 'unknown'
        WHEN c.last_video_at < NOW() - INTERVAL '21 days' THEN 'stale'
        WHEN c.consecutive_failures >= 3 THEN 'error'
        ELSE 'healthy'
    END as health_status
FROM channels c
LEFT JOIN pipeline_items pi ON pi.channel_id = c.id
GROUP BY c.id
ORDER BY c.name;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Claim an item for processing (atomic)
CREATE OR REPLACE FUNCTION claim_pipeline_item(
    p_status pipeline_status,
    p_worker_id VARCHAR(100),
    p_limit INT DEFAULT 1
)
RETURNS SETOF pipeline_items AS $$
BEGIN
    RETURN QUERY
    WITH claimed AS (
        SELECT id FROM pipeline_items
        WHERE status = p_status
          AND (claimed_by IS NULL OR claimed_at < NOW() - INTERVAL '15 minutes')
        ORDER BY
            -- Priority: higher authority channels first
            (SELECT authority_score FROM channels WHERE id = channel_id) DESC NULLS LAST,
            discovered_at ASC
        LIMIT p_limit
        FOR UPDATE SKIP LOCKED
    )
    UPDATE pipeline_items pi
    SET
        claimed_by = p_worker_id,
        claimed_at = NOW(),
        status = CASE
            WHEN p_status = 'queued' THEN 'downloading'::pipeline_status
            ELSE status
        END
    FROM claimed
    WHERE pi.id = claimed.id
    RETURNING pi.*;
END;
$$ LANGUAGE plpgsql;

-- Release stale claims (run periodically)
CREATE OR REPLACE FUNCTION release_stale_claims(p_timeout_minutes INT DEFAULT 15)
RETURNS INT AS $$
DECLARE
    released_count INT;
BEGIN
    WITH released AS (
        UPDATE pipeline_items
        SET
            claimed_by = NULL,
            claimed_at = NULL,
            status = 'queued'
        WHERE claimed_at < NOW() - (p_timeout_minutes || ' minutes')::INTERVAL
          AND status IN ('downloading', 'uploading', 'transcribing', 'embedding', 'indexing')
        RETURNING id
    )
    SELECT COUNT(*) INTO released_count FROM released;

    RETURN released_count;
END;
$$ LANGUAGE plpgsql;

-- Compute RSS URL from handle
CREATE OR REPLACE FUNCTION compute_rss_url(p_handle VARCHAR)
RETURNS TEXT AS $$
BEGIN
    -- YouTube RSS feed format
    RETURN 'https://www.youtube.com/feeds/videos.xml?channel_id=' ||
           COALESCE(
               (SELECT youtube_channel_id FROM channels WHERE youtube_handle = p_handle),
               p_handle  -- Fallback to handle if no channel_id
           );
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGERS
-- ============================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER channels_updated_at
    BEFORE UPDATE ON channels
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- SEED DATA (Sample channels)
-- ============================================

-- Will be populated via Admin UI or CSV import
-- See: docs/reference-youtube-channels.md for full list

COMMENT ON TABLE channels IS 'YouTube channels monitored by KnowledgeEnroll';
COMMENT ON TABLE pipeline_items IS 'Individual video processing state for the ingestion pipeline';
