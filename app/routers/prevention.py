from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.prevention_service import (
    score_return_risk,
    get_product_signals,
    get_analytics,
)

router = APIRouter(prefix="/api/v1/prevention", tags=["Return Prevention"])


class ScoreRequest(BaseModel):
    customer_id: str
    product_id: str
    context: str = "browse"  # 'browse', 'cart_add', 'checkout'
    selected_variant: Optional[dict] = None


@router.post("/score")
def prevention_score(request: ScoreRequest):
    """
    Score return risk for a customer-product pair.
    Returns risk score, top factors, and recommended interventions.
    """
    result = score_return_risk(
        customer_id=request.customer_id,
        product_id=request.product_id,
        context=request.context,
    )
    return result


@router.get("/product-signals/{product_id}")
def prevention_product_signals(product_id: str):
    """Fetch precomputed return signals for a product."""
    signals = get_product_signals(product_id)
    if not signals:
        raise HTTPException(status_code=404, detail="Product signals not found")
    return signals


@router.get("/analytics")
def prevention_analytics():
    """Get aggregate return prevention analytics."""
    return get_analytics()
