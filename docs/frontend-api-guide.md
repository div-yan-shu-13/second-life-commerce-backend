# Second Life Commerce — Frontend API Guide

## Base URL

```
Local:      http://localhost:8000
Production: https://second-life-commerce-api.onrender.com  (update once deployed)
```

CORS is fully open (`*`) — you can call from any frontend origin.

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

## Demo Data Available

These IDs are pre-seeded and ready to use:

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

**Good demo scenarios:**
- Low risk: `cust-005` + `prod-005`
- Medium risk: `cust-001` + `prod-003`
- High risk: `cust-002` + `prod-002`
- Very high risk: `cust-004` + `prod-004`

---

## Endpoint Details

---

### 1. Return Prevention — Score Risk

**`POST /api/v1/prevention/score`**

Call this when a user is browsing/adding to cart/checking out. Returns a risk score and suggested interventions to show them.

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
| context | string | yes | `"browse"`, `"cart_add"`, or `"checkout"` |

**Response:**
```json
{
  "prediction_id": "uuid-string",
  "risk_score": 0.4125,
  "risk_bucket": "medium",
  "top_risk_factors": [
    {
      "factor": "customer_return_rate",
      "contribution": 0.15,
      "detail": "Customer has a 38% return rate"
    },
    {
      "factor": "product_return_rate",
      "contribution": 0.18,
      "detail": "Product has a 45% return rate"
    }
  ],
  "recommended_interventions": [
    {
      "type": "size_recommendation",
      "priority": 1,
      "message": "Customers similar to you found this item runs small. Consider sizing up."
    },
    {
      "type": "review_highlight",
      "priority": 2,
      "message": "See what verified buyers say about this product's quality."
    }
  ]
}
```

**Response fields:**
| Field | Type | Description |
|-------|------|-------------|
| risk_score | float (0-1) | Higher = more likely to return |
| risk_bucket | string | `"low"` (<0.3), `"medium"` (0.3-0.6), `"high"` (>0.6) |
| top_risk_factors | array | Why this is risky (show as explanation) |
| recommended_interventions | array | What to show the user to prevent return |

**Frontend usage ideas:**
- Show a warning banner if `risk_bucket` is "high"
- Display intervention messages as helpful tips
- Show a risk meter/gauge visualization
- Color-code: green (low), yellow (medium), red (high)

---

### 2. Product Return Signals

**`GET /api/v1/prevention/product-signals/{product_id}`**

Get pre-computed return statistics for a product. Useful for product detail pages.

**Response:**
```json
{
  "product_id": "prod-002",
  "category": "clothing",
  "overall_return_rate": 0.35,
  "return_rate_by_reason": {
    "wrong_size": "0.25",
    "not_as_described": "0.10"
  },
  "size_issue_rate": 0.25,
  "avg_review_sentiment": 0.55,
  "description_completeness": 0.5,
  "common_complaints": ["runs small", "color differs from photo"]
}
```

**Frontend usage ideas:**
- Show "25% of buyers had size issues" on product page
- Display common complaints as heads-up
- Show a "return likelihood" badge

---

### 3. Prevention Analytics

**`GET /api/v1/prevention/analytics`**

Aggregated stats for a dashboard view.

**Response:**
```json
{
  "total_predictions": 42,
  "high_risk_count": 12,
  "interventions_shown": 8,
  "estimated_returns_prevented": 3
}
```

---

### 4. Quality Grading — Assess Product

**`POST /api/v1/grading/assess`**

Upload product images for AI-powered condition grading. This is the core feature — uses Gemini vision AI to analyze the product.

**Request:** `multipart/form-data`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| product_id | string | yes | Product being graded |
| product_category | string | yes | `"electronics"`, `"clothing"`, `"home"`, `"books"`, `"toys"` |
| images | File[] | yes | 1-5 image files (JPEG, PNG, WebP) |
| text_description | string | no | Optional seller/returner description |
| return_id | string | no | Link to a return event |

**JavaScript/fetch example:**
```javascript
const formData = new FormData();
formData.append('product_id', 'prod-001');
formData.append('product_category', 'electronics');
formData.append('images', fileInput.files[0]);  // File from <input type="file">
formData.append('text_description', 'Phone with cracked screen');

const response = await fetch(`${BASE_URL}/api/v1/grading/assess`, {
  method: 'POST',
  body: formData,
  // Do NOT set Content-Type header — browser sets it with boundary
});

const result = await response.json();
```

**Response:**
```json
{
  "grading_id": "858583bb-43f9-4336-8c83-ceaa7a17eee7",
  "overall_grade": "for_parts",
  "confidence": 0.95,
  "defects": [
    {
      "type": "screen_damage",
      "severity": "severe"
    }
  ],
  "explanation": "The smartphone has a severely cracked screen covering the entire display, making it largely unusable and suitable only for parts or recycling.",
  "image_urls": [
    "https://second-life-commerce-images.s3.amazonaws.com/grading/..."
  ],
  "processing_time_ms": 14330
}
```

**Response fields:**
| Field | Type | Description |
|-------|------|-------------|
| overall_grade | string | `"like_new"`, `"very_good"`, `"good"`, `"acceptable"`, `"for_parts"` |
| confidence | float (0-1) | Model confidence in the grade |
| defects | array | Detected issues with type and severity |
| explanation | string | AI-generated human-readable explanation |
| image_urls | array | Presigned S3 URLs of uploaded images (valid 1 hour) |
| processing_time_ms | int | How long AI analysis took |

**Defect types:** `scratch`, `dent`, `stain`, `crack`, `wear`, `missing_part`, `screen_damage`, `broken`

**Severity levels:** `minor`, `moderate`, `severe`

**Frontend usage ideas:**
- Drag-and-drop image upload zone
- Show grade as a colored badge (green→red scale)
- Display defects as a list with severity icons
- Show the AI explanation in a card
- Display uploaded image with the grade overlaid
- Progress spinner during the ~10-15 second processing time

**⚠️ Note:** This endpoint takes 10-15 seconds due to AI processing. Show a loading state.

---

### 5. Get Grading Result

**`GET /api/v1/grading/{grading_id}`**

Fetch a previously completed grading.

**Response:** Same format as assess response.

---

### 6. Product Routing — Decide Route

**`POST /api/v1/routing/decide`**

After grading, determine what to do with the product.

**Request:**
```json
{
  "return_id": "ret-001",
  "product_id": "prod-001",
  "return_reason": "defective",
  "product_category": "electronics",
  "original_price": 699.99,
  "product_age_days": 45,
  "condition_grade": "for_parts"
}
```

| Field | Type | Required | Values |
|-------|------|----------|--------|
| return_id | string | yes | Unique return identifier |
| product_id | string | yes | Product being returned |
| return_reason | string | yes | `"wrong_size"`, `"defective"`, `"not_as_described"`, `"no_longer_needed"`, `"better_price_found"` |
| product_category | string | yes | `"electronics"`, `"clothing"`, `"home"`, `"books"`, `"toys"` |
| original_price | float | yes | Original purchase price |
| product_age_days | int | yes | Days since purchase |
| condition_grade | string | no | From grading service: `"like_new"`, `"very_good"`, `"good"`, `"acceptable"`, `"for_parts"` |

**Response:**
```json
{
  "decision_id": "020bbe29-e79a-4673-ac74-c29077e35f3d",
  "route": "recycle",
  "confidence": 0.97,
  "estimated_recovery_usd": 35.0,
  "estimated_cost_usd": 1.0,
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

**Routes:**
| Route | Meaning | Icon suggestion |
|-------|---------|-----------------|
| `resell_as_is` | Sell directly on marketplace | 🏷️ |
| `refurbish` | Fix and sell as refurbished | 🔧 |
| `donate` | Donate to charity | 🎁 |
| `recycle` | Recycle materials | ♻️ |
| `peer_exchange` | Peer-to-peer resale | 🤝 |

**Frontend usage ideas:**
- Show route as a big colored card with icon
- Display confidence as a percentage bar
- Show estimated recovery vs cost (net value)
- Show reasoning factors as a simple chart
- If `requires_human_review: true`, show a "needs manual review" badge
- Animate the routing decision (like a sorting/flow animation)

---

### 7. Get Routing Decision

**`GET /api/v1/routing/decisions/{decision_id}`**

Fetch a previous routing decision.

---

### 8. Override Routing Decision

**`POST /api/v1/routing/decisions/{decision_id}/override`**

For admin/manual override of AI decisions.

**Request:**
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

## Full Demo Flow (Suggested UI Pages)

### Page 1: Return Prevention Dashboard
```
User selects customer → selects product → clicks "Check Risk"
→ Shows risk score gauge (0-100%)
→ Shows risk factors as cards
→ Shows recommended interventions as action items
```

### Page 2: Product Grading
```
User uploads product photo(s) → clicks "Analyze"
→ Loading spinner (10-15 sec)
→ Shows grade badge (like_new → for_parts)
→ Shows defects list
→ Shows AI explanation
→ Shows uploaded image
```

### Page 3: Product Routing
```
User fills return info OR auto-fills from grading
→ Clicks "Decide Route"
→ Shows animated routing decision
→ Shows route card with icon
→ Shows confidence + reasoning
→ Shows estimated $ recovery
→ Optional: Override button for admin
```

### Page 4: End-to-End Flow
```
Combines all 3 in sequence:
Prevention check → Purchase → Return → Grade → Route
Shows the full product lifecycle
```

### Page 5: Analytics Dashboard
```
Shows aggregate stats:
- Total predictions made
- Returns prevented
- Products routed by category (pie chart)
- Average confidence scores
```

---

## Error Handling

All endpoints return standard HTTP status codes:

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad request (invalid input) |
| 404 | Resource not found |
| 500 | Server error |

Error response format:
```json
{
  "detail": "Decision not found"
}
```

---

## Tips for Frontend Dev

1. **CORS is open** — no proxy needed, call the API directly from browser
2. **No auth required** — no tokens/headers needed (hackathon simplicity)
3. **Image upload** — use `FormData`, don't set Content-Type header manually
4. **Grading is slow** (~15 sec) — show a good loading state
5. **All IDs are UUIDs** — returned by creation endpoints, use them for fetches
6. **Presigned image URLs** expire after 1 hour — fetch fresh if displaying later
7. **Risk score is 0-1** — multiply by 100 for percentage display
8. **Render cold starts** — first request after 15 min inactivity takes ~30 sec

---

## Quick Test with curl

```bash
# Health check
curl http://localhost:8000/health

# Prevention score
curl -X POST http://localhost:8000/api/v1/prevention/score \
  -H "Content-Type: application/json" \
  -d '{"customer_id":"cust-002","product_id":"prod-004","context":"checkout"}'

# Routing decision
curl -X POST http://localhost:8000/api/v1/routing/decide \
  -H "Content-Type: application/json" \
  -d '{"return_id":"ret-001","product_id":"prod-001","return_reason":"defective","product_category":"electronics","original_price":699.99,"product_age_days":45,"condition_grade":"for_parts"}'

# Grading (with image file)
curl -X POST http://localhost:8000/api/v1/grading/assess \
  -F "product_id=prod-001" \
  -F "product_category=electronics" \
  -F "images=@broken_phone.png"
```
