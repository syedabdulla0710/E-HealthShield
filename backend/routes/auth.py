"""
Auth Route — User Registration
===============================
POST /api/register

Registers a new user (doctor or patient) and generates a
persistent CRYSTALS-Kyber keypair stored in MongoDB.
"""

import base64
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from backend.database import get_users_col
from backend.logger import log_register, log_error

# Import from the crypto module
from crypto import generate_keypair

router = APIRouter()

# ── Request / Response Models ────────────────────────────────────────────

VALID_ROLES = {"doctor", "patient"}


class RegisterRequest(BaseModel):
    wallet_address: str
    role: str

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError(
                "wallet_address must be a 42-character hex string starting with 0x"
            )
        return v.lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_ROLES:
            raise ValueError(f"role must be one of {VALID_ROLES}")
        return v


class RegisterResponse(BaseModel):
    wallet_address: str
    role: str
    kyber_public_key: str
    message: str


# ── Route ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse)
async def register_user(req: RegisterRequest):
    """
    Register a new user and generate a CRYSTALS-Kyber keypair.

    - Validates wallet address format and role.
    - Generates Kyber-768 keypair (called once per user).
    - Stores both keys (base64) in MongoDB (demo prototype).
    - Returns the public key so the frontend can display it.
    """
    users = get_users_col()

    # Check for duplicate registration
    existing = await users.find_one({"wallet_address": req.wallet_address})
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Wallet address already registered.",
        )

    try:
        # Generate persistent Kyber keypair
        public_key, secret_key = generate_keypair()

        pk_b64 = base64.b64encode(public_key).decode()
        sk_b64 = base64.b64encode(secret_key).decode()

        user_doc = {
            "wallet_address": req.wallet_address,
            "role": req.role,
            "kyber_public_key": pk_b64,
            "kyber_secret_key": sk_b64,   # ⚠️ demo only — use HSM in prod
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        await users.insert_one(user_doc)

        log_register(req.wallet_address, req.role)

        return RegisterResponse(
            wallet_address=req.wallet_address,
            role=req.role,
            kyber_public_key=pk_b64,
            message="User registered successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error("register_user", e)
        raise HTTPException(status_code=500, detail=f"Registration failed: {e}")
