"""
Blockchain Client (Stub)
========================
MongoDB-backed stand-in for the EHRAccessControl smart contract.

Every function mirrors the Solidity contract interface so that
**no route code needs to change** once the real contract is deployed.

Swap this file's internals with Web3.py calls when the blockchain
module is ready.
"""

import uuid
from datetime import datetime, timezone

from backend.database import get_blockchain_col


# ─── File Hash Storage ──────────────────────────────────────────────────

async def store_file_hash(
    file_id: str, file_hash: str, owner_wallet: str
) -> str:
    """
    Store a file's SHA-256 hash (mirrors ``uploadFile`` on-chain).

    Args:
        file_id:      Unique file identifier.
        file_hash:    SHA-256 hex digest of the original file.
        owner_wallet: Wallet address of the uploader (doctor).

    Returns:
        A mock transaction hash string.
    """
    col = get_blockchain_col()

    await col.insert_one({
        "file_id": file_id,
        "file_hash": file_hash,
        "owner": owner_wallet.lower(),
        "access_list": [owner_wallet.lower()],   # owner always has access
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return f"0x{uuid.uuid4().hex}"  # mock tx hash


async def get_file_hash(file_id: str) -> str | None:
    """
    Retrieve a stored file hash (mirrors ``getFileHash`` on-chain).

    Returns:
        The SHA-256 hex string, or None if not found.
    """
    col = get_blockchain_col()
    doc = await col.find_one({"file_id": file_id}, {"file_hash": 1})
    return doc["file_hash"] if doc else None


# ─── Access Control ─────────────────────────────────────────────────────

async def grant_access(
    file_id: str, owner_wallet: str, grantee_wallet: str
) -> str:
    """
    Grant file access to *grantee_wallet* (mirrors ``grantAccess``).

    Args:
        file_id:        Target file.
        owner_wallet:   Must match the recorded owner.
        grantee_wallet: Wallet to grant access to.

    Returns:
        A mock transaction hash.

    Raises:
        PermissionError: If caller is not the owner.
        FileNotFoundError: If file_id not found.
    """
    col = get_blockchain_col()
    doc = await col.find_one({"file_id": file_id})

    if doc is None:
        raise FileNotFoundError(f"File {file_id} not found on chain.")
    if doc["owner"] != owner_wallet.lower():
        raise PermissionError("Only the file owner can grant access.")

    await col.update_one(
        {"file_id": file_id},
        {"$addToSet": {"access_list": grantee_wallet.lower()}},
    )

    return f"0x{uuid.uuid4().hex}"


async def revoke_access(
    file_id: str, owner_wallet: str, grantee_wallet: str
) -> str:
    """
    Revoke file access from *grantee_wallet* (mirrors ``revokeAccess``).

    Returns:
        A mock transaction hash.

    Raises:
        PermissionError: If caller is not the owner.
        FileNotFoundError: If file_id not found.
    """
    col = get_blockchain_col()
    doc = await col.find_one({"file_id": file_id})

    if doc is None:
        raise FileNotFoundError(f"File {file_id} not found on chain.")
    if doc["owner"] != owner_wallet.lower():
        raise PermissionError("Only the file owner can revoke access.")

    await col.update_one(
        {"file_id": file_id},
        {"$pull": {"access_list": grantee_wallet.lower()}},
    )

    return f"0x{uuid.uuid4().hex}"


async def check_access(file_id: str, wallet_address: str) -> bool:
    """
    Check whether *wallet_address* has access (mirrors ``checkAccess``).

    Returns:
        True if access is granted, False otherwise.
    """
    col = get_blockchain_col()
    doc = await col.find_one(
        {
            "file_id": file_id,
            "access_list": wallet_address.lower(),
        }
    )
    return doc is not None


async def log_file_access(file_id: str, wallet_address: str) -> str:
    """
    Record a file-access audit event (mirrors ``logAccess``).

    In the real contract this emits a ``FileAccessed`` event.
    Here we append to an audit array.

    Returns:
        A mock transaction hash.
    """
    col = get_blockchain_col()
    await col.update_one(
        {"file_id": file_id},
        {
            "$push": {
                "audit_log": {
                    "user": wallet_address.lower(),
                    "action": "accessed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            }
        },
    )
    return f"0x{uuid.uuid4().hex}"
