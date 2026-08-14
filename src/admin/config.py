"""Configuration for KnowledgeEnroll Admin API."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    # Database
    DB_HOST = os.getenv('KNOWLEDGE_DB_HOST', '10.0.0.33')
    DB_PORT = os.getenv('KNOWLEDGE_DB_PORT', '5010')
    DB_NAME = os.getenv('KNOWLEDGE_DB_NAME', 'knowledge')
    DB_USER = os.getenv('KNOWLEDGE_DB_USER', 'knowledge')
    DB_PASSWORD = os.getenv('KNOWLEDGE_DB_PASSWORD', '')

    @classmethod
    def get_db_url(cls):
        """Get PostgreSQL connection URL."""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

    @classmethod
    def get_db_config(cls):
        """Get database connection parameters as dict."""
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'dbname': cls.DB_NAME,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
        }

    # SurrealDB
    SURREAL_URL = os.getenv('SURREAL_URL', 'http://10.0.0.33:5040')
    SURREAL_NS = os.getenv('SURREAL_NS', 'knowledge')
    SURREAL_DB = os.getenv('SURREAL_DB', 'transcripts')
    SURREAL_USER = os.getenv('SURREAL_USER', 'root')
    SURREAL_PASS = os.getenv('SURREAL_PASS', 'changeme')

    # Embedding service (semantic search is proxied to it — it owns the
    # query-embedding call and the vector index)
    EMBEDDING_SERVICE_URL = os.getenv('EMBEDDING_SERVICE_URL',
                                      'http://knowledge-embedding:5030')

    # API Settings
    API_PREFIX = '/api/v1'
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    # URL Prefix (for reverse proxy path routing)
    # Set to '/enroll' when behind Traefik at knowledge.nextlevelfoundry.com/enroll/
    URL_PREFIX = os.getenv('URL_PREFIX', '')

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
