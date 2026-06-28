from fastapi import APIRouter

from app.api.routes.analytics import router as analytics_router
from app.api.routes.health import router as health_router
from app.api.routes.search import router as search_router
from app.api.routes.similar_users import router as similar_users_router
from app.api.routes.track import router as track_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(track_router)
api_router.include_router(analytics_router)
api_router.include_router(search_router)
api_router.include_router(similar_users_router)
