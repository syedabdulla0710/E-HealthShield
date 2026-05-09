"""
Upload Route — EHR File Encryption & Storage
=============================================
POST /api/upload  (multipart/form-data)

1. Validate uploader is a registered doctor.
2. Extract keywords from the file + optional manual keywords.
3. Generate SSE tags for keyword search.
4. Encapsulate with patient's Kyber public key → shared secret.
5. AES-256-GCM encrypt the file with the shared secret.
6. Compute SHA-256 hash of the original file.
7. Store everything in MongoDB + record hash on "blockchain".
"""

import base64
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.config import settings
from backend.database import get_users_col, get_files_col
from backend import blockchain_client
from backend.logger import log_upload, log_error

from crypto import (
    encrypt_file,
    encapsulate,
    extract_keywords,
    generate_tags,
    compute_file_hash,
)

router = APIRouter()


# ── Response Model ───────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    file_id: str
    file_hash: str
    sse_tags_count: int
    message: str


# ── Route ────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    wallet_address: str = Form(...),
    patient_wallet: str = Form(...),
    keywords: str = Form(""),
):
    """
    Upload, encrypt, and store an EHR file.

    The uploader must be a registered doctor. The file is encrypted
    for the specified patient using their Kyber public key.
    """
    users = get_users_col()
    files = get_files_col()

    # ── 1. Normalise wallet addresses ────────────────────────────────
    wallet_address = wallet_address.strip().lower()
    patient_wallet = patient_wallet.strip().lower()

    # ── 2. Validate uploader is a doctor ─────────────────────────────
    uploader = await users.find_one({"wallet_address": wallet_address})
    if not uploader:
        raise HTTPException(status_code=403, detail="Uploader not registered.")
    if uploader["role"] != "doctor":
        raise HTTPException(
            status_code=403, detail="Only doctors can upload files."
        )

    # ── 3. Validate patient exists ───────────────────────────────────
    patient = await users.find_one({"wallet_address": patient_wallet})
    if not patient:
        raise HTTPException(
            status_code=404, detail="Patient wallet not registered."
        )

    # ── 4. Read and validate file size ───────────────────────────────
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(file_bytes) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB} MB.",
        )

    filename = file.filename or "unnamed_file"

    try:
        # ── 5. Extract keywords + merge manual keywords ──────────────
        auto_keywords = extract_keywords(file_bytes, filename)
        manual = [
            kw.strip().lower()
            for kw in keywords.split(",")
            if kw.strip()
        ]
        all_keywords = sorted(set(auto_keywords + manual))

        # ── 6. Generate SSE tags ─────────────────────────────────────
        sse_key = settings.sse_key_bytes
        sse_tags = generate_tags(sse_key, all_keywords)

        # ── 7. Kyber encapsulate (patient's public key) ──────────────
        patient_pk = base64.b64decode(patient["kyber_public_key"])
        kyber_ct, shared_secret = encapsulate(patient_pk)

        # ── 8. AES-256-GCM encrypt ──────────────────────────────────
        aes_result = encrypt_file(file_bytes, shared_secret)

        # ── 9. Compute file hash ─────────────────────────────────────
        file_hash = compute_file_hash(file_bytes)

        # ── 10. Generate file ID ─────────────────────────────────────
        file_id = str(uuid.uuid4())

        # ── 11. Store in MongoDB ─────────────────────────────────────
        file_doc = {
            "file_id": file_id,
            "filename": filename,
            "owner_wallet": wallet_address,
            "patient_wallet": patient_wallet,
            "encrypted_data": base64.b64encode(aes_result["ciphertext"]).decode(),
            "aes_nonce": base64.b64encode(aes_result["nonce"]).decode(),
            "aes_tag": base64.b64encode(aes_result["tag"]).decode(),
            "kyber_ciphertext": base64.b64encode(kyber_ct).decode(),
            "sse_tags": sse_tags,
            "file_hash": file_hash,
            "file_size": len(file_bytes),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        await files.insert_one(file_doc)

        # ── 12. Record hash on blockchain + grant access ─────────────
        await blockchain_client.store_file_hash(
            file_id, file_hash, wallet_address
        )
        # Auto-grant access to the patient
        await blockchain_client.grant_access(
            file_id, wallet_address, patient_wallet
        )

        # ── 13. Log the event ────────────────────────────────────────
        log_upload(
            wallet_address, file_id, filename, file_hash, len(sse_tags)
        )

        return UploadResponse(
            file_id=file_id,
            file_hash=file_hash,
            sse_tags_count=len(sse_tags),
            message="File uploaded and encrypted successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error("upload_file", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")
