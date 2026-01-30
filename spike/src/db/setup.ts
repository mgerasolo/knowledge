import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { query, closePool } from "./client.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function setup() {
  console.log("Setting up database schema...");

  const schemaPath = join(__dirname, "schema.sql");
  const schema = readFileSync(schemaPath, "utf-8");

  try {
    await query(schema);
    console.log("Schema created successfully.");

    // Verify tables exist
    const result = await query(
      "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    );
    console.log(
      "Tables:",
      result.rows.map((r) => r.tablename)
    );

    // Verify extensions
    const extResult = await query(
      "SELECT extname FROM pg_extension ORDER BY extname"
    );
    console.log(
      "Extensions:",
      extResult.rows.map((r) => r.extname)
    );
  } catch (err) {
    console.error("Schema setup failed:", err);
    process.exit(1);
  } finally {
    await closePool();
  }
}

setup();
