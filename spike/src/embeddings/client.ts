import { config } from "../config.js";

interface EmbeddingResponse {
  data: Array<{
    embedding: number[];
    index: number;
  }>;
  model: string;
  usage: {
    prompt_tokens: number;
    total_tokens: number;
  };
}

const THROTTLE_MS = 100;
let lastCall = 0;

async function throttle(): Promise<void> {
  const now = Date.now();
  const elapsed = now - lastCall;
  if (elapsed < THROTTLE_MS) {
    await new Promise((r) => setTimeout(r, THROTTLE_MS - elapsed));
  }
  lastCall = Date.now();
}

export async function getEmbedding(text: string): Promise<number[]> {
  await throttle();

  const response = await fetch(`${config.LITELLM_URL}/embeddings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.LITELLM_API_KEY}`,
    },
    body: JSON.stringify({
      model: config.EMBEDDING_MODEL,
      input: text,
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Embedding request failed (${response.status}): ${err}`);
  }

  const data: EmbeddingResponse = await response.json();
  return data.data[0].embedding;
}

export async function getEmbeddingBatch(
  texts: string[]
): Promise<number[][]> {
  // LiteLLM supports batch embeddings — send all at once
  await throttle();

  const response = await fetch(`${config.LITELLM_URL}/embeddings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.LITELLM_API_KEY}`,
    },
    body: JSON.stringify({
      model: config.EMBEDDING_MODEL,
      input: texts,
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(
      `Batch embedding request failed (${response.status}): ${err}`
    );
  }

  const data: EmbeddingResponse = await response.json();
  // Sort by index to maintain order
  return data.data
    .sort((a, b) => a.index - b.index)
    .map((d) => d.embedding);
}
