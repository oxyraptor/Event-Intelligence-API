from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.schemas import SimilarUsersResponse

router = APIRouter(tags=["similar-users"])


def get_container(request: Request):
    return request.app.state.container


@router.get("/similar-users", response_model=SimilarUsersResponse)
def similar_users(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Query(..., alias="userId"),
    top_n: int = Query(default=5, ge=1, le=50, alias="topN"),
):
    try:
        service = get_container(request).similar_users(db)
        return service.compare_users(user_id=user_id, top_k=top_n)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
