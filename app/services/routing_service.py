import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.aws.dynamodb import put_item, get_item, get_table
from app.ml.routing_model import routing_model, REFURB_COST


def decide_route(data: dict) -> dict:
    """Run routing prediction and store decision in DynamoDB."""
    # Run ML prediction
    prediction = routing_model.predict(data)

    # Estimate recovery and cost
    price = float(data.get("original_price", 4000.0))
    category = data.get("product_category", "electronics").lower()
    route = prediction["route"]

    recovery_estimates = {
        "resell_as_is": 75.0,
        "refurbish": 55.0,
        "peer_exchange": 60.0,
        "donate": 0.0,
        "recycle": 5.0,
    }
    cost_estimates = {
        "resell_as_is": 1.0,
        "refurbish": (REFURB_COST.get(category, 1500.0) / price) * 100 if price > 0 else 5.0,
        "peer_exchange": 0.5,
        "donate": 0.3,
        "recycle": 0.2,
    }

    estimated_recovery_pct = recovery_estimates.get(route, 0.0)
    estimated_cost_pct = round(cost_estimates.get(route, 1.0), 2)

    decision_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    decision = {
        "decision_id": decision_id,
        "return_id": data.get("return_id", str(uuid.uuid4())),
        "route": route,
        "confidence_score": Decimal(str(round(prediction["confidence"], 4))),
        "model_version": "lgbm_v1" if routing_model.model else "rule_based_v1",
        "reasoning": prediction["reasoning"],
        "estimated_recovery": Decimal(str(round(estimated_recovery_pct, 2))),
        "estimated_cost": Decimal(str(round(estimated_cost_pct, 2))),
        "decided_at": now,
        "outcome_status": "pending",
        "created_at": now,
    }

    put_item("RoutingDecisions", decision)

    return {
        "decision_id": decision_id,
        "route": route,
        "confidence": prediction["confidence"],
        "estimated_recovery_pct": round(estimated_recovery_pct, 2),
        "estimated_cost_pct": round(estimated_cost_pct, 2),
        "reasoning": prediction["reasoning"],
        "requires_human_review": prediction["confidence"] < 0.6,
    }


def get_decision(decision_id: str) -> dict:
    """Fetch a routing decision by ID."""
    item = get_item("RoutingDecisions", {"decision_id": decision_id})
    if not item:
        return None
    return item


def override_decision(decision_id: str, new_route: str, reason: str) -> dict:
    """Override a routing decision."""
    item = get_item("RoutingDecisions", {"decision_id": decision_id})
    if not item:
        return None

    original_route = item["route"]
    now = datetime.now(timezone.utc).isoformat()

    table = get_table("RoutingDecisions")
    table.update_item(
        Key={"decision_id": decision_id},
        UpdateExpression="SET #r = :route, override_reason = :reason, outcome_status = :status",
        ExpressionAttributeNames={"#r": "route"},
        ExpressionAttributeValues={
            ":route": new_route,
            ":reason": reason,
            ":status": "overridden",
        },
    )

    return {
        "decision_id": decision_id,
        "original_route": original_route,
        "new_route": new_route,
        "status": "overridden",
    }
