"""Database connection utilities for KnowledgeEnroll Admin API."""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from config import Config


@contextmanager
def get_db_connection():
    """Get a database connection with automatic cleanup."""
    conn = None
    try:
        conn = psycopg2.connect(**Config.get_db_config())
        yield conn
    finally:
        if conn:
            conn.close()


@contextmanager
def get_db_cursor(commit=False):
    """Get a database cursor with automatic cleanup."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def test_connection():
    """Test database connectivity."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
