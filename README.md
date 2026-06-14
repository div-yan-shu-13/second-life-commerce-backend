# Second Life Commerce

**AI-Powered Returns & Sustainable Resale Platform**

Every year, millions of products are returned, underused, or discarded. Second Life Commerce uses AI to ensure every returned product gets a meaningful second life — reducing waste, cutting costs, and building customer trust.

## What It Does

1. **Predictive Return Prevention** — Scores return risk before purchase and recommends interventions to reduce returns
2. **Vision-Based Quality Grading** — Uses Amazon Rekognition + Bedrock to assess product condition from photos
3. **Intelligent Product Routing** — ML model decides optimal disposition: resell, refurbish, donate, recycle, or peer exchange

## Tech Stack

- **API**: FastAPI (Python)
- **Database**: Amazon DynamoDB (always-free tier)
- **Image Storage**: Amazon S3
- **Computer Vision**: Amazon Rekognition
- **Generative AI**: Amazon Bedrock (Claude Haiku)
- **ML Models**: LightGBM (routing) + XGBoost (prevention)
- **Hosting**: Render.com (free tier)

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd second-life-commerce
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure AWS credentials
copy .env.example .env
# Edit .env with your AWS credentials

# Create DynamoDB tables
python scripts/create_tables.py

# Seed demo data
python scripts/seed_data.py

# Train ML models (or use pre-trained)
python ml_training/generate_synthetic_data.py
python ml_training/train_routing_model.py
python ml_training/train_prevention_model.py

# Run locally
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/routing/decide` | POST | Route a returned product |
| `/api/v1/routing/decisions/{id}` | GET | Get routing decision |
| `/api/v1/grading/assess` | POST | Grade product from images |
| `/api/v1/grading/{id}` | GET | Get grading result |
| `/api/v1/prevention/score` | POST | Score return risk |
| `/api/v1/prevention/product-signals/{id}` | GET | Product return signals |
| `/api/v1/prevention/analytics` | GET | Prevention stats |

## Architecture

```
Render.com (FastAPI)
    ├── Return Prevention API → XGBoost model
    ├── Quality Grading API  → S3 + Rekognition + Bedrock
    └── Product Routing API  → LightGBM model
        │
        └── Amazon DynamoDB (all data storage)
```

## Team

Built for Amazon HackOn 2026.
