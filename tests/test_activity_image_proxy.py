import pytest
from fastapi import HTTPException

from activity.server.services.image_proxy_service import ImageProxyService


@pytest.mark.asyncio
async def test_image_proxy_rejects_non_https_url():
    service = ImageProxyService()

    with pytest.raises(HTTPException) as error:
        await service._validate_url("http://example.com/image.png")

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_image_proxy_rejects_private_network_address():
    service = ImageProxyService()

    with pytest.raises(HTTPException) as error:
        await service._validate_url("https://127.0.0.1/image.png")

    assert error.value.status_code == 400
