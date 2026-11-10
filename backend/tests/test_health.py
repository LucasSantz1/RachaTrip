import pytest
from django.db import InterfaceError, OperationalError, connection


@pytest.mark.django_db
def test_health_ok(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_down(client, monkeypatch):
    def broken():
        raise OperationalError("secret db detail: host=db password=hunter2")

    monkeypatch.setattr(connection, "ensure_connection", broken)
    response = client.get("/api/health/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert b"hunter2" not in response.content


def test_health_db_interface_error(client, monkeypatch):
    def broken():
        raise InterfaceError("connection already closed")

    monkeypatch.setattr(connection, "ensure_connection", broken)
    response = client.get("/api/health/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_options_exposes_no_metadata(client):
    response = client.options("/api/health/")
    assert "parses" not in response.content.decode()
    assert "renders" not in response.content.decode()


@pytest.mark.django_db
def test_health_security_headers(client):
    response = client.get("/api/health/")
    assert response["Referrer-Policy"] == "no-referrer"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"


@pytest.mark.django_db
def test_health_accepts_internal_api_host(client, settings):
    # O rewrite do Next envia "Host: api:8000"; sem "api" no ALLOWED_HOSTS o Django responde 400.
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "api"]
    response = client.get("/api/health/", HTTP_HOST="api:8000")
    assert response.status_code == 200
