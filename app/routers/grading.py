from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional, List

from app.services.grading_service import assess_product, get_grading_result

router = APIRouter(prefix="/api/v1/grading", tags=["Quality Grading"])


@router.post("/assess")
async def grading_assess(
    product_id: str = Form(...),
    product_category: str = Form(...),
    images: List[UploadFile] = File(...),
    text_description: Optional[str] = Form(None),
    return_id: Optional[str] = Form(None),
):
    """
    Upload product images for AI-powered quality grading.
    Uses Amazon Rekognition + Bedrock for condition assessment.
    """
    if len(images) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 images allowed")

    for img in images:
        if not img.content_type or not img.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {img.content_type}. Only images allowed.",
            )

    result = await assess_product(
        product_id=product_id,
        product_category=product_category,
        image_files=images,
        text_description=text_description or "",
        return_id=return_id,
    )
    return result


@router.get("/{grading_id}")
def grading_get_result(grading_id: str):
    """Fetch a grading result by ID."""
    result = get_grading_result(grading_id)
    if not result:
        raise HTTPException(status_code=404, detail="Grading result not found")
    return result
