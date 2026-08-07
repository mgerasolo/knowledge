"""SurrealDB client for embedding service."""
import hashlib
import requests
from config import Config


def surreal_query(query: str):
    """Execute SurrealDB query."""
    try:
        response = requests.post(
            f"{Config.SURREAL_URL}/sql",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "surreal-ns": Config.SURREAL_NS,
                "surreal-db": Config.SURREAL_DB,
            },
            auth=(Config.SURREAL_USER, Config.SURREAL_PASS),
            data=query,
            timeout=30
        )
        if response.ok:
            return response.json()
        else:
            print(f"SurrealDB error: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"SurrealDB connection error: {e}")
    return None


def statement_errors(payload) -> list:
    """Pull statement-level error messages out of a SurrealDB response.

    SurrealDB answers HTTP 200 even when individual statements are rejected —
    the failure only shows up as {"status": "ERR"} inside the payload. Callers
    that check for a non-None result therefore read a rejected write as a
    success. This is what let 1,086 videos be marked "indexed" while the
    database held nothing (2026-08-05).
    """
    if not isinstance(payload, list):
        return ["unexpected response shape from SurrealDB"]
    return [
        str(stmt.get("result", "unknown error"))
        for stmt in payload
        if isinstance(stmt, dict) and stmt.get("status") == "ERR"
    ]


def surreal_write(query: str):
    """Execute a write and confirm it actually landed.

    Returns (ok, error). Every write path must use this rather than calling
    surreal_query() and assuming a non-None return means success.
    """
    result = surreal_query(query)
    if result is None:
        return False, "SurrealDB unreachable or returned a non-200 response"
    errors = statement_errors(result)
    if errors:
        return False, "; ".join(errors)
    return True, None


def test_connection():
    """Test SurrealDB connectivity AND that our namespace/database resolve.

    A reachable server with a missing namespace answers 200 with an error body,
    which previously reported as "connected".
    """
    ok, _ = surreal_write("INFO FOR DB;")
    return ok


def create_safe_id(text: str) -> str:
    """Create a safe ID from text."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


def escape_string(text: str) -> str:
    """Escape string for SurrealDB query."""
    if not text:
        return ""
    # Escape in order: backslash first, then others
    escaped = text.replace("\\", "\\\\")
    escaped = escaped.replace("'", "\\'")
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace("\r", "\\r")
    escaped = escaped.replace("\t", "\\t")
    # Remove null bytes and other control characters
    escaped = ''.join(c for c in escaped if ord(c) >= 32 or c in '\n\r\t')
    return escaped
