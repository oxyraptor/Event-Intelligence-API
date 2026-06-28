from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.domain.schemas import SearchResponse

router = APIRouter(tags=["search"])


def get_container(request: Request):
    return request.app.state.container


@router.get("/search", response_model=SearchResponse)
def search(
    request: Request,
    db: Session = Depends(get_db),
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=10, ge=1, le=50, alias="topK"),
    min_score: float | None = Query(default=None, alias="minScore"),
):
    settings = get_settings()
    service = get_container(request).search(db)
    return service.search(query=query, top_k=top_k, min_score=min_score if min_score is not None else settings.search_min_score)
