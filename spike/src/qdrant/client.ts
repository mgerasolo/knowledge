import { QdrantClient } from "@qdrant/js-client-rest";
import { config } from "../config.js";

const COLLECTION_NAME = "knowledge_segments";

const client = new QdrantClient({
  url: config.QDRANT_URL,
});

export async function ensureCollection(): Promise<void> {
  const collections = await client.getCollections();
  const exists = collections.collections.some(
    (c) => c.name === COLLECTION_NAME
  );

  if (!exists) {
    console.log(
      `Creating Qdrant collection "${COLLECTION_NAME}" (dim=${config.EMBEDDING_DIMENSION}, cosine)...`
    );
    await client.createCollection(COLLECTION_NAME, {
      vectors: {
        size: config.EMBEDDING_DIMENSION,
        distance: "Cosine",
      },
    });

    // Create payload indexes for filtered search
    await client.createPayloadIndex(COLLECTION_NAME, {
      field_name: "video_id",
      field_schema: "integer",
    });
    await client.createPayloadIndex(COLLECTION_NAME, {
      field_name: "channel_name",
      field_schema: "keyword",
    });
    await client.createPayloadIndex(COLLECTION_NAME, {
      field_name: "youtube_video_id",
      field_schema: "keyword",
    });

    console.log("Collection created with payload indexes.");
  } else {
    console.log(`Collection "${COLLECTION_NAME}" already exists.`);
  }
}

export interface SegmentPayload {
  segment_id: number;
  video_id: number;
  channel_name: string;
  video_title: string;
  text: string;
  start_time: number;
  end_time: number;
  youtube_video_id: string;
}

export async function upsertVectors(
  points: Array<{
    id: string;
    vector: number[];
    payload: SegmentPayload;
  }>
): Promise<void> {
  if (points.length === 0) return;

  await client.upsert(COLLECTION_NAME, {
    wait: true,
    points: points.map((p) => ({
      id: p.id,
      vector: p.vector,
      payload: p.payload as unknown as Record<string, unknown>,
    })),
  });
}

export interface SearchResult {
  score: number;
  payload: SegmentPayload;
}

export async function searchSimilar(
  vector: number[],
  limit: number = 10
): Promise<SearchResult[]> {
  const results = await client.search(COLLECTION_NAME, {
    vector,
    limit,
    with_payload: true,
  });

  return results.map((r) => ({
    score: r.score,
    payload: r.payload as unknown as SegmentPayload,
  }));
}

export async function getCollectionInfo() {
  return client.getCollection(COLLECTION_NAME);
}

export { client, COLLECTION_NAME };
