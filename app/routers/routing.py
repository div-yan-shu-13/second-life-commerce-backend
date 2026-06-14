from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.routing_service import decide_route, get_decision, override_decision

router = APIRouter(prefix="/api/v1/routing", tags=["Product Routing"])


class RouteRequest(BaseModel):
    return_id: str
    product_id: str
    return_reason: str
    product_category: str = "electronics"
    original_price: float = 50.0
    product_age_days: int = 30
    condition_grade: Optional[str] = None
    condition_confidence: Optional[float] = None


class OverrideRequest(BaseModel):
    new_route: str
    reason: str


@router.post("/decide")
def route_decide(request: RouteRequest):
    """Determine the optimal disposition route for a returned product."""
    data = request.model_dump()
    result = decide_route(data)
    return result


@router.get("/decisions/{decision_id}")
def route_get_decision(decision_id: str):
    """Fetch a routing decision by ID."""
    decision = get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.post("/decisions/{decision_id}/override")
def route_override(decision_id: str, request: OverrideRequest):
    """Override a routing decision with a new route."""
    result = override_decision(decision_id, request.new_route, request.reason)
    if not result:
        raise HTTPException(status_code=404, detail="Decision not found")
    return result
