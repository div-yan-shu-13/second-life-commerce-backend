import uuid
import time
from datetime import datetime, timezone
from decimal import Decimal

from app.aws.s3 import upload_image, get_presigned_url
from app.aws.rekognition import detect_labels
from app.aws.bedrock import grade_product_with_image
from app.aws.dynamodb import put_item, get_item
from app.config import settings


async def assess_product(
    product_id: str,
    product_category: str,
    image_files: list,
    text_description: str = "",
    return_id: str = None,
) -> dict:
    """
    Full grading pipeline:
    1. Read image bytes
    2. Upload images to S3
    3. Send actual image to Bedrock (Claude vision) for grading
    4. Optionally run Rekognition for extra labels
    5. Store results in DynamoDB
    """
    grading_id = str(uuid.uuid4())
    start_time = time.time()

    # Step 1: Read image bytes and upload to S3
    image_keys = []
    first_image_bytes = None
    first_content_type = "image/jpeg"

    for i, image_file in enumerate(image_files):
        file_bytes = await image_file.read()
        if i == 0:
            first_image_bytes = file_bytes
            first_content_type = image_file.content_type or "image/jpeg"
        s3_key = f"grading/{grading_id}/{i}_{image_file.filename}"
        upload_image(file_bytes, s3_key, image_file.content_type or "image/jpeg")
        image_keys.append(s3_key)

    # Step 2: Grade using Gemini vision (sends actual image)
    grading_result = None
    is_invalid_image = False

    if settings.USE_BEDROCK and first_image_bytes:
        try:
            grading_result = grade_product_with_image(
                image_bytes=first_image_bytes,
                product_category=product_category,
                text_description=text_description,
                content_type=first_content_type,
            )
            # Check if Gemini flagged this as not a product image
            if grading_result and grading_result.get("error"):
                is_invalid_image = True
        except Exception as e:
            print(f"Gemini vision error: {e}")

    # Step 3: Fallback to Rekognition-based grading if Bedrock failed
    if grading_result is None:
        all_labels = []
        for key in image_keys:
            try:
                labels = detect_labels(key)
                all_labels.extend(labels)
            except Exception as e:
                print(f"Rekognition error for {key}: {e}")

        # Deduplicate labels
        seen = {}
        for label in all_labels:
            name = label["Name"]
            if name not in seen or label["Confidence"] > seen[name]["Confidence"]:
                seen[name] = label
        unique_labels = list(seen.values())
        grading_result = _fallback_grading(unique_labels)

    processing_time_ms = int((time.time() - start_time) * 1000)

    # If image was flagged as not a product, return error response
    if is_invalid_image:
        image_urls = [get_presigned_url(key) for key in image_keys]
        return {
            "grading_id": grading_id,
            "error": True,
            "overall_grade": None,
            "confidence": 0.0,
            "defects": [],
            "explanation": grading_result.get("message", "Image does not appear to show a product. Please upload a clear photo of the item you are returning."),
            "image_urls": image_urls,
            "processing_time_ms": processing_time_ms,
        }

    # Step 4: Store in DynamoDB
    now = datetime.now(timezone.utc).isoformat()

    request_item = {
        "grading_id": grading_id,
        "return_id": return_id or "none",
        "product_id": product_id,
        "product_category": product_category,
        "image_keys": image_keys,
        "text_description": text_description or "",
        "status": "completed",
        "created_at": now,
    }
    put_item("GradingRequests", request_item)

    result_item = {
        "grading_id": grading_id,
        "overall_grade": grading_result.get("grade", "good"),
        "overall_confidence": Decimal(str(round(grading_result.get("confidence", 0.5), 4))),
        "model_version": "bedrock_vision_v1" if settings.USE_BEDROCK else "rekognition_fallback_v1",
        "defects": grading_result.get("defects", []),
        "grade_explanation": grading_result.get("explanation", ""),
        "processing_time_ms": processing_time_ms,
        "created_at": now,
    }
    put_item("GradingResults", result_item)

    # Generate presigned URLs for images
    image_urls = [get_presigned_url(key) for key in image_keys]

    return {
        "grading_id": grading_id,
        "overall_grade": grading_result.get("grade", "good"),
        "confidence": grading_result.get("confidence", 0.5),
        "defects": grading_result.get("defects", []),
        "explanation": grading_result.get("explanation", ""),
        "image_urls": image_urls,
        "processing_time_ms": processing_time_ms,
    }


def get_grading_result(grading_id: str) -> dict:
    """Fetch a grading result by ID."""
    result = get_item("GradingResults", {"grading_id": grading_id})
    if not result:
        return None
    request = get_item("GradingRequests", {"grading_id": grading_id})
    image_urls = []
    if request and request.get("image_keys"):
        image_urls = [get_presigned_url(key) for key in request["image_keys"]]
    result["image_urls"] = image_urls
    return result


def _fallback_grading(labels: list) -> dict:
    """Rule-based grading from Rekognition labels when Bedrock is unavailable."""
    label_names = [l["Name"].lower() for l in labels]

    damage_keywords = ["scratch", "dent", "crack", "stain", "damage", "broken",
                       "worn", "torn", "chipped", "bent", "rust", "corrosion",
                       "shattered", "cracked screen", "missing"]
    good_keywords = ["new", "clean", "pristine", "sealed", "unopened", "mint"]

    damage_count = sum(1 for name in label_names if any(kw in name for kw in damage_keywords))
    good_count = sum(1 for name in label_names if any(kw in name for kw in good_keywords))

    defects = []

    if damage_count == 0 and good_count > 0:
        grade = "like_new"
        confidence = 0.6
    elif damage_count == 0:
        grade = "good"  # Can't confirm like_new without positive signals
        confidence = 0.5
    elif damage_count == 1:
        grade = "good"
        confidence = 0.55
        defects = [{"type": "wear", "severity": "minor"}]
    elif damage_count == 2:
        grade = "acceptable"
        confidence = 0.5
        defects = [{"type": "damage", "severity": "moderate"}]
    else:
        grade = "for_parts"
        confidence = 0.5
        defects = [{"type": "damage", "severity": "severe"}]

    return {
        "grade": grade,
        "confidence": confidence,
        "defects": defects,
        "explanation": f"Fallback grading: detected {len(labels)} labels, "
                       f"{damage_count} damage indicators, {good_count} positive indicators. "
                       f"Note: For accurate grading, Bedrock vision analysis is recommended.",
    }
