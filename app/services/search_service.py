from __future__ import annotations

from app.domain.schemas import SearchResponse, SearchResult
from app.domain.serializers import event_to_read_schema
from app.repositories.event_repository import EventRepository
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


class SearchService:
    def __init__(self, repository: EventRepository, embedding_service: EmbeddingService, vector_store: VectorStore) -> None:
        self.repository = repository
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def search(self, *, query: str, top_k: int, min_score: float) -> SearchResponse:
        query_embedding = self.embedding_service.embed_text(query)
        result = self.vector_store.search(query_embedding=query_embedding, top_k=top_k)
        ids = result.get("ids", [[]])[0] or []
        distances = result.get("distances", [[]])[0] or []
        events = self.repository.get_by_ids(ids)
        events_by_id = {event.id: event for event in events}

        rows: list[SearchResult] = []
        for event_id, distance in zip(ids, distances, strict=False):
            event = events_by_id.get(event_id)
            if event is None:
                continue
            score = max(0.0, 1.0 - float(distance))
            if score < min_score:
                continue
            rows.append(SearchResult(event=event_to_read_schema(event), score=score))
        return SearchResponse(query=query, results=rows)
