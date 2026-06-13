"""Central config object loaded from environment + .env.

Every module imports `settings` from here. No env-var reads scattered around.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Neo4j Aura ──────────────────────────────────────────
    neo4j_uri: str
    neo4j_user: str = "neo4j"
    neo4j_password: str
    neo4j_database: str = "neo4j"

    # ── Groq (custom-agent LLM) ─────────────────────────────
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # ── HuggingFace / embeddings ────────────────────────────
    hf_token: str | None = None
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Aura Agent platform provider (one of two) ───────────
    openai_api_key: str | None = None
    google_application_credentials: str | None = None
    gcp_project_id: str | None = None
    gcp_location: str = "us-central1"

    # ── App ─────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    data_dir: Path = Field(default=Path("./data"))

    # ── Derived paths ───────────────────────────────────────
    @property
    def raw_dir(self) -> Path:
        d = self.data_dir / "raw"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def processed_dir(self) -> Path:
        d = self.data_dir / "processed"
        d.mkdir(parents=True, exist_ok=True)
        return d


# Singleton — import this everywhere.
settings = Settings()  # type: ignore[call-arg]
