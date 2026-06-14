"""Quick verification that AWS credentials and services are working."""
import boto3
from dotenv import load_dotenv
import os

load_dotenv()

print("Verifying AWS setup...\n")

# Test DynamoDB
try:
    ddb = boto3.client("dynamodb", region_name="us-east-1")
    tables = ddb.list_tables()["TableNames"]
    print(f"✓ DynamoDB: Connected ({len(tables)} tables)" if tables else "✓ DynamoDB: Connected (no tables yet)")
except Exception as e:
    print(f"✗ DynamoDB: {e}")

# Test S3
try:
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket = os.getenv("S3_BUCKET_NAME")
    s3.head_bucket(Bucket=bucket)
    print(f"✓ S3: Bucket '{bucket}' exists")
except Exception as e:
    print(f"✗ S3: {e}")

# Test Bedrock access
try:
    bedrock = boto3.client("bedrock", region_name="us-east-1")
    models = bedrock.list_foundation_models()["modelSummaries"]
    haiku = [m for m in models if "haiku" in m["modelId"]]
    print(f"✓ Bedrock: {len(haiku)} Haiku model(s) available")
except Exception as e:
    print(f"✗ Bedrock: {e}")

print("\nDone!")
