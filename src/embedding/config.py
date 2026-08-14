"""Configuration for KnowledgeEnroll Embedding Service."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Embedding service configuration."""

    # SurrealDB
    SURREAL_URL = os.getenv('SURREAL_URL', 'http://10.0.0.33:5040')
    SURREAL_USER = os.getenv('SURREAL_USER', 'root')
    SURREAL_PASS = os.getenv('SURREAL_PASS', 'changeme')
    SURREAL_NS = os.getenv('SURREAL_NS', 'knowledge')
    SURREAL_DB = os.getenv('SURREAL_DB', 'transcripts')

    # LiteLLM (Embedding Model)
    LITELLM_URL = os.getenv('LITELLM_URL', 'http://10.0.0.27:2764/v1/embeddings')
    LITELLM_API_KEY = os.getenv('LITELLM_API_KEY', '')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'embeddings')
    # Dimension and task prefixes are properties of the chosen model, not of
    # this service: nomic-v2 (jarvis-embed) is 768-dim and trained with
    # 'search_document: '/'search_query: ' prefixes; OpenAI text-embedding-3
    # (the gateway 'embeddings' alias) is 1536-dim with no prefixes. Vectors
    # from different models are NOT interchangeable — changing the model means
    # re-embedding the corpus and redefining the index dimension.
    EMBEDDING_DIM = int(os.getenv('EMBEDDING_DIM', '1536'))
    EMBEDDING_DOC_PREFIX = os.getenv('EMBEDDING_DOC_PREFIX', '')
    EMBEDDING_QUERY_PREFIX = os.getenv('EMBEDDING_QUERY_PREFIX', '')

    # Speakr API
    SPEAKR_API_URL = os.getenv('SPEAKR_API_URL', 'http://10.0.0.33:5000/api')

    # Chunking
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '500'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '100'))

    # Flask
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('EMBEDDING_PORT', '5030'))
