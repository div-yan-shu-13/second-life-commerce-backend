"""
Train LightGBM routing model.
Run: python ml_training/train_routing_model.py
"""
import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import lightgbm as lgb

# Load data
DATA_PATH = "ml_training/data/routing_training_data.csv"
OUTPUT_PATH = "trained_models/routing_lgbm.pkl"

if not os.path.exists(DATA_PATH):
    print("Training data not found. Run generate_synthetic_data.py first.")
    exit(1)

df = pd.read_csv(DATA_PATH)
print(f"Loaded {len(df)} samples\n")

# Encode features
CATEGORY_MAP = {"electronics": 0, "clothing": 1, "home": 2, "books": 3, "toys": 4}
REASON_MAP = {"wrong_size": 0, "defective": 1, "not_as_described": 2, "no_longer_needed": 3, "better_price_found": 4}
GRADE_MAP = {"like_new": 4, "very_good": 3, "good": 2, "acceptable": 1, "for_parts": 0}
ROUTE_MAP = {"resell_as_is": 0, "refurbish": 1, "donate": 2, "recycle": 3, "peer_exchange": 4}

CATEGORY_RETURN_RATES = {"electronics": 0.15, "clothing": 0.30, "home": 0.12, "books": 0.05, "toys": 0.10}
REFURB_COST = {"electronics": 3500.0, "clothing": 600.0, "home": 1500.0, "books": 200.0, "toys": 800.0}

# Feature engineering
df["category_encoded"] = df["product_category"].map(CATEGORY_MAP)
df["reason_encoded"] = df["return_reason"].map(REASON_MAP)
df["grade_encoded"] = df["condition_grade"].map(GRADE_MAP)
df["category_return_rate"] = df["product_category"].map(CATEGORY_RETURN_RATES)
df["refurb_cost"] = df["product_category"].map(REFURB_COST)

# Resale estimate
condition_factor = {4: 0.85, 3: 0.70, 2: 0.55, 1: 0.35, 0: 0.10}
df["resale_estimate"] = df.apply(
    lambda r: r["original_price"] * condition_factor[r["grade_encoded"]], axis=1
)

# Target
df["target"] = df["optimal_route"].map(ROUTE_MAP)

# Feature columns
FEATURES = [
    "category_encoded", "original_price", "product_age_days",
    "reason_encoded", "grade_encoded", "category_return_rate",
    "resale_estimate", "refurb_cost",
]

X = df[FEATURES].values
y = df["target"].values

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Train: {len(X_train)}, Test: {len(X_test)}")
print(f"Classes: {np.unique(y_train)}\n")

# Train LightGBM
model = lgb.LGBMClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    num_leaves=31,
    objective="multiclass",
    num_class=5,
    random_state=42,
    verbose=-1,
)

model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy:.4f}\n")

ROUTE_LABELS = ["resell_as_is", "refurbish", "donate", "recycle", "peer_exchange"]
print("Classification Report:")
print(classification_report(y_test, y_pred, target_names=ROUTE_LABELS))

# Feature importances
print("\nFeature Importances:")
for name, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
    print(f"  {name}: {imp}")

# Save model
os.makedirs("trained_models", exist_ok=True)
joblib.dump(model, OUTPUT_PATH)
print(f"\nModel saved to {OUTPUT_PATH}")
print(f"Model size: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")
