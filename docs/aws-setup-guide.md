# AWS Setup Guide — Getting Your .env Keys

## Your .env file needs these values:

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=second-life-commerce-images-<your-unique-suffix>
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307
MODEL_PATH=trained_models/
```

Here's how to get each one:

---

## Step 1: Create an AWS Account (skip if you have one)

1. Go to https://aws.amazon.com/free/
2. Click "Create a Free Account"
3. Enter email, password, account name
4. Choose "Personal" account type
5. Enter credit/debit card (you WON'T be charged if staying in free tier)
6. Complete phone verification
7. Select "Basic Support" (free)
8. Done — you'll get $200 in credits on new accounts

---

## Step 2: Get AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

These let your code talk to AWS programmatically.

1. Sign in to AWS Console: https://console.aws.amazon.com/
2. Click your account name (top-right) → "Security credentials"
   - OR go directly to: https://console.aws.amazon.com/iam/
3. In the left sidebar, click **Users** → **Create user**
4. User name: `second-life-commerce-dev`
5. Click **Next**
6. Select **Attach policies directly**
7. Search and check these policies:
   - `AmazonS3FullAccess`
   - `AmazonDynamoDBFullAccess`
   - `AmazonRekognitionFullAccess`
   - `AmazonBedrockFullAccess`
8. Click **Next** → **Create user**
9. Click on the user you just created
10. Go to **Security credentials** tab
11. Scroll to **Access keys** → Click **Create access key**
12. Select **Application running outside AWS** → **Next**
13. Click **Create access key**
14. **COPY BOTH VALUES NOW** (you won't see the secret again):
    - Access key ID → this is your `AWS_ACCESS_KEY_ID` (starts with `AKIA...`)
    - Secret access key → this is your `AWS_SECRET_ACCESS_KEY`

⚠️ **Never commit these to git.** The .gitignore already excludes .env.

---

## Step 3: Set AWS_DEFAULT_REGION

Use `us-east-1` — it has the best Bedrock model availability.

```
AWS_DEFAULT_REGION=us-east-1
```

That's it. No action needed, just use this value.

---

## Step 4: Create S3 Bucket → Get S3_BUCKET_NAME

1. Go to S3 Console: https://console.aws.amazon.com/s3/
2. Click **Create bucket**
3. Bucket name: `second-life-commerce-images-<add-random-suffix>`
   - Example: `second-life-commerce-images-abc123`
   - Must be globally unique across ALL AWS accounts
4. Region: **US East (N. Virginia) us-east-1**
5. **Uncheck** "Block all public access" (we need presigned URLs to work)
   - Check the acknowledgment box
6. Leave everything else as default
7. Click **Create bucket**
8. Copy the bucket name → this is your `S3_BUCKET_NAME`

### Set up CORS (needed for frontend image uploads):
1. Click on your bucket → **Permissions** tab
2. Scroll to **Cross-origin resource sharing (CORS)** → Edit
3. Paste:
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["*"],
    "MaxAgeSeconds": 3000
  }
]
```
4. Save changes

---

## Step 5: Verify Bedrock Access → BEDROCK_MODEL_ID

As of 2025, Bedrock models are auto-enabled — no manual activation needed.
Models activate on first invocation. Just verify it works:

1. Go to Bedrock Console: https://console.aws.amazon.com/bedrock/
   - Make sure you're in **us-east-1** (check top-right region dropdown)
2. Left sidebar → **Model catalog**
3. Find **Claude 3 Haiku** → click it → **Open in playground**
4. If prompted for use case details (first-time Anthropic users):
   - Describe your use case: "Hackathon project — product condition assessment"
   - Approval is typically instant
5. Send a test message in the playground to confirm it responds

Your model ID is:
```
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307
```

If Haiku isn't available, alternatives:
- `anthropic.claude-3-5-haiku-20241022`
- `amazon.titan-text-express-v1` (Amazon's own model, always available)

---

## Step 6: MODEL_PATH

This just points to where your trained .pkl files will live:

```
MODEL_PATH=trained_models/
```

No AWS setup needed. This is a local path.

---

## Final .env File

After all steps, your `.env` should look like:

```
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=second-life-commerce-images-d1v7
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307
MODEL_PATH=trained_models/
```

---

## Verify Everything Works

After filling in your .env, run this quick test:

```bash
python -c "
import boto3
from dotenv import load_dotenv
import os

load_dotenv()

# Test DynamoDB
ddb = boto3.client('dynamodb', region_name='us-east-1')
print('DynamoDB:', ddb.list_tables()['TableNames'] or 'Connected (no tables yet)')

# Test S3
s3 = boto3.client('s3', region_name='us-east-1')
print('S3 Bucket:', os.getenv('S3_BUCKET_NAME'))

# Test Bedrock access
bedrock = boto3.client('bedrock', region_name='us-east-1')
models = bedrock.list_foundation_models()['modelSummaries']
haiku = [m for m in models if 'haiku' in m['modelId']]
print('Bedrock Haiku available:', len(haiku) > 0)

print('\nAll good! Ready to build.')
"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `AccessDeniedException` on Bedrock | Go back to Step 5, make sure model access is granted |
| `NoSuchBucket` | Double-check bucket name in .env matches exactly |
| `InvalidAccessKeyId` | Regenerate access key in IAM (Step 2) |
| `SignatureDoesNotMatch` | Secret key has a typo — regenerate it |
| Bedrock returns empty/error | Check region is us-east-1 in both console AND .env |
| `ResourceNotFoundException` on DynamoDB | Run `python scripts/create_tables.py` first |

---

## Cost Safety

To make sure you never get charged:

1. Go to **AWS Budgets**: https://console.aws.amazon.com/billing/home#/budgets
2. Click **Create budget** → **Zero spend budget**
3. Set email alert at $0.01
4. This will email you the moment anything costs money

DynamoDB (25GB) and Lambda (1M requests) are **always free** — no time limit.
S3 (5GB) and Rekognition (5K images) are free for first 12 months.
Bedrock uses your $200 credits.
