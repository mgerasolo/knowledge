import { config } from "./config.js";
import { query, closePool } from "./db/client.js";
import { ensureCollection, getCollectionInfo, client } from "./qdrant/client.js";
import { getEmbedding } from "./embeddings/client.js";

async function preflight() {
  console.log("=== Pre-flight Checks ===\n");
  let allPassed = true;

  // 1. PostgreSQL
  try {
    const result = await query("SELECT version()");
    console.log("[OK] PostgreSQL:", result.rows[0].version.split(" on ")[0]);
    const tables = await query(
      "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    );
    console.log(
      "     Tables:",
      tables.rows.map((r) => r.tablename).join(", ")
    );
  } catch (err: any) {
    console.error("[FAIL] PostgreSQL:", err.message);
    allPassed = false;
  }

  // 2. Qdrant
  try {
    const health = await fetch(`${config.QDRANT_URL}/healthz`);
    const healthText = await health.text();
    console.log(`[OK] Qdrant: ${healthText.trim()}`);
    await ensureCollection();
    const info = await getCollectionInfo();
    console.log(
      `     Collection: ${info.vectors_count} vectors, status=${info.status}`
    );
  } catch (err: any) {
    console.error("[FAIL] Qdrant:", err.message);
    allPassed = false;
  }

  // 3. LiteLLM + Embedding model
  try {
    const modelsRes = await fetch(`${config.LITELLM_URL}/models`, {
      headers: { Authorization: `Bearer ${config.LITELLM_API_KEY}` },
    });
    if (!modelsRes.ok) throw new Error(`HTTP ${modelsRes.status}`);
    const models: any = await modelsRes.json();
    const modelNames = models.data.map((m: any) => m.id);
    const hasEmbedding = modelNames.some(
      (n: string) =>
        n.includes("embed") || n === config.EMBEDDING_MODEL
    );
    console.log(
      `[OK] LiteLLM: ${modelNames.length} models, embedding=${hasEmbedding ? "yes" : "NO"}`
    );

    // Test actual embedding
    const start = Date.now();
    const vec = await getEmbedding("preflight test");
    const elapsed = Date.now() - start;
    console.log(
      `     Embedding test: dim=${vec.length}, latency=${elapsed}ms`
    );
    if (vec.length !== config.EMBEDDING_DIMENSION) {
      console.warn(
        `[WARN] Dimension mismatch! Expected ${config.EMBEDDING_DIMENSION}, got ${vec.length}`
      );
    }
  } catch (err: any) {
    console.error("[FAIL] LiteLLM:", err.message);
    allPassed = false;
  }

  // 4. YouTube API
  try {
    const testUrl = `https://www.googleapis.com/youtube/v3/channels?part=id&forHandle=@Google&key=${config.YOUTUBE_API_KEY}`;
    const res = await fetch(testUrl);
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`HTTP ${res.status}: ${body}`);
    }
    const data: any = await res.json();
    console.log(
      `[OK] YouTube API: key valid, quota test passed (found ${data.items?.length || 0} channels)`
    );
  } catch (err: any) {
    console.error("[FAIL] YouTube API:", err.message);
    allPassed = false;
  }

  console.log(
    `\n=== ${allPassed ? "All checks passed" : "SOME CHECKS FAILED"} ===`
  );
  await closePool();
  process.exit(allPassed ? 0 : 1);
}

preflight();
