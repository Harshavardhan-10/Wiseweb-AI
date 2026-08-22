"""API v1 router."""

from fastapi import APIRouter

from app.api.routes.architecture import router as architecture_router
from app.api.routes.auth import router as auth_router
from app.api.routes.comparisons import router as comparisons_router
from app.api.routes.findings import router as findings_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.reports import router as reports_router
from app.api.routes.scans import router as scans_router
from app.api.routes.users import router as users_router
from app.api.routes.websites import router as websites_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(websites_router)
api_router.include_router(scans_router)
api_router.include_router(findings_router)
api_router.include_router(recommendations_router)
api_router.include_router(architecture_router)
api_router.include_router(comparisons_router)
api_router.include_router(monitoring_router)
api_router.include_router(reports_router)
