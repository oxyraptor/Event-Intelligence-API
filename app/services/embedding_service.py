from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

import numpy as np


class EmbeddingService:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
        except Exception:
            self._model = None

    def _fallback_embed(self, text: str) -> list[float]:
        dimension = 384
        vector = [0.0] * dimension
        tokens = text.lower().split()
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % dimension
            weight = 1.0 + (int.from_bytes(digest[4:8], "little") % 1000) / 1000.0
            vector[index] += weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if self._model is None:
            return [self._fallback_embed(text) for text in texts]

        embeddings = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(embeddings, dtype=float).tolist()

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
