"""List inference profiles available."""
import boto3
from dotenv import load_dotenv

load_dotenv()

client = boto3.client("bedrock", region_name="us-east-1")

# Try listing inference profiles with correct method
try:
    paginator = client.get_paginator("list_inference_profiles")
    for page in paginator.paginate():
        for p in page.get("inferenceProfileSummaries", []):
            pid = p.get("inferenceProfileId", "")
            if "claude" in pid.lower() or "haiku" in pid.lower():
                print(f"  ID: {pid}")
                print(f"  Name: {p.get('inferenceProfileName', '')}")
                print(f"  Type: {p.get('type', '')}")
                print(f"  Status: {p.get('status', '')}")
                print()
except Exception as e:
    print(f"Paginator failed: {e}")
    # Try direct call
    try:
        resp = client.list_inference_profiles(maxResults=100)
        for p in resp.get("inferenceProfileSummaries", []):
            pid = p.get("inferenceProfileId", "")
            if "claude" in pid.lower() or "haiku" in pid.lower():
                print(f"  ID: {pid}")
                print(f"  Name: {p.get('inferenceProfileName', '')}")
                print()
    except Exception as e2:
        print(f"Direct call also failed: {e2}")
        print("\nTrying alternative: invoke with us. prefix...")
        # Just test invoke directly
        rt = boto3.client("bedrock-runtime", region_name="us-east-1")
        test_ids = [
            "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
            "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        ]
        import json
        for mid in test_ids:
            try:
                resp = rt.converse(
                    modelId=mid,
                    messages=[{"role": "user", "content": [{"text": "Say hi"}]}],
                    inferenceConfig={"maxTokens": 10},
                )
                print(f"  ✓ WORKS: {mid}")
            except Exception as ex:
                err = str(ex)[:100]
                print(f"  ✗ {mid}: {err}")
