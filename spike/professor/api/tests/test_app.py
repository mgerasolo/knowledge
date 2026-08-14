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
    body = response.get_json()
    assert body["personalities"]["myron-golden"] == 298
    assert body["personalities"]["chris-durkin"] == 344
    assert body["corpus_videos"] == 298 + 344

    monkeypatch.setattr(app_module, "db", ReachableDB(False))
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["surrealdb"] == "unreachable"


def test_personalities_endpoint_lists_both_professors():
    client = app_module.app.test_client()
    response = client.get("/api/personalities")
    assert response.status_code == 200
    listed = {p["personality_id"]: p for p in response.get_json()}
    assert listed["myron-golden"]["display_name"] == "Myron Golden"
    assert listed["chris-durkin"]["display_name"] == "Pastor Chris Durkin"


def test_ask_requires_bearer_key_when_configured(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setattr(app_module.Config, "PROFESSOR_API_KEY", "sekrit")
    monkeypatch.setitem(app_module.services, "myron-golden", FakeService())
    body = {"personality_id": "myron-golden", "question": "How?"}
    assert client.post("/api/ask", json=body).status_code == 401
    assert (
        client.post(
            "/api/ask", json=body, headers={"Authorization": "Bearer wrong"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/ask", json=body, headers={"Authorization": "Bearer sekrit"}
        ).status_code
        == 200
    )


def test_validate_secrets_aborts_on_missing_values(monkeypatch):
    monkeypatch.setattr(app_module.Config, "SURREAL_PASS", "")
    monkeypatch.setattr(app_module.Config, "LITELLM_API_KEY", "k")
    monkeypatch.setattr(app_module.Config, "PROFESSOR_API_KEY", "k")
    import pytest

    with pytest.raises(SystemExit, match="SURREAL_PASS"):
        app_module.Config.validate_secrets()


def test_ask_rejects_non_object_json_and_passes_valid_contract(monkeypatch):
    client = app_module.app.test_client()
    monkeypatch.setitem(app_module.services, "myron-golden", FakeService())
    assert client.post("/api/ask", json=[]).status_code == 400
    assert (
        client.post(
            "/api/ask", json={"personality_id": "nobody", "question": "How?"}
        ).status_code
        == 400
    )

    response = client.post(
        "/api/ask",
        json={"personality_id": "myron-golden", "question": "How?"},
    )
    assert response.status_code == 200
    assert set(response.get_json()["tiers"]) == {"said", "might_say", "extension"}
