import os
import numpy as np
import joblib
from app.config import settings

# Route labels
ROUTE_LABELS = ["resell_as_is", "refurbish", "donate", "recycle", "peer_exchange"]

# Category encoding
CATEGORY_MAP = {"electronics": 0, "clothing": 1, "home": 2, "books": 3, "toys": 4}

# Return reason encoding
REASON_MAP = {
    "wrong_size": 0,
    "defective": 1,
    "not_as_described": 2,
    "no_longer_needed": 3,
    "better_price_found": 4,
}

# Condition grade encoding
GRADE_MAP = {"like_new": 4, "very_good": 3, "good": 2, "acceptable": 1, "for_parts": 0}


# Category average return rates (precomputed lookup)
CATEGORY_RETURN_RATES = {
    "electronics": 0.15,
    "clothing": 0.30,
    "home": 0.12,
    "books": 0.05,
    "toys": 0.10,
}

# Refurbishment cost estimates by category (USD)
REFURB_COST = {
    "electronics": 45.0,
    "clothing": 8.0,
    "home": 20.0,
    "books": 3.0,
    "toys": 10.0,
}


class RoutingModel:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        model_path = os.path.join(settings.MODEL_PATH, "routing_lgbm.pkl")
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            self.model = None  # Will use rule-based fallback

    def engineer_features(self, data: dict) -> np.ndarray:
        """Transform API input into model feature vector."""
        category = data.get("product_category", "electronics").lower()
        reason = data.get("return_reason", "no_longer_needed").lower()
        condition = data.get("condition_grade", "good").lower()
        price = float(data.get("original_price", 50.0))
        age_days = int(data.get("product_age_days", 30))

        category_encoded = CATEGORY_MAP.get(category, 0)
        reason_encoded = REASON_MAP.get(reason, 3)
        condition_encoded = GRADE_MAP.get(condition, 2)
        category_return_rate = CATEGORY_RETURN_RATES.get(category, 0.15)
        refurb_cost = REFURB_COST.get(category, 20.0)

        # Estimated resale value: price * condition factor
        condition_factor = {4: 0.85, 3: 0.70, 2: 0.55, 1: 0.35, 0: 0.10}
        resale_estimate = price * condition_factor.get(condition_encoded, 0.5)

        features = np.array([[
            category_encoded,
            price,
            age_days,
            reason_encoded,
            condition_encoded,
            category_return_rate,
            resale_estimate,
            refurb_cost,
        ]])
        return features

    def _rule_based_fallback(self, data: dict) -> dict:
        """Rule-based routing when ML model is not available."""
        condition = data.get("condition_grade", "good").lower()
        price = float(data.get("original_price", 50.0))
        reason = data.get("return_reason", "no_longer_needed").lower()

        if condition in ("like_new", "very_good") and price > 30:
            route = "resell_as_is"
            confidence = 0.85
        elif condition == "good" and reason != "defective":
            route = "refurbish"
            confidence = 0.70
        elif condition == "acceptable" and price > 20:
            route = "refurbish"
            confidence = 0.60
        elif condition == "for_parts" or (condition == "acceptable" and price < 10):
            route = "recycle"
            confidence = 0.75
        elif price < 15:
            route = "donate"
            confidence = 0.65
        else:
            route = "peer_exchange"
            confidence = 0.55

        return {
            "route": route,
            "confidence": confidence,
            "reasoning": {"method": "rule_based", "top_factors": []},
        }

    def predict(self, data: dict) -> dict:
        """Predict optimal route for a returned product."""
        if self.model is None:
            return self._rule_based_fallback(data)

        features = self.engineer_features(data)
        probabilities = self.model.predict_proba(features)[0]
        predicted_class = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_class])
        route = ROUTE_LABELS[predicted_class]

        # Feature importance for explainability
        feature_names = [
            "category", "price", "age_days", "return_reason",
            "condition_grade", "category_return_rate",
            "resale_estimate", "refurb_cost",
        ]
        importances = self.model.feature_importances_
        top_factors = sorted(
            zip(feature_names, importances.tolist()),
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        return {
            "route": route,
            "confidence": confidence,
            "reasoning": {
                "method": "ml_model",
                "top_factors": [
                    {"feature": f, "importance": round(imp, 4)}
                    for f, imp in top_factors
                ],
            },
        }


# Singleton instance
routing_model = RoutingModel()
