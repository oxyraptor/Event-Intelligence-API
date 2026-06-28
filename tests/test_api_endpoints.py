from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.api.routes.search as search_route
import app.main as app_main
from app.core.database import get_db
from app.domain.schemas import (
    AnalyticsBreakdownRow,
    AnalyticsResponse,
    EventRead,
    SearchResponse,
    SearchResult,
    SimilarUserRow,
    SimilarUsersResponse,
    TrackResponse,
)
from app.main import create_app


class DummyService:
    def __init__(self, return_value=None, side_effect=None) -> None:
        self.return_value = return_value
        self.side_effect = side_effect
        self.calls: list[dict[str, object]] = []

    def track(self, payload):
        self.calls.append({"payload": payload})
        if self.side_effect is not None:
            raise self.side_effect
        return self.return_value

    def summarize(self, **kwargs):
        self.calls.append(kwargs)
        if self.side_effect is not None:
            raise self.side_effect
        return self.return_value

    def search(self, **kwargs):
        self.calls.append(kwargs)
        if self.side_effect is not None:
            raise self.side_effect
        return self.return_value

    def compare_users(self, **kwargs):
        self.calls.append(kwargs)
        if self.side_effect is not None:
            raise self.side_effect
        return self.return_value


class DummyContainer:
    def __init__(self, *, ingestion=None, analytics=None, search=None, similar_users=None) -> None:
        self._ingestion = ingestion
        self._analytics = analytics
        self._search = search
        self._similar_users = similar_users
        self.last_db = None

    def ingestion(self, db):
        self.last_db = db
        return self._ingestion

    def analytics(self, db):
        self.last_db = db
        return self._analytics

    def search(self, db):
        self.last_db = db
        return self._search

    def similar_users(self, db):
        self.last_db = db
        return self._similar_users


def _build_app(monkeypatch, container, *, search_min_score: float = 0.35):
    monkeypatch.setattr(
        app_main,
        "get_settings",
        lambda: SimpleNamespace(auto_create_tables=False, search_min_score=search_min_score),
    )
    app = create_app(container=container)
    app.dependency_overrides[get_db] = lambda: object()
    return app


def test_health_endpoint(monkeypatch) -> None:
    app = _build_app(monkeypatch, DummyContainer())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_track_endpoint_uses_ingestion_service(monkeypatch) -> None:
    timestamp = datetime(2026, 6, 27, 18, 0, 0, tzinfo=UTC)
    event = EventRead(
        id="event-1",
        user_id="user_123",
        event="product_viewed",
        timestamp=timestamp,
        created_at=timestamp,
        metadata={"category": "electronics"},
        raw_text="product_viewed -- category: electronics",
        embedding_model="model",
    )
    ingestion = DummyService(return_value=TrackResponse(event=event, vector_indexed=True))
    app = _build_app(monkeypatch, DummyContainer(ingestion=ingestion))
    client = TestClient(app)

    response = client.post(
        "/track",
        json={
            "userId": "user_123",
            "event": "product_viewed",
            "timestamp": "2026-06-27T18:00:00Z",
            "metadata": {"category": "electronics"},
        },
    )

    assert response.status_code == 200
    assert response.json()["vectorIndexed"] is True
    assert ingestion.calls[0]["payload"].user_id == "user_123"
    assert ingestion.calls[0]["payload"].event == "product_viewed"


def test_analytics_endpoint_validates_date_range(monkeypatch) -> None:
    app = _build_app(monkeypatch, DummyContainer())
    client = TestClient(app)

    response = client.get("/analytics?from=2026-06-28T00:00:00Z&to=2026-06-27T00:00:00Z")

    assert response.status_code == 400
    assert response.json() == {"detail": "from must be less than or equal to to"}


def test_analytics_endpoint_passes_query_aliases(monkeypatch) -> None:
    analytics = DummyService(
        return_value=AnalyticsResponse(
            total_count=2,
            distinct_users=1,
            event_breakdown=[AnalyticsBreakdownRow(key="product_viewed", count=2)],
            top_users=[AnalyticsBreakdownRow(key="user_123", count=2)],
        )
    )
    app = _build_app(monkeypatch, DummyContainer(analytics=analytics))
    client = TestClient(app)

    response = client.get("/analytics?event=product_viewed&userId=user_123&topN=5")

    assert response.status_code == 200
    assert response.json()["totalCount"] == 2
    assert analytics.calls[0]["event_name"] == "product_viewed"
    assert analytics.calls[0]["user_id"] == "user_123"
    assert analytics.calls[0]["top_limit"] == 5


def test_search_endpoint_uses_configured_default_min_score(monkeypatch) -> None:
    result = SearchResponse(
        query="electronics",
        results=[
            SearchResult(
                event=EventRead(
                    id="e1",
                    user_id="u1",
                    event="product_viewed",
                    timestamp=None,
                    created_at=datetime(2026, 6, 27, 18, 0, 0, tzinfo=UTC),
                    metadata={},
                    raw_text="product_viewed",
                    embedding_model=None,
                ),
                score=0.9,
            )
        ],
    )
    search = DummyService(return_value=result)
    app = _build_app(monkeypatch, DummyContainer(search=search), search_min_score=0.72)
    monkeypatch.setattr(search_route, "get_settings", lambda: SimpleNamespace(search_min_score=0.72))
    client = TestClient(app)

    response = client.get("/search?query=electronics&topK=3")

    assert response.status_code == 200
    assert response.json()["query"] == "electronics"
    assert search.calls[0]["min_score"] == 0.72
    assert search.calls[0]["top_k"] == 3


def test_search_endpoint_rejects_empty_query(monkeypatch) -> None:
    app = _build_app(monkeypatch, DummyContainer())
    client = TestClient(app)

    response = client.get("/search?query=")

    assert response.status_code == 422


def test_similar_users_endpoint_maps_lookup_error_to_404(monkeypatch) -> None:
    similar_users = DummyService(side_effect=LookupError("No events found for user_id=user_404"))
    app = _build_app(monkeypatch, DummyContainer(similar_users=similar_users))
    client = TestClient(app)

    response = client.get("/similar-users?userId=user_404")

    assert response.status_code == 404
    assert response.json() == {"detail": "No events found for user_id=user_404"}


def test_similar_users_endpoint_passes_top_n(monkeypatch) -> None:
    similar_users = DummyService(
        return_value=SimilarUsersResponse(
            user_id="user_123",
            results=[SimilarUserRow(user_id="user_456", score=0.83)],
        )
    )
    app = _build_app(monkeypatch, DummyContainer(similar_users=similar_users))
    client = TestClient(app)

    response = client.get("/similar-users?userId=user_123&topN=7")

    assert response.status_code == 200
    assert response.json()["userId"] == "user_123"
    assert similar_users.calls[0]["user_id"] == "user_123"
    assert similar_users.calls[0]["top_k"] == 7