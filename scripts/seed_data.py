"""
Seed demo data into DynamoDB tables.
Run once: python scripts/seed_data.py
"""
import sys
import os
import uuid
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.aws.dynamodb import put_item

# --- Customer Return Profiles ---
CUSTOMERS = [
    {
        "customer_id": "cust-001",
        "total_orders": 25,
        "total_returns": 2,
        "return_rate": Decimal("0.08"),
        "top_return_reasons": ["no_longer_needed"],
        "category_return_rates": {"electronics": "0.05", "clothing": "0.15"},
    },
    {
        "customer_id": "cust-002",
        "total_orders": 40,
        "total_returns": 15,
        "return_rate": Decimal("0.375"),
        "top_return_reasons": ["wrong_size", "not_as_described"],
        "category_return_rates": {"clothing": "0.50", "electronics": "0.20"},
    },
    {
        "customer_id": "cust-003",
        "total_orders": 10,
        "total_returns": 1,
        "return_rate": Decimal("0.10"),
        "top_return_reasons": ["defective"],
        "category_return_rates": {"electronics": "0.10", "home": "0.05"},
    },
    {
        "customer_id": "cust-004",
        "total_orders": 60,
        "total_returns": 25,
        "return_rate": Decimal("0.42"),
        "top_return_reasons": ["wrong_size", "better_price_found"],
        "category_return_rates": {"clothing": "0.55", "toys": "0.30"},
    },
    {
        "customer_id": "cust-005",
        "total_orders": 15,
        "total_returns": 0,
        "return_rate": Decimal("0.00"),
        "top_return_reasons": [],
        "category_return_rates": {},
    },
]

# --- Product Return Signals ---
PRODUCTS = [
    {
        "product_id": "prod-001",
        "category": "electronics",
        "overall_return_rate": Decimal("0.08"),
        "return_rate_by_reason": {"defective": "0.03", "not_as_described": "0.05"},
        "size_issue_rate": Decimal("0.0"),
        "avg_review_sentiment": Decimal("0.75"),
        "description_completeness": Decimal("0.9"),
        "common_complaints": ["battery life shorter than expected"],
    },
    {
        "product_id": "prod-002",
        "category": "clothing",
        "overall_return_rate": Decimal("0.35"),
        "return_rate_by_reason": {"wrong_size": "0.25", "not_as_described": "0.10"},
        "size_issue_rate": Decimal("0.25"),
        "avg_review_sentiment": Decimal("0.55"),
        "description_completeness": Decimal("0.5"),
        "common_complaints": ["runs small", "color differs from photo"],
    },
    {
        "product_id": "prod-003",
        "category": "home",
        "overall_return_rate": Decimal("0.12"),
        "return_rate_by_reason": {"not_as_described": "0.07", "defective": "0.05"},
        "size_issue_rate": Decimal("0.0"),
        "avg_review_sentiment": Decimal("0.65"),
        "description_completeness": Decimal("0.75"),
        "common_complaints": ["assembly instructions unclear"],
    },
    {
        "product_id": "prod-004",
        "category": "clothing",
        "overall_return_rate": Decimal("0.45"),
        "return_rate_by_reason": {"wrong_size": "0.35", "no_longer_needed": "0.10"},
        "size_issue_rate": Decimal("0.35"),
        "avg_review_sentiment": Decimal("0.40"),
        "description_completeness": Decimal("0.4"),
        "common_complaints": ["sizes inconsistent", "fabric feels cheap", "no size chart"],
    },
    {
        "product_id": "prod-005",
        "category": "electronics",
        "overall_return_rate": Decimal("0.05"),
        "return_rate_by_reason": {"defective": "0.02", "no_longer_needed": "0.03"},
        "size_issue_rate": Decimal("0.0"),
        "avg_review_sentiment": Decimal("0.85"),
        "description_completeness": Decimal("0.95"),
        "common_complaints": [],
    },
]


def seed():
    print("Seeding customer profiles...")
    for customer in CUSTOMERS:
        put_item("CustomerReturnProfiles", customer)
        print(f"  ✓ {customer['customer_id']}")

    print("\nSeeding product return signals...")
    for product in PRODUCTS:
        put_item("ProductReturnSignals", product)
        print(f"  ✓ {product['product_id']}")

    print("\nDone! Demo data ready.")
    print("\nDemo scenarios:")
    print("  • Low risk:  cust-005 + prod-005 (no returns + low return product)")
    print("  • Medium:    cust-001 + prod-003 (good customer + medium product)")
    print("  • High risk: cust-002 + prod-002 (serial returner + high return clothing)")
    print("  • Very high: cust-004 + prod-004 (serial returner + problematic product)")


if __name__ == "__main__":
    seed()
