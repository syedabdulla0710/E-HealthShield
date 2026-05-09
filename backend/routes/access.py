"""
Access Routes — Grant / Revoke / Check Access
==============================================
POST /api/grant-access
POST /api/revoke-access
GET  /api/check-access/{file_id}/{wallet_address}

Access control is enforced through the blockchain (stub).
Only the file owner can grant or revoke access.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend import blockchain_client
from backend.database import get_files_col
from backend.logger import log_access, log_error

router = APIRouter()


# ── Request / Response Models ────────────────────────────────────────────

class AccessRequest(BaseModel):
    file_id: str
    owner_wallet: str
    grantee_wallet: str


class AccessResponse(BaseModel):
    message: str
    tx_hash: str


class CheckAccessResponse(BaseModel):
    has_access: bool


# ── Grant Access ─────────────────────────────────────────────────────────

@router.post("/grant-access", response_model=AccessResponse)
async def grant_access(req: AccessRequest):
    """
    Grant file access to another wallet address.

    Only the file owner can perform this action.
    """
    files = get_files_col()
    owner = req.owner_wallet.strip().lower()
    grantee = req.grantee_wallet.strip().lower()

    # Verify file exists in our database
    file_doc = await files.find_one({"file_id": req.file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found.")

    # Verify ownership
    if file_doc["owner_wallet"] != owner:
        raise HTTPException(
            status_code=403, detail="Only the file owner can grant access."
        )

    try:
        tx_hash = await blockchain_client.grant_access(
            req.file_id, owner, grantee
        )

        log_access(owner, req.file_id, f"GRANT to {grantee}")

        return AccessResponse(
            message="Access granted",
            tx_hash=tx_hash,
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log_error("grant_access", e)
        raise HTTPException(status_code=500, detail=f"Grant failed: {e}")


# ── Revoke Access ────────────────────────────────────────────────────────

@router.post("/revoke-access", response_model=AccessResponse)
async def revoke_access(req: AccessRequest):
    """
    Revoke file access from a wallet address.

    Only the file owner can perform this action.
    """
    files = get_files_col()
    owner = req.owner_wallet.strip().lower()
    grantee = req.grantee_wallet.strip().lower()

    file_doc = await files.find_one({"file_id": req.file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found.")

    if file_doc["owner_wallet"] != owner:
        raise HTTPException(
            status_code=403, detail="Only the file owner can revoke access."
        )

    try:
        tx_hash = await blockchain_client.revoke_access(
            req.file_id, owner, grantee
        )

        log_access(owner, req.file_id, f"REVOKE from {grantee}")

        return AccessResponse(
            message="Access revoked",
            tx_hash=tx_hash,
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log_error("revoke_access", e)
        raise HTTPException(status_code=500, detail=f"Revoke failed: {e}")


# ── Check Access ─────────────────────────────────────────────────────────

@router.get(
    "/check-access/{file_id}/{wallet_address}",
    response_model=CheckAccessResponse,
)
async def check_access(file_id: str, wallet_address: str):
    """
    Check whether a wallet address has access to a file.
    """
    wallet = wallet_address.strip().lower()

    try:
        has_access = await blockchain_client.check_access(file_id, wallet)
        log_access(wallet, file_id, "CHECK")
        return CheckAccessResponse(has_access=has_access)

    except Exception as e:
        log_error("check_access", e)
        raise HTTPException(status_code=500, detail=f"Access check failed: {e}")
