from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class StoredVector:
    event_id: str
    user_id: str
    event_name: str
    timestamp: str
    created_at: str
    raw_text: str
    embedding_model: str
    embedding: list[float]


def _normalize(vector: Sequence[float]) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_values = _normalize(left)
    right_values = _normalize(right)
    return sum(l * r for l, r in zip(left_values, right_values, strict=False))


class VectorStore:
    def __init__(self, persist_directory: str, collection_name: str, model_name: str) -> None:
        self._storage_dir = Path(persist_directory)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._storage_file = self._storage_dir / f"{collection_name}.json"
        self._records: dict[str, StoredVector] = {}
        self.model_name = model_name
        self._load()

    def _load(self) -> None:
        if not self._storage_file.exists():
            return
        payload = json.loads(self._storage_file.read_text(encoding="utf-8"))
        for item in payload.get("records", []):
            record = StoredVector(**item)
            self._records[record.event_id] = record

    def _save(self) -> None:
        payload = {"records": [asdict(record) for record in self._records.values()]}
        self._storage_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def upsert_event(
        self,
        *,
        event_id: str,
        user_id: str,
        event_name: str,
        timestamp: datetime | None,
        created_at: datetime,
        raw_text: str,
        embedding: Sequence[float],
    ) -> None:
        self._records[event_id] = StoredVector(
            event_id=event_id,
            user_id=user_id,
            event_name=event_name,
            timestamp=timestamp.isoformat() if timestamp is not None else "",
            created_at=created_at.isoformat(),
            raw_text=raw_text,
            embedding_model=self.model_name,
            embedding=_normalize(embedding),
        )
        self._save()

    def search(self, *, query_embedding: Sequence[float], top_k: int) -> dict[str, list]:
        scored: list[tuple[str, StoredVector, float]] = []
        for event_id, record in self._records.items():
            similarity = _cosine_similarity(query_embedding, record.embedding)
            scored.append((event_id, record, similarity))
        scored.sort(key=lambda item: item[2], reverse=True)
        scored = scored[:top_k]

        return {
            "ids": [[event_id for event_id, _, _ in scored]],
            "distances": [[1.0 - similarity for _, _, similarity in scored]],
            "metadatas": [
                [
                    {
                        "event_id": record.event_id,
                        "user_id": record.user_id,
                        "event": record.event_name,
                        "timestamp": record.timestamp,
                        "created_at": record.created_at,
                        "raw_text": record.raw_text,
                        "embedding_model": record.embedding_model,
                    }
                    for _, record, _ in scored
                ]
            ],
        }

    def get_embeddings_for_user(self, user_id: str) -> list[list[float]]:
        return [record.embedding for record in self._records.values() if record.user_id == user_id]
