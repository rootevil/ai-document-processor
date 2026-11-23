
from app.core.config import settings


def test_application_name():
    assert settings.app_name == "Document AI"


def test_application_version():
    assert settings.app_version == "0.1.0"


def test_debug_mode():
    assert settings.debug is True


def test_api_prefix():
    assert settings.api_v1_prefix == "/api/v1"


def test_max_upload_size():
    assert settings.max_upload_size == 10 * 1024 * 1024
