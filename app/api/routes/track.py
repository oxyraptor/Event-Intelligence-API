from fastapi import APIRouter, Depends
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.schemas import EventCreate, TrackResponse

router = APIRouter(tags=["track"])


def get_container(request: Request):
    return request.app.state.container


@router.post("/track", response_model=TrackResponse)
def track_event(payload: EventCreate, db: Session = Depends(get_db), container=Depends(get_container)):
    service = container.ingestion(db)
    return service.track(payload)
