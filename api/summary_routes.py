"""AI summary route.

The route accepts the already-computed dashboard metrics instead of a file so
the summary cost is paid only when the user asks for it.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from utils.ai_summary import SummaryUnavailable, generate_summary

router = APIRouter(tags=["ai"])


class SummaryRequest(BaseModel):
    trend: str = Field(default="unknown", max_length=40)
    winner_model: str | None = Field(default=None, max_length=80)
    mae: float | None = None
    total_sales: float | None = None
    alert_count: int = Field(default=0, ge=0)
    top_product: str | None = Field(default=None, max_length=120)
    top_category: str | None = Field(default=None, max_length=120)


class SummaryResponse(BaseModel):
    summary: str
    model: str | None = None


@router.post("/summary", response_model=SummaryResponse)
def create_summary(payload: SummaryRequest) -> SummaryResponse:
    try:
        result = generate_summary(payload.model_dump())
    except SummaryUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return SummaryResponse(summary=result.text, model=result.model)
