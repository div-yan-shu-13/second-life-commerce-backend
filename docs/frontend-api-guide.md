# Second Life Commerce — Frontend API Guide

## Base URL

```
Local:      http://localhost:8000
Production: https://second-life-commerce-api.onrender.com  (update once deployed)
```

CORS is fully open (`*`) — call from any frontend origin, no proxy needed, no auth required.

## Interactive API Docs

Visit `{BASE_URL}/docs` for Swagger UI with try-it-out functionality.

---

## Overview of Endpoints

| # | Endpoint | Method | Purpose |
|---|----------|--------|---------|
| 1 | `/api/v1/prevention/score` | POST | Get return risk score before purchase |
| 2 | `/api/v1/prevention/product-signals/{product_id}` | GET | Get product return stats |
| 3 | `/api/v1/prevention/analytics` | GET | Dashboard analytics |
| 4 | `/api/v1/grading/assess` | POST | Upload images → get AI condition grade |
| 5 | `/api/v1/grading/{grading_id}` | GET | Fetch a previous grading result |
| 6 | `/api/v1/routing/decide` | POST | Route a returned product |
| 7 | `/api/v1/routing/decisions/{decision_id}` | GET | Fetch a routing decision |
| 8 | `/api/v1/routing/decisions/{decision_id}/override` | POST | Override a routing decision |
| 9 | `/health` | GET | Health check |

---

## Demo Data (Pre-seeded)

**Customers:**
| customer_id | Profile | Return Rate |
|-------------|---------|-------------|
| `cust-001` | Good customer | 8% |
| `cust-002` | Serial returner (clothing) | 37.5% |
| `cust-003` | Normal customer | 10% |
| `cust-004` | Heavy returner | 42% |
| `cust-005` | Perfect customer, never returns | 0% |

**Products:**
| product_id | Category | Return Rate | Issues |
|------------|----------|-------------|--------|
| `prod-001` | Electronics | 8% | Battery complaints |
| `prod-002` | Clothing | 35% | Runs small, color mismatch |
| `prod-003` | Home | 12% | Assembly instructions |
| `prod-004` | Clothing | 45% | Inconsistent sizing, no size chart |
| `prod-005` | Electronics | 5% | Almost no issues |

**Demo scenarios:**
- Low risk: `cust-005` + `prod-005`
- High risk: `cust-004` + `prod-004`

---

## Endpoint 1: Score Return Risk

**`POST /api/v1/prevention/score`**

**Request:**
```json
{
  "customer_id": "cust-002",
  "product_id": "prod-004",
  "context": "checkout"
}
```

| Field | Type | Required | Values |
|-------|------|----------|--------|
| customer_id | string | yes | Any customer ID |
| product_id | string | yes | Any product ID |
| context | string | yes | `"browse"`, `"cart_add"`, `"checkout"` |

**Response:**
```json
{
  "prediction_id": "uuid-string",
  "risk_score": 0.4125,
  "risk_bucket": "medium",
  "top_risk_factors": [
    { "factor": "customer_return_rate", "contribution": 0.15, "detail": "Customer has a 42% return rate" },
    { "factor": "product_return_rate", "contribution": 0.18, "detail": "Product has a 45% return rate" }
  ],
  "recommended_interventions": [
    { "type": "size_recommendation", "priority": 1, "message": "Customers similar to you found this item runs small. Consider sizing up." },
    { "type": "review_highlight", "priority": 2, "message": "See what verified buyers say about this product's quality." }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| risk_score | float (0-1) | Multiply by 100 for percentage |
| risk_bucket | `"low"` / `"medium"` / `"high"` | Thresholds: <0.3 / 0.3-0.6 / >0.6 |
| recommended_interventions | array | Sorted by priority (1 = most important) |

---

## Endpoint 2: Product Return Signals

**`GET /api/v1/prevention/product-signals/{product_id}`**

**Response:**
```json
{
  "product_id": "prod-002",
  "category": "clothing",
  "overall_return_rate": 0.35,
  "return_rate_by_reason": { "wrong_size": "0.25", "not_as_described": "0.10" },
  "size_issue_rate": 0.25,
  "avg_review_sentiment": 0.55,
  "description_completeness": 0.5,
  "common_complaints": ["runs small", "color differs from photo"]
}
```

Returns `404` if product not found.

---

## Endpoint 3: Prevention Analytics

**`GET /api/v1/prevention/analytics`**

```json
{
  "total_predictions": 42,
  "high_risk_count": 12,
  "interventions_shown": 8,
  "estimated_returns_prevented": 3
}
```

---

## Endpoint 4: Quality Grading

**`POST /api/v1/grading/assess`**

Upload product images for AI condition grading (uses Google Gemini vision).

**⚠️ Takes 10-15 seconds — show a loading spinner.**

**Request:** `multipart/form-data`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| product_id | string | yes | Product being graded |
| product_category | string | yes | `"electronics"`, `"clothing"`, `"home"`, `"books"`, `"toys"` |
| images | File (1-5) | yes | Image files (JPEG, PNG, WebP) |
| text_description | string | no | Optional description of the item |
| return_id | string | no | Link to a return event |

**Success Response:**
```json
{
  "grading_id": "858583bb-43f9-4336-8c83-ceaa7a17eee7",
  "overall_grade": "for_parts",
  "confidence": 0.95,
  "defects": [
    { "type": "screen_damage", "severity": "severe" }
  ],
  "explanation": "The smartphone has a severely cracked screen covering the entire display.",
  "image_urls": ["https://...s3.amazonaws.com/grading/..."],
  "processing_time_ms": 14330
}
```

**Error Response (invalid image — not a product, or wrong category):**
```json
{
  "grading_id": "...",
  "error": true,
  "overall_grade": null,
  "confidence": 0.0,
  "defects": [],
  "explanation": "Image does not appear to show a product. Please upload a clear photo of the item you are returning.",
  "image_urls": ["..."],
  "processing_time_ms": 3000
}
```

**⚠️ Check `if (result.error)` before displaying grade results.**

The AI validates:
1. Image must show a physical product (rejects landscapes, selfies, memes, etc.)
2. Product must match the selected category (rejects TV photo when category is "clothing")

**Grade scale:**
| Grade | Meaning | Color |
|-------|---------|-------|
| `like_new` | Perfect condition | 🟢 Green |
| `very_good` | Minimal wear | 🟢 Light green |
| `good` | Visible wear, functional | 🟡 Yellow |
| `acceptable` | Significant damage, functional | 🟠 Orange |
| `for_parts` | Major damage, not functional | 🔴 Red |

**Defect types:** `scratch`, `dent`, `stain`, `crack`, `wear`, `missing_part`, `screen_damage`, `broken`
**Severity:** `minor`, `moderate`, `severe`

---

## Endpoint 5: Get Previous Grading

**`GET /api/v1/grading/{grading_id}`**

Same response format as above.

---

## Endpoint 6: Route a Returned Product

**`POST /api/v1/routing/decide`**

**Request:**
```json
{
  "return_id": "ret-001",
  "product_id": "prod-001",
  "return_reason": "defective",
  "product_category": "electronics",
  "original_price": 55000.0,
  "product_age_days": 45,
  "condition_grade": "for_parts"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| return_id | string | yes | Unique return identifier |
| product_id | string | yes | Product being returned |
| return_reason | string | yes | `"wrong_size"`, `"defective"`, `"not_as_described"`, `"no_longer_needed"`, `"better_price_found"` |
| product_category | string | yes | `"electronics"`, `"clothing"`, `"home"`, `"books"`, `"toys"` |
| original_price | float | yes | Original price in ₹ (INR) |
| product_age_days | int | yes | Days since purchase |
| condition_grade | string | no | From grading endpoint |

**Response:**
```json
{
  "decision_id": "020bbe29-e79a-4673-ac74-c29077e35f3d",
  "route": "recycle",
  "confidence": 0.97,
  "estimated_recovery_pct": 5.0,
  "estimated_cost_pct": 0.15,
  "reasoning": {
    "method": "ml_model",
    "top_factors": [
      { "feature": "age_days", "importance": 8757 },
      { "feature": "price", "importance": 7330 },
      { "feature": "resale_estimate", "importance": 6192 }
    ]
  },
  "requires_human_review": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| route | string | Recommended action (see table below) |
| confidence | float (0-1) | AI confidence |
| estimated_recovery_pct | float | % of original price recovered. Calculate ₹ value: `price × recovery_pct / 100` |
| estimated_cost_pct | float | % of original price as processing cost. Calculate ₹ value: `price × cost_pct / 100` |
| requires_human_review | boolean | `true` if confidence < 60% |

**Recovery/Cost calculation example:**
- Product price: ₹55,000
- `estimated_recovery_pct`: 75.0 → Recovery = ₹55,000 × 75/100 = **₹41,250**
- `estimated_cost_pct`: 1.0 → Cost = ₹55,000 × 1/100 = **₹550**
- Net value = ₹41,250 - ₹550 = **₹40,700**

**Routes:**
| Route | Meaning | Typical Recovery % | Icon |
|-------|---------|-------------------|------|
| `resell_as_is` | Sell on marketplace directly | 75% | 🏷️ |
| `refurbish` | Repair then sell as refurbished | 55% | 🔧 |
| `peer_exchange` | Peer-to-peer resale | 60% | 🤝 |
| `donate` | Give to charity | 0% | 🎁 |
| `recycle` | Salvage materials | 5% | ♻️ |

---

## Endpoint 7: Get Routing Decision

**`GET /api/v1/routing/decisions/{decision_id}`**

Returns the stored decision. Same fields as above.

---

## Endpoint 8: Override Routing Decision

**`POST /api/v1/routing/decisions/{decision_id}/override`**

```json
{
  "new_route": "refurbish",
  "reason": "Product can be repaired cheaply"
}
```

**Response:**
```json
{
  "decision_id": "020bbe29-...",
  "original_route": "recycle",
  "new_route": "refurbish",
  "status": "overridden"
}
```

---

## Full End-to-End Flow

```
1. Customer browses → POST /prevention/score → show interventions if high risk
2. Customer returns → POST /grading/assess (upload photo) → show grade
3. System routes   → POST /routing/decide (pass grade) → show route + recovery %
```

---

## Important Notes

1. **All prices are in ₹ (INR)** — this is built for Amazon India
2. **Recovery/cost are percentages** — multiply by price/100 to get ₹ amount
3. **Grading validates images** — rejects non-product photos and wrong-category items
4. **Grading takes 10-15 sec** — always show a loading state
5. **Image URLs expire after 1 hour** — re-fetch grading result if needed later
6. **CORS is open** — no proxy or auth needed
7. **First request after idle ~30 sec** — keep-alive should prevent this
