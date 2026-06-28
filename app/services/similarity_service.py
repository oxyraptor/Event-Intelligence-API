from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from app.domain.schemas import SimilarUserRow, SimilarUsersResponse
from app.repositories.event_repository import EventRepository
from app.services.vector_store import VectorStore


def _normalize(vector: Sequence[float]) -> np.ndarray:
    array = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(array)
    if norm == 0:
        return array
    return array / norm


def _average(vectors: list[Sequence[float]]) -> np.ndarray:
    stacked = np.asarray([np.asarray(vector, dtype=float) for vector in vectors], dtype=float)
    mean_vector = stacked.mean(axis=0)
    return _normalize(mean_vector)


class SimilarityService:
    def __init__(self, repository: EventRepository, vector_store: VectorStore) -> None:
        self.repository = repository
        self.vector_store = vector_store

    def compare_users(self, *, user_id: str, top_k: int) -> SimilarUsersResponse:
        target_vectors = self.vector_store.get_embeddings_for_user(user_id)
        if not target_vectors:
            raise LookupError(f"No events found for user_id={user_id}")

        target_profile = _average(target_vectors)
        rows: list[SimilarUserRow] = []
        for other_user_id in self.repository.distinct_user_ids():
            if other_user_id == user_id:
                continue
            user_vectors = self.vector_store.get_embeddings_for_user(other_user_id)
            if not user_vectors:
                continue
            user_profile = _average(user_vectors)
            score = float(np.clip(np.dot(target_profile, user_profile), -1.0, 1.0))
            rows.append(SimilarUserRow(user_id=other_user_id, score=score))

        rows.sort(key=lambda row: row.score, reverse=True)
        return SimilarUsersResponse(user_id=user_id, results=rows[:top_k])
