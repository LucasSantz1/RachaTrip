import pytest
from django.db import OperationalError, connection


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
