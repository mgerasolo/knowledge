import sys
import socket
from pathlib import Path

import pytest


API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Fail any test that accidentally reaches the network."""
    def denied(*args, **kwargs):
        raise AssertionError("unit tests must not access the network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
