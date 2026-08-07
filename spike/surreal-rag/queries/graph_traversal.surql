-- Graph Traversal Queries for SurrealDB Spike
-- These test the graph capabilities that differentiate SurrealDB from pure vector DBs

-- ============================================
-- Q1: All videos from a channel
-- ============================================

SELECT
    ->has_video->video.* AS videos
FROM channel
WHERE youtube_handle = "MyronGolden";

-- ============================================
-- Q2: All segments from a specific video
-- ============================================

SELECT
    ->has_segment->segment.* AS segments
FROM video
WHERE youtube_id = "jgNPX9K92Os"
ORDER BY segments.chunk_index;

-- ============================================
-- Q3: Channel statistics
-- ============================================

SELECT
    name,
    domain,
    count(->has_video->video) AS video_count,
    count(->has_video->video->has_segment->segment) AS segment_count
FROM channel
GROUP ALL;

-- ============================================
-- Q4: Topics mentioned across channels (future)
-- ============================================

-- Once we have topic extraction:
-- SELECT
--     topic.name,
--     count() AS mention_count,
--     array::distinct(<-mentions<-segment<-has_segment<-video<-has_video<-channel.name) AS channels
-- FROM topic
-- GROUP BY topic.name
-- ORDER BY mention_count DESC
-- LIMIT 20;

-- ============================================
-- Q5: Find related content (future)
-- Segments that share topics with a given segment
-- ============================================

-- LET $source_segment = segment:abc123;
-- SELECT
--     segment.*,
--     array::intersect($source_segment->mentions->topic, segment->mentions->topic) AS shared_topics
-- FROM segment
-- WHERE segment != $source_segment
-- AND array::len(shared_topics) > 0
-- ORDER BY array::len(shared_topics) DESC
-- LIMIT 10;
