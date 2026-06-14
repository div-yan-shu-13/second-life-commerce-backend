# Second Life Commerce — Implementation Plan

## Phase 0: Account Setup & Prerequisites (30-60 min)

### Step 0.1: AWS Account
- [ ] Create AWS account at https://aws.amazon.com/free/ (if you don't have one)
  - Use a credit/debit card (won't be charged if you stay in free tier)
  - New accounts get $200 in credits automatically
- [ ] Sign into AWS Console
- [ ] Set region to **us-east-1** (best Bedrock model availability)

### Step 0.2: AWS IAM Setup
- [ ] Go to IAM → Users → Create User: `second-life-commerce-dev`
- [ ] Attach policies: `AmazonS3FullAccess`, `AmazonDynamoDBFullAccess`, `AmazonRekognitionReadOnlyAccess`, `AmazonBedrockFullAccess`
  - (For hackathon speed, full access is fine. Production would use least-privilege.)
- [ ] Create Access Key (CLI/programmatic) → save `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

### Step 0.3: Enable Bedrock Model Access
- [ ] Go to AWS Console → Amazon Bedrock → Model Access (left sidebar)
- [ ] Request access to: `Anthropic Claude 3 Haiku` (cheapest, fastest)
- [ ] Wait for approval (usually instant for Haiku)

### Step 0.4: Create S3 Bucket
- [ ] Go to S3 → Create Bucket
  - Name: `second-life-commerce-images` (must be globally unique, add random suffix if taken)
  - Region: us-east-1
  - Uncheck "Block all public access" (we'll use presigned URLs, but unblock for flexibility)
  - Enable CORS (for frontend uploads later):
    ```json
    [{"AllowedHeaders":["*"],"AllowedMethods":["GET","PUT","POST"],"AllowedOrigins":["*"],"MaxAgeSeconds":3000}]
    ```

### Step 0.5: Local Dev Environment
- [ ] Install Python 3.10+ (if not already)
- [ ] Install AWS CLI: `pip install awscli` → run `aws configure` with your keys
- [ ] Create project directory and Git repo
- [ ] Create virtual environment: `python -m venv venv`

### Step 0.6: Render.com Account
- [ ] Sign up at https://render.com (GitHub login works)
- [ ] No payment method needed for free tier

---

## Phase 1: Project Skeleton & Database (1-2 hours)

### Step 1.1: Initialize Project Structure
- [ ] Create folder structure:
  ```
  second-life-commerce/
  ├── app/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.py
  │   ├── aws/
  │   │   ├── __init__.py
  │   │   ├── dynamodb.py
  │   │   ├── s3.py
  │   │   ├── rekognition.py
  │   │   └── bedrock.py
  │   ├── routers/
  │   │   ├── __init__.py
  │   │   ├── routing.py
  │   │   ├── grading.py
  │   │   └── prevention.py
  │   ├── ml/
  │   │   ├── __init__.py
  │   │   ├── routing_model.py
  │   │   └── prevention_model.py
  │   └── services/
  │       ├── __init__.py
  │       ├── routing_service.py
  │       ├── grading_service.py
  │       └── prevention_service.py
  ├── ml_training/
  ├── trained_models/
  ├── scripts/
  │   ├── create_tables.py
  │   └── seed_data.py
  ├── requirements.txt
  ├── render.yaml
  ├── .env.example
  ├── .gitignore
  └── README.md
  ```

### Step 1.2: Create requirements.txt
```
fastapi==0.104.1
uvicorn==0.24.0
boto3==1.34.0
python-multipart==0.0.6
python-dotenv==1.0.0
pydantic==2.5.0
joblib==1.3.2
numpy==1.26.2
xgboost==2.0.2
lightgbm==4.1.0
scikit-learn==1.3.2
mangum==0.17.0
```

### Step 1.3: Create DynamoDB Tables
- [ ] Write `scripts/create_tables.py` that creates all 7 tables:
  - ReturnEvents
  - RoutingDecisions
  - GradingRequests
  - GradingResults
  - ReturnRiskPredictions
  - ProductReturnSignals
  - CustomerReturnProfiles
- [ ] Run script: `python scripts/create_tables.py`
- [ ] Verify in AWS Console → DynamoDB → Tables

### Step 1.4: Create FastAPI Skeleton
- [ ] `app/main.py` — app initialization, health check endpoint
- [ ] `app/config.py` — load env vars, AWS client configuration
- [ ] `app/aws/dynamodb.py` — DynamoDB client + helper functions (put_item, get_item, query)
- [ ] `app/aws/s3.py` — S3 client + upload/presigned URL functions
- [ ] Test locally: `uvicorn app.main:app --reload` → hit http://localhost:8000/docs

---

## Phase 2: ML Model Training (2-3 hours)

### Step 2.1: Generate Synthetic Data (Google Colab or SageMaker Studio)
- [ ] Create `ml_training/generate_synthetic_data.ipynb`
- [ ] Generate routing training data:
  - 10K return events with realistic category/reason/price distributions
  - Label optimal routes using business rules + noise
- [ ] Generate prevention training data:
  - 50K order records with ~15% return rate
  - Encode known patterns (clothing→high returns, serial returners, etc.)
- [ ] Save datasets as CSV to Colab/local

### Step 2.2: Train Routing Model
- [ ] Create `ml_training/train_routing_model.ipynb`
- [ ] Feature engineering (encode categoricals, normalize numerics)
- [ ] Train LightGBM multi-class classifier (5 routes)
- [ ] Evaluate: accuracy, per-class F1, confusion matrix
- [ ] Export: `joblib.dump(model, 'routing_lgbm.pkl')`
- [ ] Download .pkl file to `trained_models/`

### Step 2.3: Train Prevention Model
- [ ] Create `ml_training/train_prevention_model.ipynb`
- [ ] Feature engineering (customer features, product features)
- [ ] Train XGBoost binary classifier (will_return: 0/1)
- [ ] Evaluate: AUC-ROC, precision-recall curve
- [ ] Generate SHAP values for explainability
- [ ] Export: `joblib.dump(model, 'prevention_xgb.pkl')`
- [ ] Download .pkl file to `trained_models/`

### Step 2.4: Verify Models Load
- [ ] Test loading both models locally in Python
- [ ] Check memory usage (should be < 10MB each)
- [ ] Run sample predictions to verify output format

---

## Phase 3: Core API — Product Routing Engine (2-3 hours)

### Step 3.1: Routing Service
- [ ] `app/services/routing_service.py`:
  - Load LightGBM model on import
  - `predict_route(features_dict)` → route, confidence, reasoning
  - Feature engineering function (transform API input → model features)

### Step 3.2: Routing Router
- [ ] `app/routers/routing.py`:
  - `POST /api/v1/routing/decide` — accept return info, call model, store decision in DynamoDB, return result
  - `GET /api/v1/routing/decisions/{decision_id}` — fetch from DynamoDB
  - `POST /api/v1/routing/decisions/{decision_id}/override` — update route in DynamoDB

### Step 3.3: Test Routing
- [ ] Test via FastAPI Swagger UI (http://localhost:8000/docs)
- [ ] Verify DynamoDB entries are created
- [ ] Verify model returns sensible routes for different inputs

---

## Phase 4: Core API — Vision Quality Grading (2-3 hours)

### Step 4.1: AWS Integration
- [ ] `app/aws/rekognition.py`:
  - `detect_labels(s3_bucket, s3_key)` → list of labels with confidence
  - `detect_moderation_labels(...)` → content moderation check
- [ ] `app/aws/bedrock.py`:
  - `grade_product(image_labels, category, description)` → grade, defects, explanation
  - Prompt template for Claude Haiku
- [ ] `app/aws/s3.py`:
  - `upload_image(file_bytes, filename)` → s3_key
  - `get_presigned_url(s3_key)` → temporary download URL

### Step 4.2: Grading Service
- [ ] `app/services/grading_service.py`:
  - `assess_product(images, category, description)`:
    1. Upload images to S3
    2. Call Rekognition on each image
    3. Aggregate labels
    4. Call Bedrock with labels + context → get grade
    5. Store request + result in DynamoDB
    6. Return grading result

### Step 4.3: Grading Router
- [ ] `app/routers/grading.py`:
  - `POST /api/v1/grading/assess` — accept multipart images, orchestrate grading
  - `GET /api/v1/grading/{grading_id}` — fetch stored result

### Step 4.4: Test Grading
- [ ] Upload a test image via Swagger/curl
- [ ] Verify image lands in S3
- [ ] Verify Rekognition returns labels
- [ ] Verify Bedrock returns grade + explanation
- [ ] Verify full result stored in DynamoDB

---

## Phase 5: Core API — Return Prevention (1-2 hours)

### Step 5.1: Prevention Service
- [ ] `app/services/prevention_service.py`:
  - Load XGBoost model on import
  - `predict_return_risk(customer_id, product_id, context)`:
    1. Fetch customer profile from DynamoDB
    2. Fetch product signals from DynamoDB
    3. Engineer features
    4. Run XGBoost prediction → risk_score
    5. Get SHAP contributions → top_risk_factors
    6. Select interventions (rule-based)
    7. Store prediction in DynamoDB
    8. Return result

### Step 5.2: Prevention Router
- [ ] `app/routers/prevention.py`:
  - `POST /api/v1/prevention/score` — risk scoring
  - `GET /api/v1/prevention/product-signals/{product_id}` — product return info
  - `GET /api/v1/prevention/analytics` — aggregate stats

### Step 5.3: Seed Demo Data
- [ ] `scripts/seed_data.py`:
  - Seed 50-100 customer profiles into CustomerReturnProfiles table
  - Seed 100-200 product signals into ProductReturnSignals table
  - This gives the prevention API something to look up during demo

### Step 5.4: Test Prevention
- [ ] Score a customer-product pair
- [ ] Verify risk factors make sense (high-return-rate customer → high score)
- [ ] Verify interventions are selected appropriately

---

## Phase 6: Integration & End-to-End Flow (1-2 hours)

### Step 6.1: Wire Components Together
- [ ] After grading completes, auto-trigger routing decision
- [ ] Store grading → routing linkage (condition_grade flows into routing features)
- [ ] Add endpoint: `POST /api/v1/returns/process` — full pipeline:
  1. Accept return info + images
  2. Run grading → get condition
  3. Run routing (with condition) → get disposition route
  4. Return combined result

### Step 6.2: Add Health & Demo Endpoints
- [ ] `GET /health` — basic health check
- [ ] `GET /api/v1/demo/scenario` — returns pre-built demo data showing the full flow
- [ ] `GET /api/v1/stats` — aggregate counts from all tables

### Step 6.3: End-to-End Test
- [ ] Test full flow: prevention score → purchase → return → grading → routing
- [ ] Verify all DynamoDB entries chain together correctly

---

## Phase 7: Deploy to Render (30-60 min)

### Step 7.1: Prepare for Deployment
- [ ] Ensure `render.yaml` is in repo root
- [ ] Ensure `.env.example` documents all required vars
- [ ] Commit `trained_models/*.pkl` to git (small enough at 5MB)
- [ ] Add `.gitignore` (exclude `.env`, `venv/`, `__pycache__/`)
- [ ] Push to GitHub

### Step 7.2: Deploy on Render
- [ ] Go to Render Dashboard → New → Web Service
- [ ] Connect GitHub repo
- [ ] Configure:
  - Build command: `pip install -r requirements.txt`
  - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Plan: Free
- [ ] Add environment variables (AWS keys, bucket name, model ID)
- [ ] Deploy → wait for build
- [ ] Test live URL: `https://your-app.onrender.com/docs`

### Step 7.3: Verify Production
- [ ] Hit all endpoints on live URL
- [ ] Upload an image through live grading endpoint
- [ ] Confirm AWS services respond (DynamoDB writes, S3 uploads, Rekognition/Bedrock calls)

---

## Phase 8: Demo UI (Optional, 2-3 hours)

### Step 8.1: Quick Streamlit Frontend
- [ ] Create `demo_ui/app.py` using Streamlit
- [ ] Pages:
  - **Return Prevention**: Select customer + product → show risk score + interventions
  - **Quality Grading**: Upload image → show grade + defects + explanation
  - **Product Routing**: Submit return → show route decision with reasoning
  - **Full Flow**: End-to-end demo combining all three
- [ ] Deploy on Render (separate service) or Streamlit Cloud (free)

### Step 8.2: Alternative: Gradio on Hugging Face Spaces
- [ ] If Streamlit is too heavy, use Gradio (free hosting on HF Spaces)
- [ ] Image upload component → shows grading result
- [ ] Interactive demo with minimal code

---

## Phase 9: Polish & Presentation (1-2 hours)

### Step 9.1: README
- [ ] Project overview, architecture diagram
- [ ] Setup instructions
- [ ] API documentation link (FastAPI auto-docs)
- [ ] Demo video/screenshots

### Step 9.2: Presentation Deck (5-7 slides)
1. Problem: returns cost $X billion/year, waste, distrust
2. Solution: AI ecosystem for product second life
3. Architecture: AWS-native diagram (show DynamoDB, S3, Rekognition, Bedrock, Lambda)
4. Demo: live walkthrough of the three components
5. Impact metrics: projected return reduction %, cost savings, CO2 reduction
6. Scaling path: how this grows from demo → production with same AWS services
7. Future: peer-to-peer marketplace, green credits, recommendations

### Step 9.3: Demo Script
- [ ] Practice the demo flow (2-3 min):
  1. "Customer is browsing → risk score → intervention shown"
  2. "Customer returns item → uploads photo → AI grades condition"
  3. "System routes product to best destination → resell/refurbish/donate"
- [ ] Prepare fallback screenshots in case of cold-start delay

---

## Time Estimate Summary

| Phase | Time | Can Parallel? |
|-------|------|---------------|
| Phase 0: Setup | 30-60 min | No (prerequisite) |
| Phase 1: Skeleton | 1-2 hours | No (foundation) |
| Phase 2: ML Training | 2-3 hours | Yes (Colab while coding) |
| Phase 3: Routing API | 2-3 hours | Yes (after Phase 1) |
| Phase 4: Grading API | 2-3 hours | Yes (after Phase 1) |
| Phase 5: Prevention API | 1-2 hours | Yes (after Phase 1) |
| Phase 6: Integration | 1-2 hours | No (needs 3-5) |
| Phase 7: Deploy | 30-60 min | No (needs 6) |
| Phase 8: Demo UI | 2-3 hours | Yes (after Phase 7) |
| Phase 9: Polish | 1-2 hours | No (last) |

**Total: ~15-22 hours** (can be done in 2-3 days or compressed into an intense 24h hackathon)

**Critical path**: Phase 0 → 1 → (2,3,4,5 in parallel) → 6 → 7 → 9

**If time is tight, cut**:
- Phase 8 (Demo UI) — use Swagger/curl for demo instead
- Reduce Phase 2 to simpler models
- Skip the Lambda async path in Phase 4

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Bedrock access not approved | Fallback: use CLIP zero-shot locally (add `open-clip-torch` to requirements) |
| Render cold start (30s) | Pre-warm before demo; have screenshots ready |
| Model too large for 512MB RAM | LightGBM + XGBoost are tiny (~5MB each); only CLIP would be a problem |
| AWS free tier exceeded | Set CloudWatch billing alarm at $1; DynamoDB + Lambda are always-free |
| Rekognition bad results | Supplement with Bedrock vision (Claude can analyze images directly) |
| S3 CORS issues | Configure CORS on bucket creation; test upload from browser early |
