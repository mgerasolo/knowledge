import pytest
import requests

from surreal_client import SurrealClient, SurrealError, statement_errors


class FakeConfig:
    SURREAL_URL = "http://database.invalid"
    SURREAL_USER = "user"
    SURREAL_PASS = "super-secret"
    SURREAL_NS = "knowledge"
    SURREAL_DB = "transcripts"
    REQUEST_TIMEOUT = 1


class Response:
    def __init__(self, payload, fail=False):
        self.payload = payload
        self.fail = fail

    def raise_for_status(self):
        if self.fail:
            raise requests.HTTPError("upstream included super-secret")

    def json(self):
        return self.payload


class Session:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def post(self, *args, **kwargs):
        self.kwargs = kwargs
        return self.response


def test_query_binds_variables_in_params_header_and_checks_statement_status():
    session = Session(Response({"id": 1, "result": [{"status": "OK", "result": [{"count": 1}]}]}))
    result = SurrealClient(FakeConfig, session).result("RETURN $question;", {"question": "héllo"})
    assert result == [{"count": 1}]
    assert session.kwargs["json"]["method"] == "query"
    assert session.kwargs["json"]["params"] == ["RETURN $question;", {"question": "héllo"}]
    assert session.kwargs["headers"]["Content-Type"] == "application/json"

    errors = statement_errors([{"status": "ERR", "result": "bad statement"}])
    assert errors == ["bad statement"]


def test_transport_error_is_sanitized_and_does_not_expose_password():
    client = SurrealClient(FakeConfig, Session(Response({}, fail=True)))
    with pytest.raises(SurrealError) as caught:
        client.query("INFO FOR DB;")
    assert "super-secret" not in str(caught.value)
