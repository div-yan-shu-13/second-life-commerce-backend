# Second Life Commerce

**AI-Powered Returns & Sustainable Resale Platform**

Every year, millions of products are returned, underused, or discarded. Second Life Commerce uses AI to ensure every returned product gets a meaningful second life — reducing waste, cutting costs, and building customer trust.

## What It Does

1. **Predictive Return Prevention** — Scores return risk before purchase and recommends interventions to reduce returns
2. **Vision-Based Quality Grading** — Uses Google Gemini AI to assess product condition from photos
3. **Intelligent Product Routing** — ML model decides optimal disposition: resell, refurbish, donate, recycle, or peer exchange

## Tech Stack

- **API**: FastAPI (Python)
- **Database**: Amazon DynamoDB (always-free tier)
- **Image Storage**: Amazon S3
- **Vision AI**: Google Gemini 2.5 Flash (multimodal image analysis)
- **ML Models**: LightGBM (routing) + XGBoost (prevention)
- **Hosting**: Render.com (free tier)

## Architecture

```
Render.com (FastAPI)
    ├── Return Prevention API  → XGBoost model + DynamoDB lookups
    ├── Quality Grading API   → S3 upload + Gemini vision AI
    └── Product Routing API   → LightGBM model + DynamoDB storage
        │
        ├── Amazon DynamoDB (all application data)
        ├── Amazon S3 (product image storage)
        └── Google Gemini API (AI vision grading)
```

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd second-life-commerce
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure credentials
copy .env.example .env
# Edit .env with your AWS credentials + Gemini API key

# Create DynamoDB tables
python scripts/create_tables.py

# Seed demo data
python scripts/seed_data.py

# Train ML models
python ml_training/generate_synthetic_data.py
python ml_training/train_routing_model.py
python ml_training/train_prevention_model.py

# Run locally
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

## Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS IAM | Programmatic access key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM | Secret key |
| `AWS_DEFAULT_REGION` | — | `us-east-1` |
| `S3_BUCKET_NAME` | AWS S3 | Your bucket name |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) | Free API key for vision AI |
| `USE_BEDROCK` | — | `true` to enable AI grading, `false` for fallback |
| `MODEL_PATH` | — | `trained_models/` |
| `RENDER_EXTERNAL_URL` | Render | Your deployed URL (for keep-alive) |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/prevention/score` | POST | Score return risk for customer + product |
| `/api/v1/prevention/product-signals/{id}` | GET | Product return statistics |
| `/api/v1/prevention/analytics` | GET | Aggregate prevention stats |
| `/api/v1/grading/assess` | POST | Upload images → AI condition grade |
| `/api/v1/grading/{id}` | GET | Fetch grading result |
| `/api/v1/routing/decide` | POST | Route a returned product |
| `/api/v1/routing/decisions/{id}` | GET | Fetch routing decision |
| `/api/v1/routing/decisions/{id}/override` | POST | Human override of AI decision |
| `/health` | GET | Health check |

## AWS Services Used (Free Tier)

| Service | Purpose | Free Limit |
|---------|---------|-----------|
| DynamoDB | All application data | 25GB, always free |
| S3 | Product image storage | 5GB, 12 months free |

## How It Works

```
Customer browses product
    → Prevention API scores return risk
    → If high risk: show interventions (size guide, reviews, warnings)

Customer returns product
    → Uploads product photo
    → Grading API: S3 upload → Gemini AI analyzes condition
    → Returns grade (like_new → for_parts) + defects + explanation

AI decides product's next life
    → Routing API: LightGBM classifies optimal route
    → Routes to: resell / refurbish / donate / recycle / peer exchange
    → Shows confidence score + reasoning
```

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI app + keep-alive
│   ├── config.py            # Environment config
│   ├── aws/                 # AWS + Gemini service clients
│   │   ├── dynamodb.py      # DynamoDB operations
│   │   ├── s3.py            # S3 upload/presigned URLs
│   │   ├── rekognition.py   # Rekognition (backup)
│   │   └── bedrock.py       # Gemini vision AI
│   ├── routers/             # API endpoints
│   ├── ml/                  # ML model loading + inference
│   └── services/            # Business logic
├── ml_training/             # Model training scripts
├── trained_models/          # Exported .pkl model files
├── scripts/                 # Setup scripts
├── docs/                    # Documentation
├── requirements.txt
├── render.yaml              # Render deployment config
└── .python-version          # Python 3.11
```

## Team

Built for Amazon HackOn 2026.
