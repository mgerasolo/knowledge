-- Semantic Search Queries for SurrealDB Spike
-- Run with: surreal sql --ns knowledgespike --db transcripts

-- ============================================
-- Q1: Basic Semantic Search
-- Find segments similar to a query embedding
-- ============================================

-- Replace $query_embedding with actual embedding array
-- LET $query_embedding = [0.1, 0.2, ...]; -- 768 dimensions

SELECT
    id,
    text,
    chunk_index,
    <-has_segment<-video.title AS video_title,
    <-has_segment<-video<-has_video<-channel.name AS channel_name
FROM segment
WHERE embedding <|10,100|> $query_embedding
LIMIT 10;

-- ============================================
-- Q2: Search within a specific channel
-- ============================================

SELECT
    id,
    text,
    <-has_segment<-video.title AS video_title
FROM segment
WHERE embedding <|10,100|> $query_embedding
AND <-has_segment<-video<-has_video<-channel.youtube_handle = "MyronGolden"
LIMIT 10;

-- ============================================
-- Q3: Search within a domain
-- ============================================

SELECT
    id,
    text,
    <-has_segment<-video.title AS video_title,
    <-has_segment<-video<-has_video<-channel.name AS channel_name
FROM segment
WHERE embedding <|10,100|> $query_embedding
AND <-has_segment<-video<-has_video<-channel.domain = "ai-coding"
LIMIT 10;

-- ============================================
-- Q4: Get full context for a segment
-- ============================================

LET $segment_id = segment:abc123;

SELECT
    *,
    <-has_segment<-video AS video,
    <-has_segment<-video<-has_video<-channel AS channel
FROM $segment_id;
