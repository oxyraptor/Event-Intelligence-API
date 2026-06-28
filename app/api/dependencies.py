from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.event_repository import EventRepository
from app.services.analytics_service import AnalyticsService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.search_service import SearchService
from app.services.similarity_service import SimilarityService
from app.services.vector_store import VectorStore


@dataclass(slots=True)
class AppContainer:
    repository_factory: Callable[[Session], EventRepository]
    embedding_service: EmbeddingService
    vector_store: VectorStore

    def repository(self, session: Session) -> EventRepository:
        return self.repository_factory(session)

    def ingestion(self, session: Session) -> IngestionService:
        return IngestionService(self.repository(session), self.embedding_service, self.vector_store)

    def analytics(self, session: Session) -> AnalyticsService:
        return AnalyticsService(self.repository(session))

    def search(self, session: Session) -> SearchService:
        return SearchService(self.repository(session), self.embedding_service, self.vector_store)

    def similar_users(self, session: Session) -> SimilarityService:
        return SimilarityService(self.repository(session), self.vector_store)


def build_container() -> AppContainer:
    settings = get_settings()
    embedding_service = EmbeddingService(settings.embedding_model_name)
    vector_store = VectorStore(settings.chroma_persist_directory, settings.chroma_collection_name, settings.embedding_model_name)
    return AppContainer(repository_factory=EventRepository, embedding_service=embedding_service, vector_store=vector_store)
