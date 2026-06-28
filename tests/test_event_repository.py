from __future__ import annotations

from datetime import UTC, datetime

from app.domain.models import Event
from app.repositories.event_repository import EventRepository


def _seed(repository: EventRepository) -> list[Event]:
    return [
        repository.create(
            user_id="user_a",
            event_name="product_viewed",
            timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            metadata={"category": "electronics"},
            raw_text="product_viewed -- category: electronics",
            embedding_model="model-a",
        ),
        repository.create(
            user_id="user_a",
            event_name="product_viewed",
            timestamp=datetime(2026, 6, 2, 12, 0, tzinfo=UTC),
            metadata={"category": "electronics"},
            raw_text="product_viewed -- category: electronics",
            embedding_model="model-a",
        ),
        repository.create(
            user_id="user_b",
            event_name="checkout_started",
            timestamp=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
            metadata={"category": "retail"},
            raw_text="checkout_started -- category: retail",
            embedding_model="model-b",
        ),
    ]


def test_create_and_get_by_ids_preserves_requested_order(db_session) -> None:
    repository = EventRepository(db_session)
    events = _seed(repository)

    rows = repository.get_by_ids([events[2].id, "missing", events[0].id])

    assert [row.id for row in rows] == [events[2].id, events[0].id]
    assert rows[0].user_id == "user_b"


def test_distinct_users_and_user_events(db_session) -> None:
    repository = EventRepository(db_session)
    events = _seed(repository)

    assert repository.distinct_user_ids() == ["user_a", "user_b"]
    assert [event.id for event in repository.events_for_user("user_a")] == [events[0].id, events[1].id]


def test_analytics_counts_and_grouping(db_session) -> None:
    repository = EventRepository(db_session)
    _seed(repository)

    from_timestamp = datetime(2026, 6, 2, 0, 0, tzinfo=UTC)
    to_timestamp = datetime(2026, 6, 3, 0, 0, tzinfo=UTC)

    assert repository.count_total(from_timestamp=from_timestamp, to_timestamp=to_timestamp) == 1
    assert repository.count_distinct_users(from_timestamp=from_timestamp, to_timestamp=to_timestamp) == 1
    assert repository.grouped_counts("event") == [("product_viewed", 2), ("checkout_started", 1)]
    assert repository.grouped_counts("user_id", limit=1) == [("user_a", 2)]