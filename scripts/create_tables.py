"""
Create all DynamoDB tables for Second Life Commerce.
Run once: python scripts/create_tables.py
"""
import boto3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

dynamodb = boto3.client(
    "dynamodb",
    region_name=settings.AWS_DEFAULT_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


TABLES = [
    {
        "TableName": "ReturnEvents",
        "KeySchema": [{"AttributeName": "return_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "return_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "RoutingDecisions",
        "KeySchema": [{"AttributeName": "decision_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "decision_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "GradingRequests",
        "KeySchema": [{"AttributeName": "grading_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "grading_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "GradingResults",
        "KeySchema": [{"AttributeName": "grading_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "grading_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "ReturnRiskPredictions",
        "KeySchema": [{"AttributeName": "prediction_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "prediction_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "ProductReturnSignals",
        "KeySchema": [{"AttributeName": "product_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "product_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "CustomerReturnProfiles",
        "KeySchema": [{"AttributeName": "customer_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "customer_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "ReturnInterventions",
        "KeySchema": [{"AttributeName": "intervention_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [
            {"AttributeName": "intervention_id", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
]


def create_tables():
    existing = dynamodb.list_tables()["TableNames"]

    for table_def in TABLES:
        name = table_def["TableName"]
        if name in existing:
            print(f"  ✓ Table '{name}' already exists, skipping.")
            continue

        try:
            dynamodb.create_table(**table_def)
            print(f"  ✓ Created table '{name}'")
        except Exception as e:
            print(f"  ✗ Error creating '{name}': {e}")

    print("\nDone! All tables ready.")


if __name__ == "__main__":
    print("Creating DynamoDB tables...\n")
    create_tables()
