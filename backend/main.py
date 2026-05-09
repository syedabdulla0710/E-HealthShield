"""
E-HealthShield — FastAPI Backend
=================================
Entry point for the backend API server.

Run:
    uvicorn backend.main:app --reload --port 8000
From:
    E-HealthShield/  (project root)

API docs available at:
    http://localhost:8000/docs       (Swagger UI)
    http://localhost:8000/redoc      (ReDoc)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import connect_db, close_db
from backend.routes.auth import router as auth_router
from backend.routes.upload import router as upload_router
from backend.routes.search import router as search_router
from backend.routes.access import router as access_router
from backend.routes.decrypt import router as decrypt_router


# ── Lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup / shutdown resources."""
    # Startup
    await connect_db()
    print("[OK] E-HealthShield backend is ready!")
    yield
    # Shutdown
    await close_db()


# ── App ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="E-HealthShield API",
    description=(
        "Quantum-secure, blockchain-auditable API for "
        "Electronic Health Record management."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Fallback React dev
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routes ─────────────────────────────────────────────────────

app.include_router(auth_router, prefix="/api", tags=["Auth"])
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(search_router, prefix="/api", tags=["Search"])
app.include_router(access_router, prefix="/api", tags=["Access Control"])
app.include_router(decrypt_router, prefix="/api", tags=["Decrypt"])


# ── Health Check ─────────────────────────────────────────────────────────

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Simple health-check endpoint."""
    return {"status": "healthy", "service": "E-HealthShield API"}
