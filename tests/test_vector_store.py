from __future__ import annotations

from datetime import UTC, datetime

from app.services.vector_store import VectorStore


def test_vector_store_persists_and_searches(tmp_path) -> None:
    store = VectorStore(str(tmp_path), "events", "model-a")
    store.upsert_event(
        event_id="event-1",
        user_id="user-a",
        event_name="product_viewed",
        timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        created_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        raw_text="product_viewed -- category: electronics",
        embedding=[1.0, 0.0],
    )
    store.upsert_event(
        event_id="event-2",
        user_id="user-b",
        event_name="checkout_started",
        timestamp=None,
        created_at=datetime(2026, 6, 2, 12, 0, tzinfo=UTC),
        raw_text="checkout_started -- category: retail",
        embedding=[0.0, 1.0],
    )

    search = store.search(query_embedding=[1.0, 0.0], top_k=2)

    assert search["ids"][0] == ["event-1", "event-2"]
    assert search["distances"][0][0] == 0.0
    assert search["metadatas"][0][0]["event"] == "product_viewed"

    reloaded = VectorStore(str(tmp_path), "events", "model-a")
    assert reloaded.get_embeddings_for_user("user-a") == [[1.0, 0.0]]
    assert reloaded.get_embeddings_for_user("missing") == []