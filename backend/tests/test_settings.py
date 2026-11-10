import os
import subprocess
import sys

from django.conf import settings


def test_missing_secret_key_fails():
    env = {k: v for k, v in os.environ.items() if k != "DJANGO_SECRET_KEY"}
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "import django, os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; "
            "django.setup()",
        ],
        env=env,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0


def test_default_api_permission_denies():
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == []
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAdminUser"
    ]
