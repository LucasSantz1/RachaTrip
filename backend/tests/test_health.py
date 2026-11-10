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


@pytest.mark.django_db
def test_health_security_headers(client):
    response = client.get("/api/health/")
    assert response["Referrer-Policy"] == "no-referrer"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
