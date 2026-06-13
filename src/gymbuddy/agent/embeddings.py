"""MiniLM embedding singleton for the Similarity Search tool.

Lazily loads the model on first use so importing this module is cheap and works
in environments where sentence-transformers isn't installed yet.
"""
from __future__ import annotations

from functools import lru_cache

from gymbuddy.config import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # lazy import

        _model = SentenceTransformer(settings.embedding_model)
    return _model


@lru_cache(maxsize=512)
def embed(text: str) -> tuple[float, ...]:
    """Return a normalized 384-d embedding as a hashable tuple (cached)."""
    vec = _get_model().encode(text, normalize_embeddings=True)
    return tuple(float(x) for x in vec)


def embed_list(text: str) -> list[float]:
    """Same as embed() but returns a plain list (what the Neo4j driver wants)."""
    return list(embed(text))
