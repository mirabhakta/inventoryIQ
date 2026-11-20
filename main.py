"""InventoryIQ FastAPI backend entry point.

Run with: uvicorn main:app --reload
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.alert_routes import router as alert_router
from api.analyze_routes import router as analyze_router
from api.forecast_routes import router as forecast_router
from api.summary_routes import router as summary_router

load_dotenv()

DEFAULT_ALLOWED_ORIGINS = ["http://localhost:5173"]


def get_allowed_origins() -> list[str]:
    """Read the comma-separated CORS allowlist, stripping trailing slashes."""
    raw = os.getenv("ALLOWED_ORIGINS", ",".join(DEFAULT_ALLOWED_ORIGINS))
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    return origins or list(DEFAULT_ALLOWED_ORIGINS)


app = FastAPI(
    title="InventoryIQ",
    description="AI-powered retail forecasting engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(forecast_router)
app.include_router(alert_router)
app.include_router(analyze_router)
app.include_router(summary_router)


@app.get("/")
def root():
    return {"status": "ok", "product": "InventoryIQ"}


@app.get("/health")
def health():
    """Liveness/readiness probe used by the hosting platform."""
    return {
        "status": "ok",
        "service": "inventoryiq",
        "version": app.version,
        "ai_configured": bool(os.getenv("GEMINI_API_KEY")),
    }
