import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from infrastructure.config import get_config
from infrastructure.logging import get_logger


logger = get_logger(__name__)


def configure_activity_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_activity_request(request: Request, call_next):
        started = time.perf_counter()
        logger.info("Activity request started method=%s path=%s", request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "Activity request failed method=%s path=%s elapsed_ms=%s",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path == "/api/auth/token":
            response.headers["Cache-Control"] = "no-store"
        logger.info(
            "Activity request completed method=%s path=%s status=%s elapsed_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    allowed_origins = [
        origin.strip()
        for origin in get_config().activity_allowed_origins.split(",")
        if origin.strip()
    ]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )
