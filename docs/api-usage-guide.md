# Second Life Commerce — Complete API Usage Guide

## Base URL

```
Local:      http://localhost:8000
Production: https://second-life-commerce-api.onrender.com
```

- CORS is fully open — call from any origin, no proxy needed
- No authentication required
- All responses are JSON (except grading which accepts multipart/form-data)
- **All prices are in ₹ (INR)** — built for Amazon India
- **Recovery/cost values are percentages** — multiply by `original_price / 100` to get ₹ amount
- Interactive docs at `{BASE_URL}/docs`

---

## Available Demo Data (Pre-seeded)

Use these IDs when testing — they're already in the database:

### Customers

| customer_id | Who | Return Rate | Behavior |
|-------------|-----|-------------|----------|
| `cust-001` | Good buyer | 8% | Rarely returns |
| `cust-002` | Clothing serial returner | 37.5% | Returns wrong-size clothing often |
| `cust-003` | Normal buyer | 10% | Occasional defective returns |
| `cust-004` | Heavy returner | 42% | Returns everything |
| `cust-005` | Perfect buyer | 0% | Has never returned anything |

### Products

| product_id | Category | Return Rate | Known Issues |
|------------|----------|-------------|--------------|
| `prod-001` | Electronics | 8% | Battery complaints |
| `prod-002` | Clothing | 35% | Runs small, color mismatch |
| `prod-003` | Home | 12% | Assembly instructions unclear |
| `prod-004` | Clothing | 45% | Sizes inconsistent, no size chart, feels cheap |
| `prod-005` | Electronics | 5% | Almost no issues (great product) |

---

## Endpoint 1: Score Return Risk

### `POST /api/v1/prevention/score`

**What it does:** Predicts how likely a customer is to return a specific product. Use this on product pages, cart, or checkout to show warnings/recommendations.

### Request

**Content-Type:** `application/json`

```json
{
  "customer_id": "cust-002",
  "product_id": "prod-004",
  "context": "checkout"
}
```

| Field | Type | Required | Description | Accepted Values |
|-------|------|----------|-------------|-----------------|
| `customer_id` | string | ✅ | The customer browsing/buying | Any string (use seeded IDs for demo) |
| `product_id` | string | ✅ | The product they're looking at | Any string (use seeded IDs for demo) |
| `context` | string | ✅ | Where in the funnel they are | `"browse"`, `"cart_add"`, `"checkout"` |

### Response

```json
{
  "prediction_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "risk_score": 0.4125,
  "risk_bucket": "medium",
  "top_risk_factors": [
    {
      "factor": "customer_return_rate",
      "contribution": 0.168,
      "detail": "Customer has a 42% return rate"
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
    },
    {
      "type": "return_rate_warning",
      "priority": 3,
      "message": "Heads up: 41% of similar purchases are returned."
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `prediction_id` | string (UUID) | Unique ID for this prediction |
| `risk_score` | float (0.0 - 1.0) | Higher = more likely to return. Multiply by 100 for percentage. |
| `risk_bucket` | string | `"low"` (< 0.3), `"medium"` (0.3 - 0.6), `"high"` (> 0.6) |
| `top_risk_factors` | array | Why this is risky — each factor has a name, contribution weight, and human-readable detail |
| `recommended_interventions` | array | What to show the user to prevent a return. Sorted by priority (1 = most important). |

### Intervention Types

| type | What to show |
|------|--------------|
| `size_recommendation` | Size guide, "runs small" warning |
| `review_highlight` | Relevant reviews about quality |
| `info_enrichment` | Additional product details |
| `return_rate_warning` | Direct warning about return likelihood |
| `comparison_nudge` | Suggest comparing with similar products |

### JavaScript Example

```javascript
async function getReturnRisk(customerId, productId, context) {
  const response = await fetch(`${BASE_URL}/api/v1/prevention/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer_id: customerId,
      product_id: productId,
      context: context  // 'browse', 'cart_add', or 'checkout'
    })
  });
  return await response.json();
}

// Usage
const result = await getReturnRisk('cust-002', 'prod-004', 'checkout');
console.log(`Risk: ${(result.risk_score * 100).toFixed(0)}%`);  // "Risk: 41%"
console.log(`Bucket: ${result.risk_bucket}`);  // "medium"
result.recommended_interventions.forEach(i => console.log(i.message));
```

### Demo Scenarios to Try

```javascript
// Low risk — good customer + good product
await getReturnRisk('cust-005', 'prod-005', 'browse');  // ~5-10% risk

// Medium risk — normal customer + problematic product
await getReturnRisk('cust-001', 'prod-002', 'cart_add');  // ~25-35% risk

// High risk — serial returner + terrible product
await getReturnRisk('cust-004', 'prod-004', 'checkout');  // ~50-70% risk
```

---

## Endpoint 2: Get Product Return Signals

### `GET /api/v1/prevention/product-signals/{product_id}`

**What it does:** Returns pre-computed return statistics for a product. Good for product detail pages.

### Request

No body needed. Just put the product_id in the URL.

```
GET /api/v1/prevention/product-signals/prod-002
```

### Response

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
  "common_complaints": ["runs small", "color differs from photo"],
  "last_updated": "2025-06-14T10:30:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `overall_return_rate` | float (0-1) | What % of buyers return this |
| `return_rate_by_reason` | object | Breakdown by reason |
| `size_issue_rate` | float | How often size is the problem |
| `avg_review_sentiment` | float (0-1) | 0 = negative reviews, 1 = positive |
| `description_completeness` | float (0-1) | How complete the listing info is |
| `common_complaints` | array of strings | Top customer complaints |

### JavaScript Example

```javascript
async function getProductSignals(productId) {
  const response = await fetch(`${BASE_URL}/api/v1/prevention/product-signals/${productId}`);
  if (response.status === 404) return null;
  return await response.json();
}

const signals = await getProductSignals('prod-002');
console.log(`Return rate: ${(signals.overall_return_rate * 100).toFixed(0)}%`);
console.log(`Complaints: ${signals.common_complaints.join(', ')}`);
```

### Error

Returns `404` if product_id not found:
```json
{ "detail": "Product signals not found" }
```

---

## Endpoint 3: Prevention Analytics

### `GET /api/v1/prevention/analytics`

**What it does:** Returns aggregate stats across all predictions. Use for a dashboard.

### Response

```json
{
  "total_predictions": 42,
  "high_risk_count": 12,
  "interventions_shown": 8,
  "estimated_returns_prevented": 3
}
```

### JavaScript Example

```javascript
async function getAnalytics() {
  const response = await fetch(`${BASE_URL}/api/v1/prevention/analytics`);
  return await response.json();
}
```

---

## Endpoint 4: Quality Grading — Assess Product

### `POST /api/v1/grading/assess`

**What it does:** Upload 1-5 product images and get an AI-powered condition grade. Uses computer vision to detect damage, scratches, cracks, etc.

**⚠️ Takes 10-15 seconds** — show a loading spinner.

### Request

**Content-Type:** `multipart/form-data` (NOT application/json)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_id` | string | ✅ | Which product is being graded |
| `product_category` | string | ✅ | Category for context: `"electronics"`, `"clothing"`, `"home"`, `"books"`, `"toys"` |
| `images` | File (1-5) | ✅ | Image files (JPEG, PNG, WebP). Max 5 files. |
| `text_description` | string | ❌ | Optional description from the person returning it |
| `return_id` | string | ❌ | Optional link to a return event |

### Response

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
    "https://second-life-commerce-images.s3.amazonaws.com/grading/858583bb.../0_broken_phone.png?..."
  ],
  "processing_time_ms": 14330
}
```

| Field | Type | Description |
|-------|------|-------------|
| `grading_id` | string (UUID) | Unique ID — use to fetch later |
| `overall_grade` | string | The condition grade (see table below) |
| `confidence` | float (0-1) | AI confidence in the grade |
| `defects` | array | List of detected defects |
| `explanation` | string | Human-readable AI explanation of the condition |
| `image_urls` | array | Presigned S3 URLs to view uploaded images (expire in 1 hour) |
| `processing_time_ms` | int | How long analysis took in milliseconds |

### Image Validation

The AI validates uploaded images before grading:
1. **Must be a product** — rejects landscapes, selfies, memes, food photos, etc.
2. **Must match category** — rejects a TV photo when `product_category` is "clothing"

**Error response (invalid image):**
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

**⚠️ Always check `if (result.error)` before displaying grade results.**

### Grade Scale

| Grade | Meaning | Color Suggestion |
|-------|---------|-----------------|
| `like_new` | Perfect, no wear, packaging intact | 🟢 Green |
| `very_good` | Minimal wear, minor imperfections | 🟢 Light green |
| `good` | Visible wear, functional, cosmetic issues | 🟡 Yellow |
| `acceptable` | Significant wear/damage, still functional | 🟠 Orange |
| `for_parts` | Major damage, not functional | 🔴 Red |

### Defect Object

```json
{
  "type": "screen_damage",   // what's wrong
  "severity": "severe"       // how bad
}
```

**Defect types:** `scratch`, `dent`, `stain`, `crack`, `wear`, `missing_part`, `screen_damage`, `broken`

**Severity:** `minor`, `moderate`, `severe`

### JavaScript Example

```javascript
async function gradeProduct(productId, category, imageFiles, description = '') {
  const formData = new FormData();
  formData.append('product_id', productId);
  formData.append('product_category', category);
  
  // imageFiles is a FileList from <input type="file" multiple>
  for (const file of imageFiles) {
    formData.append('images', file);
  }
  
  if (description) {
    formData.append('text_description', description);
  }

  const response = await fetch(`${BASE_URL}/api/v1/grading/assess`, {
    method: 'POST',
    body: formData,
    // ⚠️ Do NOT set Content-Type header! Browser sets it automatically with boundary.
  });
  
  return await response.json();
}

// Usage with file input
const fileInput = document.getElementById('product-images');
const result = await gradeProduct('prod-001', 'electronics', fileInput.files, 'Cracked screen phone');

console.log(`Grade: ${result.overall_grade}`);       // "for_parts"
console.log(`Confidence: ${result.confidence}`);     // 0.95
console.log(`Explanation: ${result.explanation}`);   // "The smartphone has a severely..."
```

### React Example

```jsx
function GradingForm() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const formData = new FormData(e.target);
    const response = await fetch(`${BASE_URL}/api/v1/grading/assess`, {
      method: 'POST',
      body: formData,
    });
    
    setResult(await response.json());
    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="hidden" name="product_id" value="prod-001" />
      <input type="hidden" name="product_category" value="electronics" />
      <input type="file" name="images" accept="image/*" multiple required />
      <input type="text" name="text_description" placeholder="Describe condition..." />
      <button type="submit" disabled={loading}>
        {loading ? 'Analyzing... (10-15 sec)' : 'Grade Product'}
      </button>
      
      {result && (
        <div>
          <h3>Grade: {result.overall_grade}</h3>
          <p>Confidence: {(result.confidence * 100).toFixed(0)}%</p>
          <p>{result.explanation}</p>
          {result.defects.map((d, i) => (
            <span key={i}>{d.type} ({d.severity})</span>
          ))}
        </div>
      )}
    </form>
  );
}
```

### Error Cases

| Status | Cause |
|--------|-------|
| 400 | More than 5 images, or non-image file uploaded |
| 500 | AI service error (rare) — response will still have fallback grade |

---

## Endpoint 5: Get Previous Grading

### `GET /api/v1/grading/{grading_id}`

**What it does:** Fetch a grading result that was computed earlier.

### Response

Same format as the assess endpoint response.

### JavaScript Example

```javascript
async function getGrading(gradingId) {
  const response = await fetch(`${BASE_URL}/api/v1/grading/${gradingId}`);
  if (response.status === 404) return null;
  return await response.json();
}
```

---

## Endpoint 6: Route a Returned Product

### `POST /api/v1/routing/decide`

**What it does:** Takes return information (+ optional condition grade from grading) and decides the optimal next step: resell, refurbish, donate, recycle, or peer exchange.

### Request

**Content-Type:** `application/json`

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

| Field | Type | Required | Description | Accepted Values |
|-------|------|----------|-------------|-----------------|
| `return_id` | string | ✅ | Unique ID for this return | Any string/UUID |
| `product_id` | string | ✅ | Product being returned | Any string |
| `return_reason` | string | ✅ | Why they're returning it | `"wrong_size"`, `"defective"`, `"not_as_described"`, `"no_longer_needed"`, `"better_price_found"` |
| `product_category` | string | ✅ | Product category | `"electronics"`, `"clothing"`, `"home"`, `"books"`, `"toys"` |
| `original_price` | float | ✅ | How much it cost (₹ INR) | Any positive number |
| `product_age_days` | int | ✅ | Days since purchase | Any positive integer |
| `condition_grade` | string | ❌ | From grading endpoint | `"like_new"`, `"very_good"`, `"good"`, `"acceptable"`, `"for_parts"` |

### Response

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
| `decision_id` | string (UUID) | Unique ID for this decision |
| `route` | string | The recommended action (see table below) |
| `confidence` | float (0-1) | How confident the AI is |
| `estimated_recovery_pct` | float | % of original price that can be recovered. Calculate ₹: `price × pct / 100` |
| `estimated_cost_pct` | float | % of original price as processing cost. Calculate ₹: `price × pct / 100` |
| `reasoning.method` | string | `"ml_model"` or `"rule_based"` |
| `reasoning.top_factors` | array | Which features drove the decision |
| `requires_human_review` | boolean | `true` if confidence < 60% |

### Route Options

| Route | Meaning | When | Icon |
|-------|---------|------|------|
| `resell_as_is` | Sell on marketplace directly | Good condition, high demand | 🏷️ |
| `refurbish` | Repair then sell as refurbished | Fixable damage, worth the cost | 🔧 |
| `donate` | Give to charity/non-profit | Low value, decent condition | 🎁 |
| `recycle` | Salvage materials/components | Major damage, low value | ♻️ |
| `peer_exchange` | Enable peer-to-peer resale | Medium condition, niche product | 🤝 |

### JavaScript Example

```javascript
async function routeProduct(returnData) {
  const response = await fetch(`${BASE_URL}/api/v1/routing/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(returnData)
  });
  return await response.json();
}

// Example: expensive phone, heavily damaged
const result = await routeProduct({
  return_id: 'ret-001',
  product_id: 'prod-001',
  return_reason: 'defective',
  product_category: 'electronics',
  original_price: 55000,
  product_age_days: 45,
  condition_grade: 'for_parts'   // from grading endpoint
});

console.log(`Route: ${result.route}`);           // "recycle"
console.log(`Confidence: ${result.confidence}`); // 0.97
console.log(`Recovery: ${result.estimated_recovery_pct}%`);  // "5%"
console.log(`Cost: ${result.estimated_cost_pct}%`);          // "0.15%"
// Calculate actual INR values
const price = 55000;
console.log(`Recovery ₹: ${price * result.estimated_recovery_pct / 100}`);
console.log(`Cost ₹: ${price * result.estimated_cost_pct / 100}`);
console.log(`Net ₹: ${price * (result.estimated_recovery_pct - result.estimated_cost_pct) / 100}`);
```

### Demo Scenarios

```javascript
// Like-new expensive electronics → resell_as_is
await routeProduct({
  return_id: 'demo-1', product_id: 'prod-001',
  return_reason: 'no_longer_needed', product_category: 'electronics',
  original_price: 42000, product_age_days: 7, condition_grade: 'like_new'
});

// Damaged but fixable electronics → refurbish
await routeProduct({
  return_id: 'demo-2', product_id: 'prod-001',
  return_reason: 'defective', product_category: 'electronics',
  original_price: 25000, product_age_days: 30, condition_grade: 'acceptable'
});

// Cheap book, good condition → donate
await routeProduct({
  return_id: 'demo-3', product_id: 'prod-001',
  return_reason: 'no_longer_needed', product_category: 'books',
  original_price: 350, product_age_days: 60, condition_grade: 'good'
});

// Destroyed phone → recycle
await routeProduct({
  return_id: 'demo-4', product_id: 'prod-001',
  return_reason: 'defective', product_category: 'electronics',
  original_price: 55000, product_age_days: 45, condition_grade: 'for_parts'
});
```

---

## Endpoint 7: Get Previous Routing Decision

### `GET /api/v1/routing/decisions/{decision_id}`

### Response

Returns the full stored decision object.

### JavaScript Example

```javascript
async function getDecision(decisionId) {
  const response = await fetch(`${BASE_URL}/api/v1/routing/decisions/${decisionId}`);
  if (response.status === 404) return null;
  return await response.json();
}
```

---

## Endpoint 8: Override Routing Decision

### `POST /api/v1/routing/decisions/{decision_id}/override`

**What it does:** Allows an admin/human to override the AI's routing decision.

### Request

```json
{
  "new_route": "refurbish",
  "reason": "Product can be cheaply repaired and resold"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `new_route` | string | ✅ | New route to assign | 
| `reason` | string | ✅ | Why the override is happening |

### Response

```json
{
  "decision_id": "020bbe29-...",
  "original_route": "recycle",
  "new_route": "refurbish",
  "status": "overridden"
}
```

### JavaScript Example

```javascript
async function overrideDecision(decisionId, newRoute, reason) {
  const response = await fetch(`${BASE_URL}/api/v1/routing/decisions/${decisionId}/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_route: newRoute, reason: reason })
  });
  return await response.json();
}
```

---

## Endpoint 9: Health Check

### `GET /health`

```json
{ "status": "healthy" }
```

### `GET /`

```json
{
  "service": "Second Life Commerce API",
  "version": "1.0.0",
  "status": "healthy",
  "endpoints": {
    "routing": "/api/v1/routing/decide",
    "grading": "/api/v1/grading/assess",
    "prevention": "/api/v1/prevention/score",
    "docs": "/docs"
  }
}
```

---

## Complete End-to-End Flow Example

Here's how all three components connect in a real scenario:

```javascript
// ====== STEP 1: Customer is browsing ======
// Check if this purchase is risky
const riskResult = await fetch(`${BASE_URL}/api/v1/prevention/score`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    customer_id: 'cust-002',
    product_id: 'prod-002',
    context: 'browse'
  })
}).then(r => r.json());

// Show interventions if risk is medium/high
if (riskResult.risk_bucket !== 'low') {
  // Display: "Customers similar to you found this runs small..."
  showInterventions(riskResult.recommended_interventions);
}


// ====== STEP 2: Customer bought it and now wants to return ======
// They upload a photo of the product
const formData = new FormData();
formData.append('product_id', 'prod-002');
formData.append('product_category', 'clothing');
formData.append('images', photoFile);
formData.append('text_description', 'Shirt has a stain on the front');

const gradingResult = await fetch(`${BASE_URL}/api/v1/grading/assess`, {
  method: 'POST',
  body: formData
}).then(r => r.json());

// Show: "Grade: acceptable, Defects: stain (moderate)"
showGrade(gradingResult);


// ====== STEP 3: Route the product to its next life ======
const routingResult = await fetch(`${BASE_URL}/api/v1/routing/decide`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    return_id: 'ret-12345',
    product_id: 'prod-002',
    return_reason: 'not_as_described',
    product_category: 'clothing',
    original_price: 3500,
    product_age_days: 14,
    condition_grade: gradingResult.overall_grade  // "acceptable"
  })
}).then(r => r.json());

// Show: "Route: donate ♻️ (confidence: 72%)"
showRoutingDecision(routingResult);
```

---

## Error Handling

```javascript
async function apiCall(url, options = {}) {
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (err) {
    if (err.message === 'Failed to fetch') {
      // Server is cold-starting (wait 30 sec on first request after idle)
      throw new Error('Server warming up, please try again in 30 seconds');
    }
    throw err;
  }
}
```

---

## Important Notes

1. **Grading takes 10-15 seconds** — always show a loading state
2. **First request after idle takes ~30 seconds** — server wakes up (keep-alive should prevent this but just in case)
3. **Image URLs expire after 1 hour** — if displaying grading results later, re-fetch them
4. **No pagination** — analytics endpoint returns all data (fine for hackathon scale)
5. **IDs are UUIDs** — generated server-side, returned in creation responses
6. **Condition grade flows between endpoints** — grading output → routing input
7. **All number responses are JSON numbers** — no string conversion needed
