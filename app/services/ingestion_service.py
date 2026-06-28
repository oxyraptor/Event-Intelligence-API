from __future__ import annotations

import logging

from app.domain.serializers import event_to_read_schema
from app.domain.schemas import EventCreate, TrackResponse
from app.repositories.event_repository import EventRepository
from app.services.embedding_service import EmbeddingService
from app.services.text_builder import build_event_text
from app.services.vector_store import VectorStore


logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, repository: EventRepository, embedding_service: EmbeddingService, vector_store: VectorStore) -> None:
        self.repository = repository
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def track(self, payload: EventCreate) -> TrackResponse:
        raw_text = build_event_text(payload.event, payload.metadata)
        event = self.repository.create(
            user_id=payload.user_id,
            event_name=payload.event,
            timestamp=payload.timestamp,
            metadata=payload.metadata,
            raw_text=raw_text,
            embedding_model=self.embedding_service.model_name,
        )

        vector_indexed = False
        try:
            embedding = self.embedding_service.embed_text(raw_text)
            self.vector_store.upsert_event(
                event_id=event.id,
                user_id=event.user_id,
                event_name=event.event,
                timestamp=event.timestamp,
                created_at=event.created_at,
                raw_text=raw_text,
                embedding=embedding,
            )
            vector_indexed = True
        except Exception:
            logger.exception("vector indexing failed after event persistence", extra={"event_id": event.id, "stage": "vector_index"})

        return TrackResponse(event=event_to_read_schema(event), vector_indexed=vector_indexed)
