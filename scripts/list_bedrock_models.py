"""List available Bedrock models to find the correct model ID."""
import boto3
from dotenv import load_dotenv
import os

load_dotenv()

client = boto3.client("bedrock", region_name="us-east-1")

# List all foundation models
models = client.list_foundation_models()["modelSummaries"]

print("=== Available Claude/Anthropic models ===\n")
for m in models:
    if "anthropic" in m["modelId"].lower() or "claude" in m["modelId"].lower():
        print(f"  {m['modelId']}")
        print(f"    Name: {m.get('modelName', 'N/A')}")
        print(f"    Input: {m.get('inputModalities', [])}")
        print(f"    Status: {m.get('modelLifecycle', {}).get('status', 'N/A')}")
        print()

print("\n=== Available Amazon Titan models ===\n")
for m in models:
    if "titan" in m["modelId"].lower() and "text" in m["modelId"].lower():
        print(f"  {m['modelId']}")
        print(f"    Name: {m.get('modelName', 'N/A')}")
        print(f"    Input: {m.get('inputModalities', [])}")
        print()

# Also list inference profiles
print("\n=== Inference Profiles ===\n")
try:
    profiles = client.list_inference_profiles()["inferenceProfileSummaries"]
    for p in profiles:
        if "claude" in p.get("inferenceProfileId", "").lower() or "haiku" in p.get("inferenceProfileName", "").lower():
            print(f"  ID: {p['inferenceProfileId']}")
            print(f"  Name: {p.get('inferenceProfileName', 'N/A')}")
            print(f"  Status: {p.get('status', 'N/A')}")
            print()
except Exception as e:
    print(f"  Could not list profiles: {e}")
