import os
import numpy as np
import joblib
from app.config import settings

CATEGORY_MAP = {"electronics": 0, "clothing": 1, "home": 2, "books": 3, "toys": 4}


class PreventionModel:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        model_path = os.path.join(settings.MODEL_PATH, "prevention_xgb.pkl")
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            self.model = None  # Will use rule-based fallback

    def engineer_features(
        self,
        customer_profile: dict,
        product_signals: dict,
        context: str,
    ) -> np.ndarray:
        """Transform customer + product data into model feature vector."""
        customer_return_rate = float(customer_profile.get("return_rate", 0.1))
        category = product_signals.get("category", "electronics").lower()
        cat_return_rates = customer_profile.get("category_return_rates", {})
        customer_cat_rate = float(cat_return_rates.get(category, customer_return_rate))

        product_return_rate = float(product_signals.get("overall_return_rate", 0.1))
        size_issue_rate = float(product_signals.get("size_issue_rate", 0.0))
        review_sentiment = float(product_signals.get("avg_review_sentiment", 0.5))
        desc_completeness = float(product_signals.get("description_completeness", 0.7))
        category_encoded = CATEGORY_MAP.get(category, 0)

        total_orders = int(customer_profile.get("total_orders", 1))
        is_first_in_category = 1 if total_orders < 3 else 0

        features = np.array([[
            customer_return_rate,
            customer_cat_rate,
            product_return_rate,
            size_issue_rate,
            review_sentiment,
            desc_completeness,
            category_encoded,
            is_first_in_category,
        ]])
        return features

    def _rule_based_fallback(
        self, customer_profile: dict, product_signals: dict
    ) -> dict:
        """Rule-based risk scoring when ML model is not available."""
        customer_rate = float(customer_profile.get("return_rate", 0.1))
        product_rate = float(product_signals.get("overall_return_rate", 0.1))

        # Simple weighted average
        risk_score = 0.4 * customer_rate + 0.4 * product_rate + 0.2 * 0.15
        risk_score = min(max(risk_score, 0.0), 1.0)

        factors = []
        if customer_rate > 0.3:
            factors.append({
                "factor": "customer_return_rate",
                "contribution": round(customer_rate * 0.4, 3),
                "detail": f"Customer has a {customer_rate:.0%} return rate",
            })
        if product_rate > 0.2:
            factors.append({
                "factor": "product_return_rate",
                "contribution": round(product_rate * 0.4, 3),
                "detail": f"Product has a {product_rate:.0%} return rate",
            })

        return {
            "risk_score": round(risk_score, 4),
            "top_risk_factors": factors,
            "method": "rule_based",
        }

    def predict(
        self,
        customer_profile: dict,
        product_signals: dict,
        context: str = "browse",
    ) -> dict:
        """Predict return risk for a customer-product pair."""
        if self.model is None:
            return self._rule_based_fallback(customer_profile, product_signals)

        features = self.engineer_features(customer_profile, product_signals, context)
        risk_score = float(self.model.predict_proba(features)[0][1])

        # Feature contributions (approximated from model feature importances)
        feature_names = [
            "customer_return_rate", "customer_category_rate",
            "product_return_rate", "size_issue_rate",
            "review_sentiment", "description_completeness",
            "category", "is_first_in_category",
        ]
        importances = self.model.feature_importances_
        feature_values = features[0]

        factors = []
        for name, imp, val in sorted(
            zip(feature_names, importances, feature_values),
            key=lambda x: x[1],
            reverse=True,
        )[:3]:
            factors.append({
                "factor": name,
                "contribution": round(float(imp), 4),
                "detail": f"{name} = {val:.3f}",
            })

        return {
            "risk_score": round(risk_score, 4),
            "top_risk_factors": factors,
            "method": "ml_model",
        }


def select_interventions(risk_score: float, risk_factors: list) -> list:
    """Rule-based intervention selection based on risk factors."""
    if risk_score < 0.3:
        return []

    interventions = []
    factor_names = [f["factor"] for f in risk_factors]

    if "size_issue_rate" in factor_names:
        interventions.append({
            "type": "size_recommendation",
            "priority": 1,
            "message": "Customers similar to you found this item runs small. Consider sizing up.",
        })
    if "description_completeness" in factor_names:
        interventions.append({
            "type": "info_enrichment",
            "priority": 2,
            "message": "Here are key details other buyers wanted to know before purchasing.",
        })
    if "product_return_rate" in factor_names:
        interventions.append({
            "type": "review_highlight",
            "priority": 2,
            "message": "See what verified buyers say about this product's quality.",
        })
    if "customer_return_rate" in factor_names or "customer_category_rate" in factor_names:
        interventions.append({
            "type": "return_rate_warning",
            "priority": 3,
            "message": f"Heads up: {int(risk_score * 100)}% of similar purchases are returned.",
        })

    if not interventions:
        interventions.append({
            "type": "comparison_nudge",
            "priority": 3,
            "message": "Compare similar products to make sure this is the right fit.",
        })

    return sorted(interventions, key=lambda x: x["priority"])


# Singleton instance
prevention_model = PreventionModel()
