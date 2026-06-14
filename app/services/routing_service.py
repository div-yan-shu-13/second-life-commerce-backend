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
    price = float(data.get("original_price", 50.0))
    category = data.get("product_category", "electronics").lower()
    route = prediction["route"]

    recovery_estimates = {
        "resell_as_is": price * 0.75,
        "refurbish": price * 0.55,
        "peer_exchange": price * 0.60,
        "donate": 0.0,
        "recycle": price * 0.05,
    }
    cost_estimates = {
        "resell_as_is": 5.0,
        "refurbish": REFURB_COST.get(category, 20.0),
        "peer_exchange": 3.0,
        "donate": 2.0,
        "recycle": 1.0,
    }

    estimated_recovery = recovery_estimates.get(route, 0.0)
    estimated_cost = cost_estimates.get(route, 5.0)

    decision_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    decision = {
        "decision_id": decision_id,
        "return_id": data.get("return_id", str(uuid.uuid4())),
        "route": route,
        "confidence_score": Decimal(str(round(prediction["confidence"], 4))),
        "model_version": "lgbm_v1" if routing_model.model else "rule_based_v1",
        "reasoning": prediction["reasoning"],
        "estimated_recovery": Decimal(str(round(estimated_recovery, 2))),
        "estimated_cost": Decimal(str(round(estimated_cost, 2))),
        "decided_at": now,
        "outcome_status": "pending",
        "created_at": now,
    }

    put_item("RoutingDecisions", decision)

    return {
        "decision_id": decision_id,
        "route": route,
        "confidence": prediction["confidence"],
        "estimated_recovery_usd": round(estimated_recovery, 2),
        "estimated_cost_usd": round(estimated_cost, 2),
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
