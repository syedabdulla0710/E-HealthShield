"""
MongoDB Async Connection
========================
Manages the Motor (async) client lifecycle and provides
collection accessors for the rest of the application.

Usage:
    from database import get_users_col, get_files_col
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from backend.config import settings

# ── Module-level state (initialised during app lifespan) ─────────────────

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


# ── Lifecycle ────────────────────────────────────────────────────────────

async def connect_db() -> None:
    """
    Open the Motor client and create required indexes.

    Called once during FastAPI lifespan startup.
    The server will **not** start if MongoDB is unreachable.
    """
    global _client, _db

    _client = AsyncIOMotorClient(settings.MONGO_URI)
    _db = _client[settings.MONGO_DB_NAME]

    # Ping to verify connectivity — raises on failure, halting startup
    await _client.admin.command("ping")
    print(
        f"[OK] Connected to MongoDB: "
        f"{settings.MONGO_URI}/{settings.MONGO_DB_NAME}"
    )

    # ── Indexes ──────────────────────────────────────────────────────
    users = _db["users"]
    await users.create_index("wallet_address", unique=True)

    files = _db["encrypted_files"]
    await files.create_index("file_id", unique=True)
    await files.create_index("sse_tags")           # array index for search
    await files.create_index("owner_wallet")
    await files.create_index("patient_wallet")

    # Blockchain stub collection
    bc = _db["blockchain_records"]
    await bc.create_index("file_id", unique=True)


async def close_db() -> None:
    """Close the Motor client.  Called during FastAPI lifespan shutdown."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        print("[OK] MongoDB connection closed.")


# ── Collection Accessors ─────────────────────────────────────────────────

def _get_db() -> AsyncIOMotorDatabase:
    """Return the active database handle (raises if not connected)."""
    if _db is None:
        raise RuntimeError(
            "Database not initialised. Did the app lifespan start?"
        )
    return _db


def get_users_col():
    """Return the ``users`` collection."""
    return _get_db()["users"]


def get_files_col():
    """Return the ``encrypted_files`` collection."""
    return _get_db()["encrypted_files"]


def get_blockchain_col():
    """Return the ``blockchain_records`` stub collection."""
    return _get_db()["blockchain_records"]
