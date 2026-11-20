"""InventoryIQ FastAPI backend entry point.

!! Run with: uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.forecast_routes import router as forecast_router
from api.alert_routes import router as alert_router
from api.analyze_routes import router as analyze_router
from api.summary_routes import router as summary_router

app = FastAPI(
    title="InventoryIQ",
    description="AI-powered retail forecasting engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast_router)
app.include_router(alert_router)
app.include_router(analyze_router)
app.include_router(summary_router)

@app.get("/")
def root():
    return {"status": "ok", "product": "InventoryIQ"}