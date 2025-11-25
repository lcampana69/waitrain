"""Application configuration loading."""
from __future__ import annotations

import os
import pathlib
import tomllib
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Configuration for the application."""

    dsn: str
    schema_cache_path: pathlib.Path
    system_prompt: str
    llm_model: str
    llm_api_key: str

    @classmethod
    def from_toml(cls, path: pathlib.Path) -> "Settings":
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with path.open("rb") as fh:
            data = tomllib.load(fh)

        db = data.get("database", {})
        prompts = data.get("prompts", {})
        llm = data.get("llm", {})

        cache_path = pathlib.Path(db.get("schema_cache_path", "data/schema_cache.json"))
        if not cache_path.is_absolute():
            cache_path = path.parent / cache_path
        cache_path = cache_path.resolve()

        dsn = db.get("dsn", "")
        if not dsn:
            raise ValueError(f"Database DSN is required in config file: {path}")

        api_key_env = llm.get("api_key_env", "OPENAI_API_KEY")
        api_key = os.environ.get(api_key_env, "")
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. Set "
                f"{api_key_env}=<tu_api_key> antes de arrancar la aplicación."
            )

        return cls(
            dsn=dsn,
            schema_cache_path=cache_path,
            system_prompt=prompts.get(
                "system",
                "Responder preguntas sobre la base de datos usando el esquema proporcionado.",
            ),
            llm_model=llm.get("model", "gpt-4o-mini"),
            llm_api_key=api_key,
        )


def load_settings(config_path: Optional[str] = None) -> Settings:
    """Load settings from a TOML configuration file.

    Resolution order (first existing wins):
    1. Explicit ``config_path`` argument
    2. ``WAITRAIN_CONFIG`` environment variable
    3. Default ``config/database.toml`` relative to the project root
    """

    resolved_path: Optional[pathlib.Path] = None

    if config_path:
        candidate = pathlib.Path(config_path)
        if not candidate.exists():
            raise FileNotFoundError(f"Config path does not exist: {candidate}")
        resolved_path = candidate

    if resolved_path is None:
        env_path = os.environ.get("WAITRAIN_CONFIG")
        if env_path:
            candidate = pathlib.Path(env_path)
            if not candidate.exists():
                raise FileNotFoundError(f"WAITRAIN_CONFIG points to a missing file: {candidate}")
            resolved_path = candidate

    if resolved_path is None:
        resolved_path = pathlib.Path(__file__).resolve().parent.parent / "config" / "database.toml"

    return Settings.from_toml(resolved_path)
