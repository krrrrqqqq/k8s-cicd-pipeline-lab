import pytest

from app.main import create_app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("WARMUP_SECONDS", "0")
    return create_app().test_client()


def test_index_returns_service_info(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["service"] == "status-api"
    assert "version" in body


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_readyz_ok_after_warmup(client):
    resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.get_json()["ready"] is True


def test_metrics_exposed(client):
    client.get("/")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert b"status_api_requests_total" in resp.data
