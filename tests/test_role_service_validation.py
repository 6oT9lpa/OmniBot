import pytest

from application.services.role_service import RoleService


def test_validate_image_url_accepts_public_https_url():
    url = RoleService.validate_image_url("https://cdn.discordapp.com/icons/1/icon.png")
    assert url == "https://cdn.discordapp.com/icons/1/icon.png"


def test_validate_image_url_rejects_http_url():
    with pytest.raises(ValueError):
        RoleService.validate_image_url("http://example.com/icon.png")


def test_validate_image_url_rejects_private_ip():
    with pytest.raises(ValueError):
        RoleService.validate_image_url("https://127.0.0.1/icon.png")
