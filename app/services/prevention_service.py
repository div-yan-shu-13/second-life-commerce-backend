import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.aws.dynamodb import put_item, get_item, scan_items
from app.ml.prevention_model import prevention_model, select_interventions


def score_return_risk(
    customer_id: str,
    product_id: str,
    context: str = "browse",
) -> dict:
    """Score return risk for a customer-product pair."""
    # Fetch customer profile from DynamoDB
    customer_profile = get_item("CustomerReturnProfiles", {"customer_id": customer_id})
    if not customer_profile:
        customer_profile = {
            "customer_id": customer_id,
            "total_orders": 5,
            "total_returns": 1,
            "return_rate": 0.15,
            "category_return_rates": {},
        }

    # Fetch product signals from DynamoDB
    product_signals = get_item("ProductReturnSignals", {"product_id": product_id})
    if not product_signals:
        product_signals = {
            "product_id": product_id,
            "category": "electronics",
            "overall_return_rate": 0.12,
            "size_issue_rate": 0.0,
            "avg_review_sentiment": 0.6,
            "description_completeness": 0.7,
        }

    # Run prediction
    prediction = prevention_model.predict(customer_profile, product_signals, context)
    risk_score = prediction["risk_score"]

    # Determine risk bucket
    if risk_score < 0.3:
        risk_bucket = "low"
    elif risk_score < 0.6:
        risk_bucket = "medium"
    else:
        risk_bucket = "high"

    # Select interventions
    interventions = select_interventions(risk_score, prediction["top_risk_factors"])

    # Store prediction in DynamoDB
    prediction_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    prediction_item = {
        "prediction_id": prediction_id,
        "customer_id": customer_id,
        "product_id": product_id,
        "prediction_context": context,
        "risk_score": Decimal(str(round(risk_score, 4))),
        "risk_bucket": risk_bucket,
        "top_risk_factors": prediction["top_risk_factors"],
        "model_version": "xgb_v1" if prevention_model.model else "rule_based_v1",
        "predicted_at": now,
        "created_at": now,
    }
    put_item("ReturnRiskPredictions", prediction_item)

    return {
        "prediction_id": prediction_id,
        "risk_score": risk_score,
        "risk_bucket": risk_bucket,
        "top_risk_factors": prediction["top_risk_factors"],
        "recommended_interventions": interventions,
    }


def get_product_signals(product_id: str) -> dict:
    """Fetch product return signals."""
    signals = get_item("ProductReturnSignals", {"product_id": product_id})
    if not signals:
        return None
    return signals


def get_analytics() -> dict:
    """Get aggregate prevention analytics."""
    try:
        predictions = scan_items("ReturnRiskPredictions")
        total = len(predictions)
        high_risk = sum(1 for p in predictions if p.get("risk_bucket") == "high")

        interventions = scan_items("ReturnInterventions")
        interventions_shown = len(interventions)

        # Estimate returns prevented (simplified: 30% of high-risk interventions)
        estimated_prevented = int(high_risk * 0.3)

        return {
            "total_predictions": total,
            "high_risk_count": high_risk,
            "interventions_shown": interventions_shown,
            "estimated_returns_prevented": estimated_prevented,
        }
    except Exception:
        return {
            "total_predictions": 0,
            "high_risk_count": 0,
            "interventions_shown": 0,
            "estimated_returns_prevented": 0,
        }
