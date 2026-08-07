-- Knowledge Spike: PostgreSQL Schema
-- Throwaway prototype — capture everything YouTube gives us

CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    youtube_channel_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    custom_url TEXT,
    country TEXT,
    subscriber_count BIGINT,
    video_count BIGINT,
    view_count BIGINT,
    thumbnail_url TEXT,
    banner_url TEXT,
    published_at TIMESTAMPTZ,
    channel_type TEXT, -- expert/platform/curator/hybrid (nullable, set later)
    raw_api_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    channel_id INTEGER REFERENCES channels(id),
    youtube_video_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    published_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    url TEXT,
    thumbnail_url TEXT,
    view_count BIGINT,
    like_count BIGINT,
    comment_count BIGINT,
    tags TEXT[],
    category_id TEXT,
    default_language TEXT,
    default_audio_language TEXT,
    is_short BOOLEAN DEFAULT FALSE,
    aspect_ratio TEXT, -- landscape/portrait/square
    is_live_content BOOLEAN DEFAULT FALSE,
    transcript_status TEXT DEFAULT 'pending', -- pending/fetched/failed/no_transcript
    transcript_error TEXT,
    raw_api_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transcripts (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id),
    full_text TEXT NOT NULL,
    language TEXT,
    source TEXT, -- 'youtube-transcript-npm' / 'manual' etc.
    word_count INTEGER,
    char_count INTEGER,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS segments (
    id SERIAL PRIMARY KEY,
    video_id INTEGER REFERENCES videos(id),
    transcript_id INTEGER REFERENCES transcripts(id),
    text TEXT NOT NULL,
    start_time REAL, -- seconds from video start
    end_time REAL,
    speaker_label TEXT, -- NULL for spike (reserved for future diarization)
    embedding_id TEXT, -- Qdrant point ID
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_videos_youtube_video_id ON videos(youtube_video_id);
CREATE INDEX IF NOT EXISTS idx_videos_transcript_status ON videos(transcript_status);
CREATE INDEX IF NOT EXISTS idx_transcripts_video_id ON transcripts(video_id);
CREATE INDEX IF NOT EXISTS idx_segments_video_id ON segments(video_id);
CREATE INDEX IF NOT EXISTS idx_segments_transcript_id ON segments(transcript_id);

-- pg_trgm indexes for fuzzy search on names/titles
CREATE INDEX IF NOT EXISTS idx_channels_name_trgm ON channels USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_videos_title_trgm ON videos USING gin (title gin_trgm_ops);
