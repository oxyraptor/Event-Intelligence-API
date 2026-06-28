from __future__ import annotations

from app.domain.models import Event
from app.domain.schemas import EventRead


def event_to_read_schema(event: Event) -> EventRead:
    return EventRead(
        id=event.id,
        user_id=event.user_id,
        event=event.event,
        timestamp=event.timestamp,
        created_at=event.created_at,
        metadata=event.metadata_json,
        raw_text=event.raw_text,
        embedding_model=event.embedding_model,
    )
