# Second Life Commerce — MVP Technical Design (Hackathon Edition)

## Constraints
- **Budget**: $0 — AWS Free Tier + free services only
- **Hosting**: Render.com (free tier) for API server
- **AWS Services**: Free tier (new accounts get $200 credits + always-free services)
- **Timeline**: Hackathon sprint (2-3 days)
- **Scale**: Demo-grade (~100 requests, not production load)

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Render.com (Free Tier)                                │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │              FastAPI Application (Single Service)                    │     │
│  │                                                                     │     │
│  │  /api/v1/routing/*       → LightGBM model (in-memory)             │     │
│  │  /api/v1/grading/*       → Calls Amazon Rekognition + Bedrock     │     │
│  │  /api/v1/prevention/*    → XGBoost model (in-memory)              │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐
│  Amazon DynamoDB   │  │  Amazon S3         │  │  Amazon Bedrock        │
│  (Always Free)     │  │  (Free Tier)       │  │  (Free Credits)        │
│  25GB storage      │  │  5GB storage       │  │  Claude/Titan for      │
│  25 RCU/WCU        │  │  Image uploads     │  │  grading explanations  │
└────────────────────┘  └────────────────────┘  └────────────────────────┘
            │                       │
            ▼                       ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐
│  Amazon Rekognition│  │  AWS Lambda        │  │  Amazon SageMaker      │
│  (Free Tier)       │  │  (Always Free)     │  │  Studio (Free Tier)    │
│  5K images/mo      │  │  1M requests/mo    │  │  Notebook for training │
│  Defect detection  │  │  Background tasks  │  │  (or use Colab)        │
└────────────────────┘  └────────────────────┘  └────────────────────────┘
```

---

## AWS Free Tier Services We're Using

| AWS Service | Free Tier Limit | What We Use It For |
|-------------|----------------|--------------------|
| **Amazon S3** | 5GB storage, 20K GET, 2K PUT/mo | Product image storage |
| **Amazon DynamoDB** | 25GB storage, 25 RCU, 25 WCU (always free) | All application data |
| **AWS Lambda** | 1M requests, 400K GB-sec/mo (always free) | Background processing, async grading |
| **Amazon Rekognition** | 5K images/mo (first 12 months) | Defect detection, label detection |
| **Amazon Bedrock** | Free credits ($200 on new account) | AI-powered grading explanations, condition assessment |
| **Amazon SageMaker** | Studio notebook free tier | Model training (alternative to Colab) |
| **Amazon CloudWatch** | 10 metrics, 10 alarms (always free) | Basic monitoring |
| **API Gateway** | 1M API calls/mo (first 12 months) | Optional: front API Gateway for Lambda |

**New AWS accounts (created after July 2025) get $200 in credits** — more than enough to cover any overages during the hackathon.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| API Framework | FastAPI (Python) | Async, auto-docs, ML-friendly |
| Primary Database | Amazon DynamoDB (always free) | NoSQL, zero maintenance, 25GB free |
| Image Storage | Amazon S3 (free tier) | Native AWS, integrates with Rekognition |
| Vision AI | Amazon Rekognition + Bedrock | AWS-native, no model training needed for demo |
| ML Training | SageMaker Studio or Google Colab | Free notebooks with GPU |
| ML Serving | In-process (load .pkl at startup) | Zero infra for tabular models |
| Hosting | Render.com free tier | Simple deploy, free HTTPS |
| Demo UI (optional) | Streamlit on Render or HF Spaces | Quick to build |

---

## Component 1: Product Routing Engine

### Purpose
Decides the optimal disposition path for a returned/unused product:
resell_as_is | refurbish | donate | recycle | peer_exchange

### Data Schema (DynamoDB)

```
Table: ReturnEvents
  Partition Key: return_id (String/UUID)
  
  Attributes:
    order_id: String
    product_id: String
    customer_id: String
    return_reason: String  # 'wrong_size', 'defective', 'not_as_described', 'no_longer_needed', 'better_price_found'
    return_reason_detail: String
    initiated_at: String (ISO 8601)
    received_at: String (ISO 8601)
    product_category: String
    product_subcategory: String
    original_price: Number
    product_age_days: Number
    warranty_status: String  # 'active', 'expired', 'none'
    created_at: String (ISO 8601)

  GSI: CategoryIndex
    Partition Key: product_category
    Sort Key: initiated_at


Table: RoutingDecisions
  Partition Key: decision_id (String/UUID)
  
  Attributes:
    return_id: String
    route: String  # 'resell_as_is', 'refurbish', 'donate', 'recycle', 'peer_exchange'
    confidence_score: Number
    model_version: String
    reasoning: Map  # {top_factors: [{feature, importance, value}]}
    estimated_recovery: Number
    estimated_cost: Number
    override_by: String
    override_reason: String
    decided_at: String (ISO 8601)
    outcome_status: String  # 'pending', 'in_progress', 'completed', 'failed'
    actual_recovery: Number
    created_at: String (ISO 8601)

  GSI: ReturnIndex
    Partition Key: return_id
    Sort Key: decided_at
```

### API Contract

```yaml
# POST /api/v1/routing/decide
Request:
  return_id: string (required)
  product_id: string (required)
  return_reason: string (required)
  condition_grade: string (optional — from grading service)
  condition_confidence: float (optional)

Response (200):
  decision_id: string
  route: string  # 'resell_as_is' | 'refurbish' | 'donate' | 'recycle' | 'peer_exchange'
  confidence: float
  estimated_recovery_usd: float
  estimated_cost_usd: float
  reasoning:
    top_factors:
      - feature: string
        importance: float
        value: any
  requires_human_review: boolean

# GET /api/v1/routing/decisions/{decision_id}
Response (200):
  decision_id: string
  return_id: string
  route: string
  confidence: float
  status: string
  decided_at: string

# POST /api/v1/routing/decisions/{decision_id}/override
Request:
  new_route: string (required)
  reason: string (required)

Response (200):
  decision_id: string
  original_route: string
  new_route: string
  status: "overridden"
```

### ML Pipeline (Hackathon Approach)

**Training (SageMaker Studio Notebook or Google Colab):**
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Generate    │    │  Feature     │    │  Train       │    │  Export      │
│  Synthetic   │───▶│  Engineering │───▶│  LightGBM    │───▶│  model.pkl   │
│  Dataset     │    │  (pandas)    │    │              │    │  to S3/repo  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

**Synthetic Data Strategy:**
- Generate 10K-50K synthetic return records with realistic distributions
- Categories: electronics (25%), clothing (35%), home (20%), books (10%), toys (10%)
- Return reasons correlated with category (clothing → wrong_size, electronics → defective)
- Labels: optimal route based on business logic rules + noise

**Model:**
- Algorithm: LightGBM multi-class classifier
- Target: 5 classes (resell_as_is, refurbish, donate, recycle, peer_exchange)
- Training time: ~2 min
- Model size: ~2-5MB
- Export: `joblib.dump()` → commit to repo or upload to S3

**Features:**
| Feature | Type | Source |
|---------|------|--------|
| product_category | Categorical (encoded) | Return event |
| original_price | Numeric | Return event |
| product_age_days | Numeric | Return event |
| return_reason | Categorical (encoded) | Return event |
| condition_grade | Ordinal (0-4) | Grading service |
| category_avg_return_rate | Numeric | Precomputed lookup |
| estimated_resale_value | Numeric | price × condition_factor |
| estimated_refurb_cost | Numeric | Category-based lookup |

**Serving (on Render):**
- Load model at startup: `model = joblib.load("models/routing_model.pkl")`
- Inference: < 5ms per request
- No GPU needed

---

## Component 2: Vision-Based Quality Grading

### Purpose
Assess product condition from images, output a standardized grade + defect info.

### AWS Services Used
- **Amazon S3**: Store uploaded product images
- **Amazon Rekognition**: Detect labels, defects, damage (DetectLabels, DetectCustomLabels)
- **Amazon Bedrock** (Claude/Titan): Analyze image + generate human-readable condition explanation

### Data Schema (DynamoDB)

```
Table: GradingRequests
  Partition Key: grading_id (String/UUID)
  
  Attributes:
    return_id: String
    product_id: String
    product_category: String
    image_keys: List  # S3 keys [{key, angle}]
    text_description: String
    status: String  # 'pending', 'completed', 'failed'
    created_at: String (ISO 8601)


Table: GradingResults
  Partition Key: grading_id (String/UUID)
  
  Attributes:
    overall_grade: String  # 'like_new', 'very_good', 'good', 'acceptable', 'for_parts'
    overall_confidence: Number
    model_version: String
    defects: List  # [{type, severity, confidence}]
    grade_explanation: String  # Generated by Bedrock
    processing_time_ms: Number
    rekognition_labels: List  # Raw Rekognition output
    created_at: String (ISO 8601)

  GSI: ReturnIndex
    Partition Key: return_id
```

### API Contract

```yaml
# POST /api/v1/grading/assess
# Upload image(s) for quality grading
Request (multipart/form-data):
  product_id: string (required)
  product_category: string (required)
  images: File[] (required — up to 5 images)
  text_description: string (optional)

Response (200):
  grading_id: string
  overall_grade: string
  confidence: float
  defects:
    - type: string  # 'scratch', 'dent', 'stain', 'crack', 'missing_part', 'wear'
      severity: string  # 'minor', 'moderate', 'severe'
      confidence: float
  explanation: string  # AI-generated natural language explanation
  image_urls: string[]  # S3 presigned URLs

# GET /api/v1/grading/{grading_id}
Response (200):
  grading_id: string
  status: string
  result:
    overall_grade: string
    confidence: float
    defects: array
    explanation: string
```

### ML Pipeline (Hackathon Approach)

**No custom model training needed!** We combine AWS managed AI services:

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐
│  Image       │    │  Amazon          │    │  Amazon Bedrock  │    │  Grade       │
│  Upload      │───▶│  Rekognition     │───▶│  (Claude/Titan)  │───▶│  Decision    │
│  to S3       │    │  DetectLabels    │    │  Analyze + Grade │    │  + Explain   │
└──────────────┘    └──────────────────┘    └──────────────────┘    └──────────────┘
```

**Step 1: Amazon Rekognition** (5K images/mo free)
```python
# Detect labels and potential damage indicators
response = rekognition.detect_labels(
    Image={'S3Object': {'Bucket': bucket, 'Name': key}},
    MaxLabels=20,
    MinConfidence=70
)
# Returns labels like: 'Scratch', 'Dent', 'Stain', 'Crack', 'Electronics', 'Phone', etc.
```

**Step 2: Amazon Bedrock** (using free credits)
```python
# Send image + Rekognition labels to Claude/Titan for condition grading
prompt = f"""
You are a product condition grading expert. Analyze this product image.

Rekognition detected labels: {labels}
Product category: {category}
Seller description: {description}

Grade this product on the following scale:
- like_new: Perfect condition, no visible wear, original packaging
- very_good: Minimal wear, fully functional, minor cosmetic imperfections
- good: Some visible wear, fully functional, noticeable cosmetic issues
- acceptable: Significant wear or damage, still functional
- for_parts: Major damage, not fully functional

Respond in JSON format:
{{
  "grade": "...",
  "confidence": 0.0-1.0,
  "defects": [{{"type": "...", "severity": "minor|moderate|severe"}}],
  "explanation": "..."
}}
"""

response = bedrock.invoke_model(
    modelId='anthropic.claude-3-haiku-20240307',  # cheapest, fast
    body=json.dumps({"prompt": prompt, "max_tokens": 500})
)
```

**Why this approach works for hackathon:**
- Zero training required
- Rekognition gives structured object/damage detection
- Bedrock gives intelligent reasoning + natural language explanation
- Both are AWS-native → looks great to Amazon judges
- Combined free tier easily handles demo volume

**Fallback (if Bedrock credits run out):**
- Use CLIP zero-shot locally (same approach from before)
- Or use Rekognition labels alone with a rule-based grading function

---

## Component 3: Predictive Return Prevention

### Purpose
Score return risk at browse/cart/checkout time; suggest interventions to reduce returns.

### Data Schema (DynamoDB)

```
Table: ReturnRiskPredictions
  Partition Key: prediction_id (String/UUID)
  
  Attributes:
    customer_id: String
    product_id: String
    prediction_context: String  # 'browse', 'cart_add', 'checkout'
    risk_score: Number  # 0.0 to 1.0
    risk_bucket: String  # 'low', 'medium', 'high'
    top_risk_factors: List  # [{factor, contribution, detail}]
    model_version: String
    predicted_at: String (ISO 8601)
    was_purchased: Boolean
    was_returned: Boolean
    created_at: String (ISO 8601)

  GSI: CustomerIndex
    Partition Key: customer_id
    Sort Key: predicted_at


Table: ReturnInterventions
  Partition Key: intervention_id (String/UUID)
  
  Attributes:
    prediction_id: String
    intervention_type: String  # 'size_recommendation', 'review_highlight', 'comparison_nudge', 'info_enrichment', 'return_rate_warning'
    displayed_at: String (ISO 8601)
    interacted: Boolean
    interaction_type: String
    purchase_after: Boolean
    return_after: Boolean
    created_at: String (ISO 8601)

  GSI: PredictionIndex
    Partition Key: prediction_id


Table: ProductReturnSignals
  Partition Key: product_id (String)
  
  Attributes:
    category: String
    overall_return_rate: Number
    return_rate_by_reason: Map
    size_issue_rate: Number
    avg_review_sentiment: Number
    description_completeness: Number
    common_complaints: List
    last_updated: String (ISO 8601)


Table: CustomerReturnProfiles
  Partition Key: customer_id (String)
  
  Attributes:
    total_orders: Number
    total_returns: Number
    return_rate: Number
    top_return_reasons: List
    category_return_rates: Map
    last_updated: String (ISO 8601)
```

### API Contract

```yaml
# POST /api/v1/prevention/score
Request:
  customer_id: string (required)
  product_id: string (required)
  context: string (required) — 'browse' | 'cart_add' | 'checkout'
  selected_variant: object (optional)
    size: string
    color: string

Response (200):
  prediction_id: string
  risk_score: float  # 0.0 to 1.0
  risk_bucket: string  # 'low' | 'medium' | 'high'
  top_risk_factors:
    - factor: string
      contribution: float
      detail: string
  recommended_interventions:
    - type: string
      priority: int
      message: string

# GET /api/v1/prevention/product-signals/{product_id}
Response (200):
  product_id: string
  overall_return_rate: float
  top_return_reasons:
    - reason: string
      rate: float
  risk_flags: string[]

# GET /api/v1/prevention/analytics
Response (200):
  total_predictions: int
  high_risk_count: int
  interventions_shown: int
  estimated_returns_prevented: int
```

### ML Pipeline (Hackathon Approach)

**Training (SageMaker Studio or Google Colab):**
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Generate    │    │  Feature     │    │  Train       │    │  Export      │
│  Synthetic   │───▶│  Engineering │───▶│  XGBoost     │───▶│  model.pkl   │
│  Order Data  │    │  (pandas)    │    │  Binary Clf  │    │  to S3/repo  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

**Synthetic Data Strategy:**
- Generate 50K synthetic order records
- ~15% marked as returned (realistic industry rate)
- Patterns encoded: clothing = high return rate, serial returners exist, expensive items returned less
- Model learns these patterns → demonstrates prediction capability

**Model:**
- Algorithm: XGBoost binary classifier
- Target: will_return (0/1)
- Output: probability score (0.0 - 1.0)
- Model size: ~2-5MB
- Inference: < 10ms

**Features:**
| Feature | Type | Source |
|---------|------|--------|
| customer_return_rate | Numeric | CustomerReturnProfiles table |
| customer_category_return_rate | Numeric | Computed per category |
| product_return_rate | Numeric | ProductReturnSignals table |
| product_size_issue_rate | Numeric | ProductReturnSignals table |
| price_vs_category_avg | Numeric | Computed |
| review_sentiment | Numeric | Precomputed |
| description_completeness | Numeric | Precomputed |
| category (encoded) | Categorical | Product data |
| is_first_purchase_in_category | Binary | Customer history |

**Intervention Selection (Rule-Based):**
```python
def select_interventions(risk_score, risk_factors):
    interventions = []
    if risk_score < 0.3:
        return []  # low risk, no intervention
    
    for factor in risk_factors:
        if factor["name"] == "size_issue_rate":
            interventions.append({
                "type": "size_recommendation",
                "priority": 1,
                "message": "Customers similar to you found this runs small. Consider sizing up."
            })
        elif factor["name"] == "description_completeness":
            interventions.append({
                "type": "info_enrichment",
                "priority": 2,
                "message": "Here are key details other buyers wanted to know before purchasing."
            })
        elif factor["name"] == "product_return_rate":
            interventions.append({
                "type": "review_highlight",
                "priority": 2,
                "message": "See what verified buyers say about this product's quality."
            })
    
    if not interventions:
        interventions.append({
            "type": "return_rate_warning",
            "priority": 3,
            "message": f"Note: {int(risk_score*100)}% of similar purchases are returned. Make sure this meets your needs."
        })
    
    return sorted(interventions, key=lambda x: x["priority"])
```

---

## Cross-Component Integration Flow

```
Customer browses product
        │
        ▼
┌──────────────────────────────┐
│ POST /api/v1/prevention/score │
│ → XGBoost risk prediction     │
└──────────────────────────────┘
        │
        ▼  risk_score > 0.6?
   ┌────┴────┐
   Yes       No → normal flow
   │
   ▼
Show intervention (size guide, review summary, etc.)
        │
        ▼
Customer purchases anyway
        │
        ▼ (if return initiated)
Customer uploads product photos
        │
        ▼
┌──────────────────────────────┐
│ POST /api/v1/grading/assess   │
│ → Upload to S3                │
│ → Rekognition: detect damage  │
│ → Bedrock: grade + explain    │
└──────────────────────────────┘
        │
        ▼ condition_grade + defects
┌──────────────────────────────┐
│ POST /api/v1/routing/decide   │
│ → LightGBM classification     │
└──────────────────────────────┘
        │
        ▼
Route: resell / refurbish / donate / recycle / exchange
```

---

## Project Structure

```
second-life-commerce/
├── app/
│   ├── main.py                 # FastAPI app, model loading at startup
│   ├── config.py               # AWS credentials, env vars
│   ├── aws/                    # AWS service clients
│   │   ├── dynamodb.py         # DynamoDB operations
│   │   ├── s3.py               # S3 upload/presigned URLs
│   │   ├── rekognition.py      # Image analysis
│   │   └── bedrock.py          # LLM calls for grading
│   ├── routers/                # API route handlers
│   │   ├── routing.py
│   │   ├── grading.py
│   │   └── prevention.py
│   ├── ml/                     # ML inference logic
│   │   ├── routing_model.py    # Load & predict with LightGBM
│   │   └── prevention_model.py # Load & predict with XGBoost
│   └── services/               # Business logic
│       ├── routing_service.py
│       ├── grading_service.py
│       └── prevention_service.py
├── ml_training/                # Training notebooks
│   ├── train_routing_model.ipynb
│   ├── train_prevention_model.ipynb
│   └── generate_synthetic_data.ipynb
├── trained_models/             # Exported model artifacts
│   ├── routing_lgbm.pkl
│   └── prevention_xgb.pkl
├── scripts/
│   ├── create_tables.py        # DynamoDB table creation
│   └── seed_data.py            # Seed demo data
├── requirements.txt
├── render.yaml                 # Render deployment config
├── .env.example
└── docs/
    └── mvp-technical-design.md
```

---

## Deployment

### Render Configuration (render.yaml)
```yaml
services:
  - type: web
    name: second-life-commerce-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: AWS_ACCESS_KEY_ID
        sync: false
      - key: AWS_SECRET_ACCESS_KEY
        sync: false
      - key: AWS_DEFAULT_REGION
        value: us-east-1
      - key: S3_BUCKET_NAME
        sync: false
      - key: BEDROCK_MODEL_ID
        value: anthropic.claude-3-haiku-20240307
    plan: free
```

### Environment Variables
```bash
# .env.example
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=second-life-commerce-images
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307
MODEL_PATH=trained_models/
```

### Memory Budget (Render 512MB)
- XGBoost prevention model: ~5MB ✓
- LightGBM routing model: ~5MB ✓
- FastAPI + boto3 + dependencies: ~150MB ✓
- Headroom for request handling: ~350MB ✓
- (No CLIP model needed — Rekognition + Bedrock handle vision externally)

**Big win**: By using Rekognition + Bedrock for vision, we don't load any large model in memory. This keeps Render's 512MB comfortable.

---

## Optional: Lambda for Background Processing

If you want to show more AWS integration, use Lambda for async grading:

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│  FastAPI  │────▶│  S3 Put  │────▶│  Lambda      │────▶│ DynamoDB │
│  (upload) │     │  Event   │     │  (grading)   │     │ (result) │
└──────────┘     └──────────┘     └──────────────┘     └──────────┘
```

- S3 upload triggers Lambda automatically
- Lambda calls Rekognition + Bedrock
- Lambda writes result to DynamoDB
- FastAPI polls DynamoDB for result (or client polls)

This is more "AWS-native" and impressive for judges, but adds complexity. Choose based on time available.

---

## AWS Setup Checklist

1. **Create AWS Account** (if new → get $200 credits automatically)
2. **Create S3 Bucket** (`second-life-commerce-images`, us-east-1)
3. **Create DynamoDB Tables** (run `scripts/create_tables.py`)
4. **Enable Bedrock Model Access** (Console → Bedrock → Model Access → enable Claude Haiku)
5. **Create IAM User** for Render (programmatic access with policies for S3, DynamoDB, Rekognition, Bedrock)
6. **Set Render env vars** with IAM credentials

### IAM Policy (minimum permissions)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::second-life-commerce-images",
        "arn:aws:s3:::second-life-commerce-images/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:DetectLabels",
        "rekognition:DetectModerationLabels"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/*"
    }
  ]
}
```

---

## What to Show vs What to Explain

| Show (Working Demo) | Explain (Architecture Slides) |
|---------------------|-------------------------------|
| Live API calls → real AWS responses | Production: microservices + Kafka |
| S3 image upload → Rekognition analysis | Custom-trained defect detection on SageMaker |
| Bedrock generating condition explanations | Fine-tuned domain-specific model |
| DynamoDB storing/retrieving decisions | Multi-region DynamoDB Global Tables |
| XGBoost risk scoring with SHAP values | Causal uplift model for interventions |
| Lambda processing (if built) | Step Functions orchestration |
| Render live URL | ECS/EKS deployment with auto-scaling |

---

## Hackathon Judging Angle

**Why this architecture impresses Amazon judges:**
1. **Uses AWS services correctly** — not just for the sake of it, but where they genuinely fit
2. **DynamoDB** for low-latency NoSQL → perfect for feature lookups and decisions
3. **S3** as the image backbone → feeds directly into Rekognition
4. **Rekognition** for computer vision → demonstrates managed ML service understanding
5. **Bedrock** for generative AI → shows awareness of Amazon's GenAI strategy
6. **Lambda** for event-driven processing → serverless-first thinking
7. **Shows production path** — the free tier demo scales to production without re-architecture

---

## Free Services Summary

| Service | What For | Free Limit | Cost Risk |
|---------|----------|------------|-----------|
| AWS DynamoDB | All data storage | 25GB, 25 RCU/WCU (always free) | None |
| AWS S3 | Image storage | 5GB, 20K GETs (12 months) | None at demo scale |
| AWS Lambda | Background processing | 1M requests (always free) | None |
| AWS Rekognition | Defect/label detection | 5K images (12 months) | None at demo scale |
| AWS Bedrock | AI grading explanations | Covered by $200 credits | Monitor usage |
| AWS CloudWatch | Monitoring | 10 metrics (always free) | None |
| Render.com | API hosting | 750h/mo, 512MB RAM | None |
| Google Colab | Model training | Free T4 GPU | None |
| GitHub | Code + model storage | Unlimited | None |

**Total cost: $0** (assuming new AWS account or existing free tier eligibility)
