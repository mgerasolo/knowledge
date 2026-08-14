"""Small SurrealDB HTTP client adapted from ``src/embedding/surreal_client.py``."""
from itertools import count
from typing import Any, Mapping, Optional

import requests

try:
    from .config import Config
except ImportError:  # direct execution from api/
    from config import Config


class SurrealError(RuntimeError):
    """SurrealDB transport or statement failure without credential details."""


def statement_errors(payload: Any) -> list[str]:
    """Return statement-level errors because Surreal may return them with HTTP 200."""
    if not isinstance(payload, list):
        return ["unexpected response shape from SurrealDB"]
    return [
        str(stmt.get("result", "unknown statement error"))
        for stmt in payload
        if isinstance(stmt, dict) and stmt.get("status") == "ERR"
    ]


class SurrealClient:
    """Execute SQL with bind variables through the Surreal HTTP endpoint."""

    def __init__(self, config: type[Config] = Config, session: Any = requests):
        self.config = config
        self.session = session
        self._request_ids = count(1)

    def query(self, sql: str, variables: Optional[Mapping[str, Any]] = None) -> list:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "surreal-ns": self.config.SURREAL_NS,
            "surreal-db": self.config.SURREAL_DB,
        }
        try:
            response = self.session.post(
                f"{self.config.SURREAL_URL.rstrip('/')}/rpc",
                headers=headers,
                auth=(self.config.SURREAL_USER, self.config.SURREAL_PASS),
                json={
                    "id": next(self._request_ids),
                    "method": "query",
                    "params": [sql, dict(variables or {})],
                },
                timeout=self.config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            rpc_payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise SurrealError("SurrealDB request failed") from exc
        if not isinstance(rpc_payload, dict):
            raise SurrealError("unexpected RPC response shape from SurrealDB")
        if rpc_payload.get("error"):
            error = rpc_payload["error"]
            message = error.get("message", "RPC query failed") if isinstance(error, dict) else "RPC query failed"
            raise SurrealError(str(message))
        payload = rpc_payload.get("result")
        errors = statement_errors(payload)
        if errors:
            raise SurrealError("; ".join(errors))
        return payload

    def result(self, sql: str, variables: Optional[Mapping[str, Any]] = None) -> Any:
        payload = self.query(sql, variables)
        if not payload or not isinstance(payload[0], dict):
            raise SurrealError("SurrealDB returned no statement result")
        return payload[0].get("result")

    def write(self, sql: str, variables: Optional[Mapping[str, Any]] = None) -> None:
        self.query(sql, variables)

    def reachable(self) -> bool:
        try:
            self.query("INFO FOR DB;")
            return True
        except SurrealError:
            return False


_default_client = SurrealClient()


def surreal_query(query: str, variables: Optional[Mapping[str, Any]] = None) -> list:
    """Compatibility helper matching the core module's function-level convention."""
    return _default_client.query(query, variables)


def surreal_write(query: str, variables: Optional[Mapping[str, Any]] = None) -> tuple[bool, Optional[str]]:
    try:
        _default_client.write(query, variables)
        return True, None
    except SurrealError as exc:
        return False, str(exc)


def test_connection() -> bool:
    return _default_client.reachable()
