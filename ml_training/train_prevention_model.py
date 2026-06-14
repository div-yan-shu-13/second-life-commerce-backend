"""
Train XGBoost return prevention model.
Run: python ml_training/train_prevention_model.py
"""
import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    accuracy_score,
)
import xgboost as xgb

# Load data
DATA_PATH = "ml_training/data/prevention_training_data.csv"
OUTPUT_PATH = "trained_models/prevention_xgb.pkl"

if not os.path.exists(DATA_PATH):
    print("Training data not found. Run generate_synthetic_data.py first.")
    exit(1)

df = pd.read_csv(DATA_PATH)
print(f"Loaded {len(df)} samples")
print(f"Return rate: {df['was_returned'].mean():.2%}\n")

# Features and target
FEATURES = [
    "customer_return_rate", "customer_category_rate",
    "product_return_rate", "size_issue_rate",
    "review_sentiment", "description_completeness",
    "category_encoded", "is_first_in_category",
]

X = df[FEATURES].values
y = df["was_returned"].values

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Train: {len(X_train)}, Test: {len(X_test)}")
print(f"Positive rate (train): {y_train.mean():.2%}\n")

# Train XGBoost
model = xgb.XGBClassifier(
    n_estimators=150,
    max_depth=5,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="binary:logistic",
    eval_metric="auc",
    random_state=42,
    use_label_encoder=False,
)

model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

# Evaluate
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)

print(f"Accuracy: {accuracy:.4f}")
print(f"AUC-ROC:  {auc:.4f}\n")

print("Classification Report:")
print(classification_report(y_test, y_pred, target_names=["kept", "returned"]))

# Feature importances
print("\nFeature Importances:")
for name, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
    print(f"  {name}: {imp:.4f}")

# Calibration check
print("\nCalibration (predicted vs actual return rates):")
bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
df_cal = pd.DataFrame({"predicted": y_proba, "actual": y_test})
df_cal["bin"] = pd.cut(df_cal["predicted"], bins=bins)
cal = df_cal.groupby("bin", observed=True).agg(
    mean_predicted=("predicted", "mean"),
    mean_actual=("actual", "mean"),
    count=("actual", "count"),
)
print(cal.to_string())

# Save model
os.makedirs("trained_models", exist_ok=True)
joblib.dump(model, OUTPUT_PATH)
print(f"\nModel saved to {OUTPUT_PATH}")
print(f"Model size: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")
