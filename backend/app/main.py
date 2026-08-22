"""Wiseweb-AI API entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config.logging import configure_logging
from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.security.rate_limit import RateLimitExceeded, rate_limit_handler

configure_logging()
logger = logging.getLogger("wisewebai.main")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    if settings.seed_demo:
        from scripts.seed_demo import seed_demo_if_needed
        seed_demo_if_needed()
        logger.info("demo seeding check complete")
    yield


app = FastAPI(
    title="Wiseweb-AI API",
    description=(
        "Wiseweb-AI — AI-powered Website Intelligence & Improvement Platform. "
        "Passive website analysis API. Not a penetration testing tool."
    ),
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

app.include_router(api_router)


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
