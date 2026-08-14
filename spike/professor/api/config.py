"""Environment configuration for the Professor spike.

This is intentionally local to the spike.  It mirrors the embedding service's
configuration rather than importing across the spike/core boundary.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in the supervisor container
    def load_dotenv() -> bool:
        return False


load_dotenv()


class Config:
    """Professor service configuration, read once when the process starts."""

    SURREAL_URL = os.getenv("SURREAL_URL", "http://10.0.0.33:5040")
    SURREAL_USER = os.getenv("SURREAL_USER", "root")
    SURREAL_PASS = os.getenv("SURREAL_PASS", "changeme")
    SURREAL_NS = os.getenv("SURREAL_NS", "knowledge")
    SURREAL_DB = os.getenv("SURREAL_DB", "transcripts")

    LITELLM_URL = os.getenv(
        "LITELLM_URL", "http://10.0.0.27:2764/v1/embeddings"
    )
    LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text-v1.5")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
    EMBEDDING_QUERY_PREFIX = os.getenv("EMBEDDING_QUERY_PREFIX", "search_query: ")

    CHAT_MODEL = os.getenv("CHAT_MODEL", "claude-sonnet")
    EXTENSION_MODEL = os.getenv("EXTENSION_MODEL", "grok-4")
    ENABLE_EXTENSION_MODEL = os.getenv("ENABLE_EXTENSION_MODEL", "true").lower() == "true"
    CHAT_URL = os.getenv("LITELLM_CHAT_URL", "")

    TOP_K = int(os.getenv("PROFESSOR_TOP_K", "12"))
    MIN_COSINE = float(os.getenv("PROFESSOR_MIN_COSINE", "0.20"))
    REC_BOOST = float(os.getenv("REC_BOOST", "0.15"))
    REC_HORIZON_DAYS = int(os.getenv("REC_HORIZON_DAYS", "730"))
    REQUEST_TIMEOUT = float(os.getenv("PROFESSOR_REQUEST_TIMEOUT", "60"))
    INPUT_COST_PER_MILLION = float(os.getenv("INPUT_COST_PER_MILLION", "0"))
    OUTPUT_COST_PER_MILLION = float(os.getenv("OUTPUT_COST_PER_MILLION", "0"))

    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    PORT = int(os.getenv("PROFESSOR_PORT", "5050"))
    CORPUS_PATH = Path(
        os.getenv(
            "PROFESSOR_CORPUS_PATH",
            str(Path(__file__).resolve().parents[1] / "personalities" / "myron-golden.json"),
        )
    )

    @classmethod
    def chat_url(cls) -> str:
        """Derive the OpenAI-compatible chat endpoint from the embedding URL."""
        if cls.CHAT_URL:
            return cls.CHAT_URL
        base = cls.LITELLM_URL.rstrip("/")
        if base.endswith("/embeddings"):
            base = base[: -len("/embeddings")]
        return f"{base}/chat/completions"
