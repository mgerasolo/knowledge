import app as app_module
from service import AskValidationError


class ReachableDB:
    def __init__(self, reachable):
        self._reachable = reachable

    def reachable(self):
        return self._reachable


class FakeService:
    def ask(self, personality_id, question, history):
        if not question:
            raise AskValidationError("question must be a non-empty string")
        return {
            "tiers": {"said": [], "might_say": "Inference", "extension": "General AI"},
            "citations": {},
            "disclaimer": "AI recreation from public videos",
            "meta": {"model": "test", "chunks_searched": 0, "retrieval_ms": 0, "cost_estimate_usd": 0},
        }


def test_health_is_200_only_when_database_and_corpus_are_ready(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "db", ReachableDB(True))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["corpus_videos"] == 298

    monkeypatch.setattr(app_module, "db", ReachableDB(False))
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["surrealdb"] == "unreachable"


def test_ask_rejects_non_object_json_and_passes_valid_contract(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module, "service", FakeService())
    assert client.post("/api/ask", json=[]).status_code == 400

    response = client.post(
        "/api/ask",
        json={"personality_id": "myron-golden", "question": "How?"},
    )
    assert response.status_code == 200
    assert set(response.get_json()["tiers"]) == {"said", "might_say", "extension"}
