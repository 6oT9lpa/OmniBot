from fastapi import APIRouter, Depends, Query, Response

from activity.server.dependencies import require_bearer_token
from activity.server.services.access_service import ActivityAccessService
from activity.server.services.image_proxy_service import ImageProxyService
from infrastructure.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api/media", tags=["activity-media"])


@router.get("/image")
async def get_preview_image(
    guild_id: int = Query(gt=0),
    url: str = Query(min_length=1, max_length=2048),
    access_token: str = Depends(require_bearer_token),
) -> Response:
    logger.info("Activity preview image requested guild_id=%s", guild_id)
    await ActivityAccessService().ensure_panel_access(access_token, str(guild_id))
    content, content_type = await ImageProxyService().fetch_image(url)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )
