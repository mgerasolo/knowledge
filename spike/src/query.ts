import { config } from "./config.js";
import { closePool } from "./db/client.js";
import { getEmbedding } from "./embeddings/client.js";
import { searchSimilar } from "./qdrant/client.js";

function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

async function main() {
  const queryText = process.argv.slice(2).join(" ");
  if (!queryText) {
    console.log("Usage: npm run query -- <your question>");
    console.log('Example: npm run query -- "What does Huberman say about sleep?"');
    process.exit(1);
  }

  console.log(`\nQuery: "${queryText}"\n`);
  console.log("Generating embedding...");

  const vector = await getEmbedding(queryText);

  console.log("Searching Qdrant...\n");
  const results = await searchSimilar(vector, 10);

  if (results.length === 0) {
    console.log("No results found.");
    await closePool();
    return;
  }

  console.log(`Found ${results.length} results:\n`);
  console.log("=".repeat(80));

  for (let i = 0; i < results.length; i++) {
    const r = results[i];
    const p = r.payload;
    const timeRange = `${formatTimestamp(p.start_time)} - ${formatTimestamp(p.end_time)}`;
    const ytUrl = `https://www.youtube.com/watch?v=${p.youtube_video_id}&t=${Math.floor(p.start_time)}`;

    console.log(`\n#${i + 1} (score: ${r.score.toFixed(4)})`);
    console.log(`  Channel: ${p.channel_name}`);
    console.log(`  Video:   ${p.video_title}`);
    console.log(`  Time:    ${timeRange}`);
    console.log(`  Link:    ${ytUrl}`);
    console.log(`  ---`);
    // Truncate text for display
    const displayText =
      p.text.length > 300 ? p.text.substring(0, 300) + "..." : p.text;
    console.log(`  ${displayText}`);
    console.log("=".repeat(80));
  }

  await closePool();
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});
