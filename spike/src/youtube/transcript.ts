import { execFile } from "child_process";
import { readFileSync, unlinkSync, existsSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { promisify } from "util";
import { google } from "googleapis";
import { config } from "../config.js";

const execFileAsync = promisify(execFile);

const youtube = google.youtube({
  version: "v3",
  auth: config.YOUTUBE_API_KEY,
});

// Throttle helpers
const YT_API_THROTTLE = 200;
// 15s between transcript fetches = 4 req/min.
// YouTube rate-limits at ~20+ req/min (observed 429 at video 34 with 500ms delay).
// Conservative pace: we're not real-time, no reason to push it.
const TRANSCRIPT_THROTTLE = 15_000;
let lastApiCall = 0;
let lastTranscriptCall = 0;

async function throttleApi(): Promise<void> {
  const now = Date.now();
  const elapsed = now - lastApiCall;
  if (elapsed < YT_API_THROTTLE) {
    await new Promise((r) => setTimeout(r, YT_API_THROTTLE - elapsed));
  }
  lastApiCall = Date.now();
}

async function throttleTranscript(): Promise<void> {
  const now = Date.now();
  const elapsed = now - lastTranscriptCall;
  if (elapsed < TRANSCRIPT_THROTTLE) {
    await new Promise((r) => setTimeout(r, TRANSCRIPT_THROTTLE - elapsed));
  }
  lastTranscriptCall = Date.now();
}

// --- Channel operations ---

export interface ChannelInfo {
  youtube_channel_id: string;
  name: string;
  description: string;
  custom_url: string | null;
  country: string | null;
  subscriber_count: number | null;
  video_count: number | null;
  view_count: number | null;
  thumbnail_url: string | null;
  banner_url: string | null;
  published_at: string | null;
  uploads_playlist_id: string;
  raw_api_response: any;
}

/**
 * Resolve a channel identifier to channel info.
 * Accepts: @handle, channel URL, or channel ID (UC...)
 */
export async function getChannelInfo(
  identifier: string
): Promise<ChannelInfo> {
  await throttleApi();

  // Extract channel handle or ID from URL if needed
  let params: any = {
    part: ["snippet", "statistics", "contentDetails", "brandingSettings"],
  };

  if (identifier.startsWith("UC") && identifier.length === 24) {
    params.id = [identifier];
  } else if (identifier.startsWith("@")) {
    params.forHandle = identifier;
  } else {
    // Try to extract from URL
    const handleMatch = identifier.match(/@[\w.-]+/);
    const channelIdMatch = identifier.match(/channel\/(UC[\w-]+)/);
    if (handleMatch) {
      params.forHandle = handleMatch[0];
    } else if (channelIdMatch) {
      params.id = [channelIdMatch[1]];
    } else {
      throw new Error(`Cannot parse channel identifier: ${identifier}`);
    }
  }

  const response = await youtube.channels.list(params);
  const channel = response.data.items?.[0];
  if (!channel) {
    throw new Error(`Channel not found: ${identifier}`);
  }

  const snippet = channel.snippet!;
  const stats = channel.statistics!;
  const content = channel.contentDetails!;
  const branding = channel.brandingSettings;

  return {
    youtube_channel_id: channel.id!,
    name: snippet.title!,
    description: snippet.description || "",
    custom_url: snippet.customUrl || null,
    country: snippet.country || null,
    subscriber_count: stats.subscriberCount
      ? parseInt(stats.subscriberCount)
      : null,
    video_count: stats.videoCount ? parseInt(stats.videoCount) : null,
    view_count: stats.viewCount ? parseInt(stats.viewCount) : null,
    thumbnail_url: snippet.thumbnails?.high?.url || null,
    banner_url: branding?.image?.bannerExternalUrl || null,
    published_at: snippet.publishedAt || null,
    uploads_playlist_id: content.relatedPlaylists?.uploads!,
    raw_api_response: response.data.items![0],
  };
}

// --- Video listing (via uploads playlist, 1 unit/call) ---

export interface PlaylistVideoItem {
  youtube_video_id: string;
  title: string;
  description: string;
  published_at: string;
  thumbnail_url: string | null;
  thumbnail_width: number | null;
  thumbnail_height: number | null;
}

export async function getChannelVideos(
  uploadsPlaylistId: string,
  maxResults: number = 50
): Promise<PlaylistVideoItem[]> {
  const videos: PlaylistVideoItem[] = [];
  let pageToken: string | undefined;

  while (videos.length < maxResults) {
    await throttleApi();

    const response = await youtube.playlistItems.list({
      part: ["snippet"],
      playlistId: uploadsPlaylistId,
      maxResults: Math.min(50, maxResults - videos.length), // API max is 50 per page
      pageToken,
    });

    const items = response.data.items || [];
    for (const item of items) {
      const snippet = item.snippet!;
      const thumb =
        snippet.thumbnails?.maxres ||
        snippet.thumbnails?.high ||
        snippet.thumbnails?.medium;
      videos.push({
        youtube_video_id: snippet.resourceId?.videoId!,
        title: snippet.title!,
        description: snippet.description || "",
        published_at: snippet.publishedAt!,
        thumbnail_url: thumb?.url || null,
        thumbnail_width: thumb?.width || null,
        thumbnail_height: thumb?.height || null,
      });
    }

    pageToken = response.data.nextPageToken || undefined;
    if (!pageToken || items.length === 0) break;
  }

  return videos;
}

// --- Video metadata (detailed, via videos.list) ---

export interface VideoDetails {
  youtube_video_id: string;
  title: string;
  description: string;
  published_at: string;
  duration_seconds: number;
  url: string;
  thumbnail_url: string | null;
  thumbnail_width: number | null;
  thumbnail_height: number | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  tags: string[];
  category_id: string | null;
  default_language: string | null;
  default_audio_language: string | null;
  is_short: boolean;
  aspect_ratio: string;
  is_live_content: boolean;
  raw_api_response: any;
}

function parseDuration(iso8601: string): number {
  // Parse ISO 8601 duration (PT1H2M3S) to seconds
  const match = iso8601.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!match) return 0;
  const hours = parseInt(match[1] || "0");
  const minutes = parseInt(match[2] || "0");
  const seconds = parseInt(match[3] || "0");
  return hours * 3600 + minutes * 60 + seconds;
}

function inferAspectRatio(
  width: number | null,
  height: number | null
): string {
  if (!width || !height) return "landscape"; // default assumption
  const ratio = width / height;
  if (ratio > 1.2) return "landscape";
  if (ratio < 0.8) return "portrait";
  return "square";
}

export async function getVideoDetails(
  videoIds: string[]
): Promise<VideoDetails[]> {
  const results: VideoDetails[] = [];

  // API allows up to 50 IDs per call
  for (let i = 0; i < videoIds.length; i += 50) {
    await throttleApi();
    const batch = videoIds.slice(i, i + 50);

    const response = await youtube.videos.list({
      part: ["snippet", "contentDetails", "statistics", "liveStreamingDetails"],
      id: batch,
    });

    for (const video of response.data.items || []) {
      const snippet = video.snippet!;
      const content = video.contentDetails!;
      const stats = video.statistics!;
      const duration = parseDuration(content.duration || "PT0S");
      const thumb =
        snippet.thumbnails?.maxres ||
        snippet.thumbnails?.high ||
        snippet.thumbnails?.medium;

      results.push({
        youtube_video_id: video.id!,
        title: snippet.title!,
        description: snippet.description || "",
        published_at: snippet.publishedAt!,
        duration_seconds: duration,
        url: `https://www.youtube.com/watch?v=${video.id}`,
        thumbnail_url: thumb?.url || null,
        thumbnail_width: thumb?.width || null,
        thumbnail_height: thumb?.height || null,
        view_count: stats.viewCount ? parseInt(stats.viewCount) : null,
        like_count: stats.likeCount ? parseInt(stats.likeCount) : null,
        comment_count: stats.commentCount
          ? parseInt(stats.commentCount)
          : null,
        tags: snippet.tags || [],
        category_id: snippet.categoryId || null,
        default_language: snippet.defaultLanguage || null,
        default_audio_language: snippet.defaultAudioLanguage || null,
        is_short: duration > 0 && duration <= 60,
        aspect_ratio: inferAspectRatio(thumb?.width || null, thumb?.height || null),
        is_live_content: !!video.liveStreamingDetails,
        raw_api_response: video,
      });
    }
  }

  return results;
}

// --- Transcript fetching ---
// Primary: youtube-transcript-api (Python) — lightweight, no API key, works from residential IP
// Fallback: yt-dlp — heavier but more robust browser impersonation
//
// The JS npm packages (youtube-transcript, youtube-transcript-ts) are broken
// and cannot handle YouTube's current page structure. This is NOT an IP issue.

export interface TranscriptSegment {
  text: string;
  offset: number; // ms
  duration: number; // ms
}

// youtube-transcript-api CLI output format (installed via pipx)
interface PythonTranscriptEntry {
  text: string;
  start: number; // seconds (float)
  duration: number; // seconds (float)
}

/**
 * Primary method: youtube-transcript-api CLI (Python, installed via pipx).
 * No API key, no proxy, no VPN needed from residential network.
 * CLI binary: youtube_transcript_api (outputs JSON to stdout)
 */
async function fetchTranscriptPython(
  videoId: string
): Promise<TranscriptSegment[]> {
  const { stdout } = await execFileAsync("youtube_transcript_api", [
    videoId,
    "--languages", "en",
    "--format", "json",
  ], { timeout: 15000 });

  const parsed = JSON.parse(stdout);

  // CLI outputs a flat array of {text, start, duration}
  // (may be nested in an outer array for multi-video calls)
  const entries = (Array.isArray(parsed[0]) ? parsed[0] : parsed) as PythonTranscriptEntry[];
  return entries
    .filter((e) => {
      const text = e.text.trim();
      return text && text !== "[Music]" && text !== "[Applause]";
    })
    .map((e) => ({
      text: e.text.replace(/\n/g, " ").trim(),
      offset: Math.round(e.start * 1000),
      duration: Math.round(e.duration * 1000),
    }));
}

// yt-dlp JSON3 format types
interface Json3Event {
  tStartMs: number;
  dDurationMs?: number;
  segs?: Array<{ utf8: string }>;
  aAppend?: number;
}

/**
 * Fallback method: yt-dlp CLI.
 * Heavier (binary, temp files, 3-5s/video) but most robust.
 */
async function fetchTranscriptYtDlp(
  videoId: string
): Promise<TranscriptSegment[]> {
  const tmpBase = join(tmpdir(), `yt-transcript-${videoId}`);
  const subtitleFile = `${tmpBase}.en.json3`;

  try {
    await execFileAsync("yt-dlp", [
      "--write-auto-subs",
      "--skip-download",
      "--sub-format", "json3",
      "--sub-langs", "en",
      "-o", tmpBase,
      `https://www.youtube.com/watch?v=${videoId}`,
    ], { timeout: 30000 });

    if (!existsSync(subtitleFile)) {
      return [];
    }

    const raw = JSON.parse(readFileSync(subtitleFile, "utf-8"));
    const events: Json3Event[] = raw.events || [];

    const segments: TranscriptSegment[] = [];
    for (const event of events) {
      if (!event.segs) continue;
      const text = event.segs
        .map((s) => s.utf8)
        .join("")
        .replace(/\n/g, " ")
        .trim();
      if (!text || text === "[Music]" || text === "[Applause]") continue;

      segments.push({
        text,
        offset: event.tStartMs,
        duration: event.dDurationMs || 0,
      });
    }

    return segments;
  } finally {
    try { unlinkSync(subtitleFile); } catch {}
    try { unlinkSync(`${tmpBase}.en.vtt`); } catch {}
  }
}

/**
 * Fetch transcript with automatic fallback.
 * 1. Try youtube-transcript-api (Python) — fast, lightweight
 * 2. Fall back to yt-dlp — slower but more robust
 */
export async function fetchTranscript(
  videoId: string
): Promise<TranscriptSegment[]> {
  await throttleTranscript();

  // Primary: Python youtube-transcript-api
  try {
    const segments = await fetchTranscriptPython(videoId);
    if (segments.length > 0) {
      return segments;
    }
  } catch (err: any) {
    console.warn(
      `  [transcript] Python API failed for ${videoId}: ${err.message}. Trying yt-dlp...`
    );
  }

  // Fallback: yt-dlp
  try {
    return await fetchTranscriptYtDlp(videoId);
  } catch (err: any) {
    throw new Error(`Transcript fetch failed for ${videoId}: ${err.message}`);
  }
}
