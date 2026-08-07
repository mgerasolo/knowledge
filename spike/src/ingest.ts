import { writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { randomUUID } from "crypto";
import { config } from "./config.js";
import { query, closePool } from "./db/client.js";
import { ensureCollection, upsertVectors, getCollectionInfo } from "./qdrant/client.js";
import { getEmbedding, getEmbeddingBatch } from "./embeddings/client.js";
import {
  getChannelInfo,
  getChannelVideos,
  getVideoDetails,
  fetchTranscript,
  type TranscriptSegment,
  type VideoDetails,
  type ChannelInfo,
} from "./youtube/transcript.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SAMPLES_DIR = join(__dirname, "..", "samples");
const REPORTS_DIR = join(__dirname, "..", "reports");

// --- Time-based chunking ---

interface Chunk {
  text: string;
  start_time: number; // seconds
  end_time: number; // seconds
}

function chunkTranscript(
  segments: TranscriptSegment[],
  chunkDurationSec: number = 120 // 2 minutes default
): Chunk[] {
  if (segments.length === 0) return [];

  const chunks: Chunk[] = [];
  let currentTexts: string[] = [];
  let chunkStart = segments[0].offset / 1000;
  let chunkEnd = chunkStart;

  for (const seg of segments) {
    const segStartSec = seg.offset / 1000;
    const segEndSec = (seg.offset + seg.duration) / 1000;

    // Start a new chunk if we've exceeded the duration
    if (segStartSec - chunkStart >= chunkDurationSec && currentTexts.length > 0) {
      chunks.push({
        text: currentTexts.join(" ").trim(),
        start_time: chunkStart,
        end_time: chunkEnd,
      });
      currentTexts = [];
      chunkStart = segStartSec;
    }

    currentTexts.push(seg.text);
    chunkEnd = segEndSec;
  }

  // Final chunk
  if (currentTexts.length > 0) {
    chunks.push({
      text: currentTexts.join(" ").trim(),
      start_time: chunkStart,
      end_time: chunkEnd,
    });
  }

  return chunks;
}

// --- DB helpers ---

async function upsertChannel(info: ChannelInfo): Promise<number> {
  const result = await query(
    `INSERT INTO channels (
      youtube_channel_id, name, description, custom_url, country,
      subscriber_count, video_count, view_count,
      thumbnail_url, banner_url, published_at, raw_api_response
    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
    ON CONFLICT (youtube_channel_id) DO UPDATE SET
      name=EXCLUDED.name, subscriber_count=EXCLUDED.subscriber_count,
      video_count=EXCLUDED.video_count, view_count=EXCLUDED.view_count
    RETURNING id`,
    [
      info.youtube_channel_id, info.name, info.description, info.custom_url,
      info.country, info.subscriber_count, info.video_count, info.view_count,
      info.thumbnail_url, info.banner_url, info.published_at,
      JSON.stringify(info.raw_api_response),
    ]
  );
  return result.rows[0].id;
}

async function upsertVideo(
  channelDbId: number,
  details: VideoDetails
): Promise<number> {
  const result = await query(
    `INSERT INTO videos (
      channel_id, youtube_video_id, title, description, published_at,
      duration_seconds, url, thumbnail_url, view_count, like_count,
      comment_count, tags, category_id, default_language,
      default_audio_language, is_short, aspect_ratio, is_live_content,
      raw_api_response
    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
    ON CONFLICT (youtube_video_id) DO UPDATE SET
      view_count=EXCLUDED.view_count, like_count=EXCLUDED.like_count,
      comment_count=EXCLUDED.comment_count, updated_at=NOW()
    RETURNING id`,
    [
      channelDbId, details.youtube_video_id, details.title, details.description,
      details.published_at, details.duration_seconds, details.url,
      details.thumbnail_url, details.view_count, details.like_count,
      details.comment_count, details.tags, details.category_id,
      details.default_language, details.default_audio_language,
      details.is_short, details.aspect_ratio, details.is_live_content,
      JSON.stringify(details.raw_api_response),
    ]
  );
  return result.rows[0].id;
}

async function isVideoIngested(youtubeVideoId: string): Promise<boolean> {
  const result = await query(
    "SELECT transcript_status FROM videos WHERE youtube_video_id = $1 AND transcript_status = 'fetched'",
    [youtubeVideoId]
  );
  return result.rows.length > 0;
}

// --- Main ingestion ---

interface IngestResult {
  videoId: string;
  title: string;
  status: "success" | "skipped" | "failed";
  error?: string;
  segmentCount?: number;
  transcriptLength?: number;
  embeddingTimeMs?: number;
}

async function ingestVideo(
  channelDbId: number,
  channelName: string,
  details: VideoDetails,
  sampleIndex: number
): Promise<IngestResult> {
  const videoId = details.youtube_video_id;

  // Idempotency: skip if already ingested
  if (await isVideoIngested(videoId)) {
    return { videoId, title: details.title, status: "skipped" };
  }

  // Insert/update video record
  const videoDbId = await upsertVideo(channelDbId, details);

  // Fetch transcript
  let transcriptSegments: TranscriptSegment[];
  try {
    transcriptSegments = await fetchTranscript(videoId);
  } catch (err: any) {
    const errorMsg = err.message || "Unknown transcript error";
    await query(
      "UPDATE videos SET transcript_status = 'failed', transcript_error = $1 WHERE id = $2",
      [errorMsg, videoDbId]
    );
    return { videoId, title: details.title, status: "failed", error: errorMsg };
  }

  if (transcriptSegments.length === 0) {
    await query(
      "UPDATE videos SET transcript_status = 'no_transcript' WHERE id = $1",
      [videoDbId]
    );
    return { videoId, title: details.title, status: "failed", error: "Empty transcript" };
  }

  // Save raw sample for first few
  if (sampleIndex < 5) {
    const samplePath = join(SAMPLES_DIR, `sample-${videoId}.json`);
    writeFileSync(
      samplePath,
      JSON.stringify(
        { videoId, title: details.title, segments: transcriptSegments },
        null,
        2
      )
    );
  }

  // Build full text and store transcript
  const fullText = transcriptSegments.map((s) => s.text).join(" ");
  const wordCount = fullText.split(/\s+/).length;
  const charCount = fullText.length;

  const transcriptResult = await query(
    `INSERT INTO transcripts (video_id, full_text, language, source, word_count, char_count)
     VALUES ($1, $2, $3, $4, $5, $6) RETURNING id`,
    [videoDbId, fullText, "en", "youtube-transcript-npm", wordCount, charCount]
  );
  const transcriptDbId = transcriptResult.rows[0].id;

  // Chunk the transcript
  const chunks = chunkTranscript(transcriptSegments);

  // Generate embeddings and store segments
  const embeddingStart = Date.now();
  const chunkTexts = chunks.map((c) => c.text);

  // Batch embed (send up to 20 at a time to avoid payload limits)
  const allEmbeddings: number[][] = [];
  for (let i = 0; i < chunkTexts.length; i += 20) {
    const batch = chunkTexts.slice(i, i + 20);
    const embeddings = await getEmbeddingBatch(batch);
    allEmbeddings.push(...embeddings);
  }
  const embeddingTimeMs = Date.now() - embeddingStart;

  // Insert segments and Qdrant vectors
  const qdrantPoints: Array<{
    id: string;
    vector: number[];
    payload: any;
  }> = [];

  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i];
    const embeddingId = randomUUID();

    const segResult = await query(
      `INSERT INTO segments (video_id, transcript_id, text, start_time, end_time, embedding_id)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING id`,
      [videoDbId, transcriptDbId, chunk.text, chunk.start_time, chunk.end_time, embeddingId]
    );

    qdrantPoints.push({
      id: embeddingId,
      vector: allEmbeddings[i],
      payload: {
        segment_id: segResult.rows[0].id,
        video_id: videoDbId,
        channel_name: channelName,
        video_title: details.title,
        text: chunk.text,
        start_time: chunk.start_time,
        end_time: chunk.end_time,
        youtube_video_id: videoId,
      },
    });
  }

  // Batch upsert to Qdrant (50 at a time)
  for (let i = 0; i < qdrantPoints.length; i += 50) {
    await upsertVectors(qdrantPoints.slice(i, i + 50));
  }

  // Mark video as fetched
  await query("UPDATE videos SET transcript_status = 'fetched' WHERE id = $1", [
    videoDbId,
  ]);

  return {
    videoId,
    title: details.title,
    status: "success",
    segmentCount: chunks.length,
    transcriptLength: charCount,
    embeddingTimeMs,
  };
}

// --- Channel ingestion ---

async function ingestChannel(
  identifier: string,
  maxVideos: number = 50
): Promise<IngestResult[]> {
  console.log(`\n--- Ingesting channel: ${identifier} ---`);

  // Get channel info
  const channelInfo = await getChannelInfo(identifier);
  console.log(
    `Channel: ${channelInfo.name} (${channelInfo.subscriber_count?.toLocaleString()} subs, ${channelInfo.video_count} videos)`
  );

  // Upsert channel to DB
  const channelDbId = await upsertChannel(channelInfo);

  // Get video list from uploads playlist
  console.log(`Fetching up to ${maxVideos} recent videos...`);
  const playlistVideos = await getChannelVideos(
    channelInfo.uploads_playlist_id,
    maxVideos
  );
  console.log(`Found ${playlistVideos.length} videos in playlist.`);

  // Get detailed metadata for all videos
  const videoIds = playlistVideos.map((v) => v.youtube_video_id);
  console.log("Fetching video details...");
  const videoDetails = await getVideoDetails(videoIds);
  console.log(`Got details for ${videoDetails.length} videos.`);

  // Process each video
  const results: IngestResult[] = [];
  let sampleIndex = 0;

  for (let i = 0; i < videoDetails.length; i++) {
    const details = videoDetails[i];
    const prefix = `[${i + 1}/${videoDetails.length}]`;

    try {
      const result = await ingestVideo(
        channelDbId,
        channelInfo.name,
        details,
        sampleIndex
      );
      results.push(result);

      if (result.status === "success") {
        sampleIndex++;
        console.log(
          `${prefix} OK: "${details.title}" (${result.segmentCount} segments, ${result.embeddingTimeMs}ms embed)`
        );
      } else if (result.status === "skipped") {
        console.log(`${prefix} SKIP: "${details.title}" (already ingested)`);
      } else {
        console.log(`${prefix} FAIL: "${details.title}" — ${result.error}`);
      }
    } catch (err: any) {
      console.log(`${prefix} ERROR: "${details.title}" — ${err.message}`);
      results.push({
        videoId: details.youtube_video_id,
        title: details.title,
        status: "failed",
        error: err.message,
      });
    }
  }

  return results;
}

// --- Report generation ---

function generateReport(
  allResults: IngestResult[],
  startTime: number,
  channels: string[]
) {
  const succeeded = allResults.filter((r) => r.status === "success");
  const failed = allResults.filter((r) => r.status === "failed");
  const skipped = allResults.filter((r) => r.status === "skipped");

  const report = {
    timestamp: new Date().toISOString(),
    channels,
    summary: {
      total_attempted: allResults.length,
      succeeded: succeeded.length,
      failed: failed.length,
      skipped: skipped.length,
    },
    failures: failed.map((r) => ({
      videoId: r.videoId,
      title: r.title,
      error: r.error,
    })),
    metrics: {
      avg_transcript_length_chars:
        succeeded.length > 0
          ? Math.round(
              succeeded.reduce((s, r) => s + (r.transcriptLength || 0), 0) /
                succeeded.length
            )
          : 0,
      avg_segments_per_video:
        succeeded.length > 0
          ? Math.round(
              succeeded.reduce((s, r) => s + (r.segmentCount || 0), 0) /
                succeeded.length
            )
          : 0,
      avg_embedding_time_ms:
        succeeded.length > 0
          ? Math.round(
              succeeded.reduce((s, r) => s + (r.embeddingTimeMs || 0), 0) /
                succeeded.length
            )
          : 0,
      total_segments: succeeded.reduce(
        (s, r) => s + (r.segmentCount || 0),
        0
      ),
      total_wall_clock_ms: Date.now() - startTime,
    },
  };

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const reportPath = join(REPORTS_DIR, `run-${timestamp}.json`);
  writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`\nReport saved: ${reportPath}`);

  return report;
}

// --- Main entry point ---

async function main() {
  const startTime = Date.now();

  console.log("=== Knowledge Ingestion Spike ===\n");

  // Ensure Qdrant collection exists
  await ensureCollection();

  // Channel mix for testing (as suggested in spike prompt)
  const channels = [
    "@hubaborhegyi",     // Expert: Huberman Lab (solo, deep domain)
    "@lexfridman",       // Platform: Lex Fridman (host + guests)
    "@Fireship",         // Curator/news: Fireship (short tech content)
  ];

  // Allow CLI override: tsx src/ingest.ts @channel1 @channel2 ...
  const cliChannels = process.argv.slice(2);
  const targetChannels = cliChannels.length > 0 ? cliChannels : channels;

  const maxVideosPerChannel = config.BATCH_SIZE;
  const allResults: IngestResult[] = [];

  for (const channel of targetChannels) {
    try {
      const results = await ingestChannel(channel, maxVideosPerChannel);
      allResults.push(...results);
    } catch (err: any) {
      console.error(`\nFATAL ERROR for channel ${channel}: ${err.message}`);
    }
  }

  // Generate report
  const report = generateReport(allResults, startTime, targetChannels);

  // Print summary
  console.log("\n=== Summary ===");
  console.log(
    `Videos: ${report.summary.succeeded} succeeded, ${report.summary.failed} failed, ${report.summary.skipped} skipped`
  );
  console.log(
    `Segments: ${report.metrics.total_segments} total`
  );
  console.log(
    `Avg transcript: ${report.metrics.avg_transcript_length_chars} chars`
  );
  console.log(
    `Avg embedding time: ${report.metrics.avg_embedding_time_ms}ms per video`
  );
  console.log(
    `Wall clock: ${(report.metrics.total_wall_clock_ms / 1000).toFixed(1)}s`
  );

  // Get Qdrant collection stats
  try {
    const info = await getCollectionInfo();
    console.log(
      `Qdrant: ${info.vectors_count} vectors, status=${info.status}`
    );
  } catch {}

  await closePool();
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
