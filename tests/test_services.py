from __future__ import annotations

from datetime import UTC, datetime

import sys
import types

from app.domain.schemas import EventCreate
from app.repositories.event_repository import EventRepository
from app.services.analytics_service import AnalyticsService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.search_service import SearchService
from app.services.similarity_service import SimilarityService


class FakeEmbeddingService:
    def __init__(self, model_name: str = "fake-model", embedding: list[float] | None = None) -> None:
        self.model_name = model_name
        self.embedding = embedding or [0.1, 0.2, 0.3]
        self.calls: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        return self.embedding


class FakeVectorStore:
    def __init__(self, *, search_result=None, fail_on_upsert: bool = False, embeddings_by_user: dict[str, list[list[float]]] | None = None) -> None:
        self.search_result = search_result or {"ids": [[]], "distances": [[]]}
        self.fail_on_upsert = fail_on_upsert
        self.embeddings_by_user = embeddings_by_user or {}
        self.upserts: list[dict[str, object]] = []
        self.search_calls: list[dict[str, object]] = []

    def upsert_event(self, **kwargs):
        self.upserts.append(kwargs)
        if self.fail_on_upsert:
            raise RuntimeError("vector store unavailable")

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return self.search_result

    def get_embeddings_for_user(self, user_id: str):
        return self.embeddings_by_user.get(user_id, [])


def _seed_repository(repository: EventRepository):
    first = repository.create(
        user_id="user_a",
        event_name="product_viewed",
        timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        metadata={"category": "electronics", "price": 1299},
        raw_text="product_viewed -- category: electronics | price: 1299",
        embedding_model="fake-model",
    )
    second = repository.create(
        user_id="user_b",
        event_name="checkout_started",
        timestamp=datetime(2026, 6, 2, 12, 0, tzinfo=UTC),
        metadata={"category": "retail"},
        raw_text="checkout_started -- category: retail",
        embedding_model="fake-model",
    )
    third = repository.create(
        user_id="user_c",
        event_name="search",
        timestamp=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
        metadata={"category": "retail"},
        raw_text="search -- category: retail",
        embedding_model="fake-model",
    )
    return first, second, third


def test_ingestion_service_tracks_and_indexes_event(db_session) -> None:
    repository = EventRepository(db_session)
    embedding_service = FakeEmbeddingService(embedding=[0.4, 0.5, 0.6])
    vector_store = FakeVectorStore()
    service = IngestionService(repository, embedding_service, vector_store)

    response = service.track(
        EventCreate(
            userId="user_123",
            event="product_viewed",
            timestamp="2026-06-27T18:00:00Z",
            metadata={"category": "electronics", "price": 1299},
        )
    )

    assert response.vector_indexed is True
    assert response.event.user_id == "user_123"
    assert response.event.raw_text == "product_viewed -- category: electronics | price: 1299"
    assert repository.count_total() == 1
    assert vector_store.upserts[0]["event_name"] == "product_viewed"
    assert embedding_service.calls == ["product_viewed -- category: electronics | price: 1299"]


def test_ingestion_service_keeps_event_when_vector_indexing_fails(db_session) -> None:
    repository = EventRepository(db_session)
    embedding_service = FakeEmbeddingService()
    vector_store = FakeVectorStore(fail_on_upsert=True)
    service = IngestionService(repository, embedding_service, vector_store)

    response = service.track(
        EventCreate(
            userId="user_123",
            event="checkout_started",
            metadata={},
        )
    )

    assert response.vector_indexed is False
    assert repository.count_total() == 1


def test_analytics_service_uses_repository_filters(db_session) -> None:
    repository = EventRepository(db_session)
    _seed_repository(repository)
    service = AnalyticsService(repository)

    response = service.summarize(
        event_name="product_viewed",
        user_id=None,
        from_timestamp=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
        to_timestamp=datetime(2026, 6, 30, 23, 59, tzinfo=UTC),
        top_limit=5,
    )

    assert response.total_count == 1
    assert response.distinct_users == 1
    assert response.event_breakdown[0].key == "product_viewed"
    assert response.top_users[0].key == "user_a"


def test_search_service_filters_by_score_and_missing_ids(db_session) -> None:
    repository = EventRepository(db_session)
    first, second, third = _seed_repository(repository)
    vector_store = FakeVectorStore(
        search_result={
            "ids": [[first.id, second.id, "missing", third.id]],
            "distances": [[0.1, 0.4, 0.2, 0.9]],
        }
    )
    service = SearchService(repository, FakeEmbeddingService(embedding=[1.0, 0.0, 0.0]), vector_store)

    response = service.search(query="electronics", top_k=4, min_score=0.5)

    assert response.query == "electronics"
    assert [result.event.id for result in response.results] == [first.id, second.id]
    assert response.results[0].score == 0.9
    assert response.results[1].score == 0.6


def test_similarity_service_ranks_users_and_limits_results(db_session) -> None:
    repository = EventRepository(db_session)
    _seed_repository(repository)
    vector_store = FakeVectorStore(
        embeddings_by_user={
            "user_a": [[1.0, 0.0]],
            "user_b": [[0.8, 0.2]],
            "user_c": [[0.0, 1.0]],
        }
    )
    service = SimilarityService(repository, vector_store)

    response = service.compare_users(user_id="user_a", top_k=1)

    assert response.user_id == "user_a"
    assert len(response.results) == 1
    assert response.results[0].user_id == "user_b"
    assert response.results[0].score == 0.9701425001453318


def test_similarity_service_raises_when_user_has_no_embeddings(db_session) -> None:
    repository = EventRepository(db_session)
    _seed_repository(repository)
    service = SimilarityService(repository, FakeVectorStore())

    try:
        service.compare_users(user_id="missing", top_k=5)
    except LookupError as exc:
        assert str(exc) == "No events found for user_id=missing"
    else:
        raise AssertionError("Expected LookupError")


def test_embedding_service_falls_back_when_sentence_transformer_is_unavailable(monkeypatch) -> None:
    fake_module = types.ModuleType("sentence_transformers")

    class BrokenSentenceTransformer:
        def __init__(self, model_name: str) -> None:
            raise RuntimeError("unavailable")

    fake_module.SentenceTransformer = BrokenSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    service = EmbeddingService("fake-model")
    vector = service.embed_text("hello world")

    assert service._model is None
    assert len(vector) == 384
    assert abs(sum(value * value for value in vector) - 1.0) < 1e-9