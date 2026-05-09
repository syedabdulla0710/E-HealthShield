"""
Search Route — SSE Keyword Search
==================================
POST /api/search

Searches encrypted files by keyword using Symmetric Searchable
Encryption (SSE).  The keyword is converted to a trapdoor (HMAC tag)
and matched against stored SSE tags — no decryption needed.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.database import get_users_col, get_files_col
from backend.logger import log_search, log_error

from crypto import generate_trapdoor

router = APIRouter()


# ── Request / Response Models ────────────────────────────────────────────

class SearchRequest(BaseModel):
    keyword: str
    wallet_address: str


class FileResult(BaseModel):
    file_id: str
    filename: str
    owner_wallet: str
    uploaded_at: str


class SearchResponse(BaseModel):
    results: list[FileResult]
    count: int


# ── Route ────────────────────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
async def search_files(req: SearchRequest):
    """
    Search encrypted files by keyword without decryption.

    Generates an HMAC trapdoor from the keyword and matches it
    against stored SSE tags in MongoDB.
    """
    users = get_users_col()
    files = get_files_col()

    keyword = req.keyword.strip().lower()
    wallet = req.wallet_address.strip().lower()

    # ── Validate ─────────────────────────────────────────────────────
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword must not be empty.")

    user = await users.find_one({"wallet_address": wallet})
    if not user:
        raise HTTPException(status_code=403, detail="User not registered.")

    try:
        # ── Generate trapdoor ────────────────────────────────────────
        sse_key = settings.sse_key_bytes
        trapdoor = generate_trapdoor(sse_key, keyword)

        # ── Query: find files whose sse_tags array contains the trapdoor
        cursor = files.find(
            {"sse_tags": trapdoor},
            {
                "file_id": 1,
                "filename": 1,
                "owner_wallet": 1,
                "patient_wallet": 1,
                "uploaded_at": 1,
                "_id": 0,
            },
        )

        results: list[FileResult] = []
        async for doc in cursor:
            # Only return files the user is associated with
            # (owner, patient, or has been granted access)
            if doc.get("owner_wallet") == wallet or doc.get("patient_wallet") == wallet:
                results.append(
                    FileResult(
                        file_id=doc["file_id"],
                        filename=doc["filename"],
                        owner_wallet=doc["owner_wallet"],
                        uploaded_at=doc["uploaded_at"],
                    )
                )

        log_search(wallet, keyword, len(results))

        return SearchResponse(results=results, count=len(results))

    except HTTPException:
        raise
    except Exception as e:
        log_error("search_files", e)
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
