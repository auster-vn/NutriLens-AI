from collections import Counter
from hashlib import blake2b
from math import log1p, sqrt
from typing import Protocol

from app.rag.text import tokenize


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FeatureHashEmbedding:
    def __init__(self, dimensions: int = 256) -> None:
        if dimensions < 32:
            raise ValueError("dimensions must be at least 32")
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return f"feature-hash-v3-{self._dimensions}d"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        tokens = tokenize(text, remove_stop_words=True, expand_aliases=True)
        features = tokens + [f"{left}::{right}" for left, right in zip(tokens, tokens[1:], strict=False)]
        counts = Counter(features)
        vector = [0.0] * self._dimensions
        for feature, count in counts.items():
            digest = blake2b(feature.encode(), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign * log1p(count)
        norm = sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


class SentenceTransformerEmbedding:
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional adapter
            raise RuntimeError(
                "SentenceTransformerEmbedding requires the optional 'sentence-transformers' package."
            ) from exc
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)

    @property
    def model_name(self) -> str:
        return f"sentence-transformers:{self._model_name}"

    @property
    def dimensions(self) -> int:
        return int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


def create_embedding_provider(
    *,
    provider: str,
    dimensions: int,
    sentence_transformer_model: str,
) -> EmbeddingProvider:
    if provider == "feature_hash":
        return FeatureHashEmbedding(dimensions)
    if provider == "sentence_transformers":
        return SentenceTransformerEmbedding(sentence_transformer_model)
    raise ValueError(f"Unsupported RAG embedding provider: {provider}")


def cosine_similarity(left: tuple[float, ...] | list[float], right: tuple[float, ...] | list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))
