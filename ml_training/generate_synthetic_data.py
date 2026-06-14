"""
Generate synthetic training data for routing and prevention models.
Run in Google Colab or locally: python ml_training/generate_synthetic_data.py
"""
import numpy as np
import pandas as pd
import os

np.random.seed(42)

# --- Configuration ---
N_ROUTING = 15000
N_PREVENTION = 50000

CATEGORIES = ["electronics", "clothing", "home", "books", "toys"]
CATEGORY_WEIGHTS = [0.25, 0.35, 0.20, 0.10, 0.10]

RETURN_REASONS = ["wrong_size", "defective", "not_as_described", "no_longer_needed", "better_price_found"]
ROUTES = ["resell_as_is", "refurbish", "donate", "recycle", "peer_exchange"]

CONDITION_GRADES = ["like_new", "very_good", "good", "acceptable", "for_parts"]
GRADE_NUMERIC = {"like_new": 4, "very_good": 3, "good": 2, "acceptable": 1, "for_parts": 0}

# Price ranges by category (INR)
PRICE_RANGES = {
    "electronics": (1500, 65000),
    "clothing": (500, 15000),
    "home": (800, 40000),
    "books": (200, 3000),
    "toys": (400, 8000),
}

# Return reason probabilities by category
REASON_PROBS = {
    "electronics": [0.02, 0.35, 0.25, 0.25, 0.13],
    "clothing": [0.40, 0.10, 0.20, 0.20, 0.10],
    "home": [0.05, 0.25, 0.30, 0.25, 0.15],
    "books": [0.02, 0.10, 0.15, 0.50, 0.23],
    "toys": [0.05, 0.20, 0.20, 0.35, 0.20],
}


def determine_optimal_route(category, price, condition_grade, return_reason):
    """Business rules to determine optimal route (labels for training)."""
    grade_num = GRADE_NUMERIC[condition_grade]

    # High condition + decent price → resell
    if grade_num >= 3 and price > 2500:
        base_route = "resell_as_is"
    # Medium condition + worth refurbishing
    elif grade_num >= 1 and price > 1500 and category in ("electronics", "home"):
        base_route = "refurbish"
    # Low price items in good condition → peer exchange
    elif grade_num >= 2 and price <= 2500:
        base_route = "peer_exchange"
    # Very damaged
    elif grade_num == 0:
        base_route = "recycle"
    # Low value items
    elif price < 1200:
        base_route = "donate"
    else:
        base_route = "refurbish"

    # Add noise (10% chance of random route)
    if np.random.random() < 0.10:
        base_route = np.random.choice(ROUTES)

    return base_route


def generate_routing_data():
    """Generate synthetic routing training data."""
    print(f"Generating {N_ROUTING} routing samples...")
    records = []

    for _ in range(N_ROUTING):
        category = np.random.choice(CATEGORIES, p=CATEGORY_WEIGHTS)
        price_min, price_max = PRICE_RANGES[category]
        price = round(np.random.uniform(price_min, price_max), 2)
        age_days = int(np.random.exponential(60)) + 1
        reason = np.random.choice(RETURN_REASONS, p=REASON_PROBS[category])
        condition = np.random.choice(
            CONDITION_GRADES,
            p=[0.15, 0.25, 0.30, 0.20, 0.10],
        )
        route = determine_optimal_route(category, price, condition, reason)

        records.append({
            "product_category": category,
            "original_price": price,
            "product_age_days": age_days,
            "return_reason": reason,
            "condition_grade": condition,
            "optimal_route": route,
        })

    df = pd.DataFrame(records)
    os.makedirs("ml_training/data", exist_ok=True)
    df.to_csv("ml_training/data/routing_training_data.csv", index=False)
    print(f"  Saved to ml_training/data/routing_training_data.csv")
    print(f"  Route distribution:\n{df['optimal_route'].value_counts()}\n")
    return df


def generate_prevention_data():
    """Generate synthetic return prevention training data."""
    print(f"Generating {N_PREVENTION} prevention samples...")
    records = []

    for _ in range(N_PREVENTION):
        # Customer features
        customer_return_rate = np.clip(np.random.beta(2, 8), 0, 1)
        category = np.random.choice(CATEGORIES, p=CATEGORY_WEIGHTS)
        # Category-specific rate (higher variance)
        cat_rate = np.clip(customer_return_rate + np.random.normal(0, 0.1), 0, 1)

        # Product features
        product_return_rate = np.clip(np.random.beta(2, 10), 0, 1)
        if category == "clothing":
            product_return_rate = np.clip(product_return_rate + 0.15, 0, 1)
        size_issue_rate = product_return_rate * 0.6 if category == "clothing" else 0.0
        review_sentiment = np.clip(np.random.normal(0.65, 0.15), 0, 1)
        desc_completeness = np.clip(np.random.normal(0.7, 0.2), 0, 1)

        is_first_in_category = 1 if np.random.random() < 0.2 else 0

        # Determine if returned (target variable)
        # Higher probability based on risk factors
        return_prob = (
            0.3 * customer_return_rate
            + 0.25 * product_return_rate
            + 0.15 * size_issue_rate
            + 0.1 * (1 - review_sentiment)
            + 0.1 * (1 - desc_completeness)
            + 0.05 * is_first_in_category
            + 0.05 * np.random.random()  # noise
        )
        was_returned = 1 if np.random.random() < return_prob else 0

        records.append({
            "customer_return_rate": round(customer_return_rate, 4),
            "customer_category_rate": round(cat_rate, 4),
            "product_return_rate": round(product_return_rate, 4),
            "size_issue_rate": round(size_issue_rate, 4),
            "review_sentiment": round(review_sentiment, 4),
            "description_completeness": round(desc_completeness, 4),
            "category_encoded": CATEGORIES.index(category),
            "is_first_in_category": is_first_in_category,
            "was_returned": was_returned,
        })

    df = pd.DataFrame(records)
    df.to_csv("ml_training/data/prevention_training_data.csv", index=False)
    print(f"  Saved to ml_training/data/prevention_training_data.csv")
    print(f"  Return rate: {df['was_returned'].mean():.2%}\n")
    return df


if __name__ == "__main__":
    print("=" * 50)
    print("Generating Synthetic Training Data")
    print("=" * 50 + "\n")
    generate_routing_data()
    generate_prevention_data()
    print("All data generated successfully!")
