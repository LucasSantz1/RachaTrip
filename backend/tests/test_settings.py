import os
import secrets
import subprocess
import sys

import pytest
from django.conf import settings


def _load_settings(secret_key=None, debug=None):
    env = {k: v for k, v in os.environ.items() if k not in ("DJANGO_SECRET_KEY", "DJANGO_DEBUG")}
    if secret_key is not None:
        env["DJANGO_SECRET_KEY"] = secret_key
    if debug is not None:
        env["DJANGO_DEBUG"] = debug
    return subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; "
            "from django.conf import settings; settings.SECRET_KEY",
        ],
        env=env,
        capture_output=True,
        check=False,
    )


def test_missing_secret_key_fails():
    result = _load_settings()
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr.decode()


@pytest.mark.parametrize("key", ["", "   "])
def test_empty_secret_key_fails(key):
    result = _load_settings(secret_key=key)
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr.decode()


def test_placeholder_secret_key_fails_without_debug():
    result = _load_settings(secret_key="troque-isto")  # noqa: S106
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr.decode()


def test_short_secret_key_fails_without_debug():
    assert _load_settings(secret_key="a" * 49).returncode != 0


def test_padded_short_secret_key_fails_without_debug():
    assert _load_settings(secret_key="abc" + " " * 60).returncode != 0


def test_strong_secret_key_boots_without_debug():
    result = _load_settings(secret_key=secrets.token_urlsafe(45)[:60].ljust(60, "x"))
    assert result.returncode == 0, result.stderr.decode()


def test_default_api_permission_denies():
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == []
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAdminUser"
    ]
