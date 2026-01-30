import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

dotenv.config({ path: join(__dirname, "..", ".env") });

function required(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required env var: ${key}`);
  }
  return value;
}

export const config = {
  QDRANT_URL: required("QDRANT_URL"),
  LITELLM_URL: required("LITELLM_URL"),
  LITELLM_API_KEY: required("LITELLM_API_KEY"),
  POSTGRES_URL: required("POSTGRES_URL"),
  YOUTUBE_API_KEY: required("YOUTUBE_API_KEY"),
  EMBEDDING_MODEL: process.env.EMBEDDING_MODEL || "nomic-embed",
  EMBEDDING_DIMENSION: parseInt(process.env.EMBEDDING_DIMENSION || "768", 10),
  BATCH_SIZE: parseInt(process.env.BATCH_SIZE || "50", 10),
};
