"""
Application Configuration
=========================
Loads settings from the .env file via pydantic-settings.

Usage:
    from config import settings
    print(settings.MONGO_URI)
"""

import base64
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All environment variables used by the backend.

    Values are read from ``backend/.env`` and can be overridden by real
    environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── MongoDB ──────────────────────────────────────────────────────────
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "e_healthshield"

    # ── SSE Key ──────────────────────────────────────────────────────────
    SSE_KEY: str = ""  # base64-encoded; decoded in property below

    # ── Blockchain (stub for now) ────────────────────────────────────────
    CONTRACT_ADDRESS: str = ""
    BLOCKCHAIN_RPC_URL: str = "http://127.0.0.1:8545"

    # ── File Upload ──────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 10

    # ── Derived ──────────────────────────────────────────────────────────

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        """Maximum upload file size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def sse_key_bytes(self) -> bytes:
        """
        Return the 32-byte SSE key.

        If the .env value is empty, auto-generate one and print a warning.
        This is acceptable for development but NOT for production.
        """
        if self.SSE_KEY:
            return base64.b64decode(self.SSE_KEY)

        # Auto-generate for first run
        import warnings
        key = os.urandom(32)
        encoded = base64.b64encode(key).decode()
        warnings.warn(
            f"\n⚠️  No SSE_KEY in .env — auto-generated one for this session.\n"
            f"   Add this to backend/.env to persist across restarts:\n"
            f"   SSE_KEY={encoded}\n",
            stacklevel=2,
        )
        return key


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton so .env is read only once."""
    return Settings()


# Convenience alias
settings = get_settings()
