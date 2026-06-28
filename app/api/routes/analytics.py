from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.schemas import AnalyticsResponse

router = APIRouter(tags=["analytics"])


def get_container(request: Request):
    return request.app.state.container


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(
    request: Request,
    db: Session = Depends(get_db),
    event: str | None = Query(default=None),
    user_id: str | None = Query(default=None, alias="userId"),
    from_timestamp: datetime | None = Query(default=None, alias="from"),
    to_timestamp: datetime | None = Query(default=None, alias="to"),
    top_n: int = Query(default=10, ge=1, le=100, alias="topN"),
):
    if from_timestamp is not None and to_timestamp is not None and from_timestamp > to_timestamp:
        raise HTTPException(status_code=400, detail="from must be less than or equal to to")
    service = get_container(request).analytics(db)
    return service.summarize(
        event_name=event,
        user_id=user_id,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        top_limit=top_n,
    )
