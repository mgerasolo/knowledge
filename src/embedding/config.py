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

    # Speakr API
    SPEAKR_API_URL = os.getenv('SPEAKR_API_URL', 'http://10.0.0.33:5000/api')

    # Chunking
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '500'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '100'))

    # Flask
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('EMBEDDING_PORT', '5030'))
