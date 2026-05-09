"""
Decrypt Route — File Decryption & Download
==========================================
POST /api/decrypt/{file_id}

1. Verify the requester has access (blockchain check).
2. Fetch encrypted data from MongoDB.
3. Kyber decapsulate → recover shared secret.
4. AES-256-GCM decrypt → recover original file.
5. Integrity check: SHA-256(decrypted) == stored hash.
6. Return the file as a streaming download.
"""

import base64

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend import blockchain_client
from backend.database import get_users_col, get_files_col
from backend.logger import log_decrypt, log_error

from crypto import decrypt_file, decapsulate, compute_file_hash

router = APIRouter()


# ── Request Model ────────────────────────────────────────────────────────

class DecryptRequest(BaseModel):
    wallet_address: str


# ── Route ────────────────────────────────────────────────────────────────

@router.post("/decrypt/{file_id}")
async def decrypt_ehr_file(file_id: str, req: DecryptRequest):
    """
    Decrypt and return an encrypted EHR file.

    Access is verified through the blockchain (stub) before decryption.
    After decryption, the file hash is verified against the stored
    blockchain hash to detect tampering.
    """
    users = get_users_col()
    files = get_files_col()

    wallet = req.wallet_address.strip().lower()

    # ── 1. Find the encrypted file ───────────────────────────────────
    file_doc = await files.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found.")

    # ── 2. Check access via blockchain ───────────────────────────────
    has_access = await blockchain_client.check_access(file_id, wallet)
    if not has_access:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You do not have permission to decrypt this file.",
        )

    try:
        # ── 3. Fetch the patient's Kyber secret key ──────────────────
        patient_wallet = file_doc["patient_wallet"]
        patient = await users.find_one({"wallet_address": patient_wallet})
        if not patient:
            raise HTTPException(
                status_code=500,
                detail="Patient record not found — cannot recover decryption key.",
            )

        secret_key = base64.b64decode(patient["kyber_secret_key"])

        # ── 4. Kyber decapsulate → shared secret ─────────────────────
        kyber_ct = base64.b64decode(file_doc["kyber_ciphertext"])
        shared_secret = decapsulate(kyber_ct, secret_key)

        # ── 5. AES-256-GCM decrypt ──────────────────────────────────
        ciphertext = base64.b64decode(file_doc["encrypted_data"])
        nonce = base64.b64decode(file_doc["aes_nonce"])
        tag = base64.b64decode(file_doc["aes_tag"])

        plaintext = decrypt_file(ciphertext, shared_secret, nonce, tag)

        # ── 6. Integrity verification ────────────────────────────────
        decrypted_hash = compute_file_hash(plaintext)
        stored_hash = file_doc["file_hash"]

        # Also verify against blockchain hash
        chain_hash = await blockchain_client.get_file_hash(file_id)

        if decrypted_hash != stored_hash:
            raise HTTPException(
                status_code=500,
                detail="Integrity check failed: file hash mismatch (DB).",
            )

        if chain_hash and decrypted_hash != chain_hash:
            raise HTTPException(
                status_code=500,
                detail="Integrity check failed: file hash mismatch (blockchain).",
            )

        # ── 7. Log the access event ──────────────────────────────────
        await blockchain_client.log_file_access(file_id, wallet)
        log_decrypt(wallet, file_id, file_doc["filename"])

        # ── 8. Return the file ───────────────────────────────────────
        # Determine a safe content type
        filename = file_doc["filename"]
        media_type = _guess_media_type(filename)

        return Response(
            content=plaintext,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-File-Hash": decrypted_hash,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error("decrypt_file", e)
        raise HTTPException(status_code=500, detail=f"Decryption failed: {e}")


# ── Helpers ──────────────────────────────────────────────────────────────

def _guess_media_type(filename: str) -> str:
    """Return a reasonable MIME type based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    _TYPES = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "csv": "text/csv",
        "json": "application/json",
        "xml": "application/xml",
        "html": "text/html",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    return _TYPES.get(ext, "application/octet-stream")
