"""
Vision grading using Google Gemini API (free tier).
Bedrock was throttled on free AWS accounts, so we use Gemini as the
primary vision model. Still stores data in AWS (S3 + DynamoDB).
"""
import json
import re
import google.generativeai as genai
from PIL import Image
import io
from app.config import settings

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)


def grade_product_with_image(
    image_bytes: bytes,
    product_category: str,
    text_description: str = "",
    content_type: str = "image/jpeg",
) -> dict:
    """
    Send image to Gemini for product condition grading.
    Free tier: 15 RPM, 1500 requests/day — plenty for hackathon.
    """
    prompt = """You are a product condition grading expert for a sustainable commerce platform.
Look at this product image carefully and assess its physical condition.

Product category: {category}
Seller/returner description: {description}

Grade this product on the following scale:
- like_new: Perfect condition, no visible wear, original packaging intact
- very_good: Minimal wear, fully functional, very minor cosmetic imperfections
- good: Some visible wear, fully functional, noticeable cosmetic issues
- acceptable: Significant wear or damage, still functional
- for_parts: Major damage, not fully functional, suitable only for parts/recycling

Look carefully for: scratches, dents, cracks, stains, missing parts, screen damage, scuffs, discoloration, broken components.

Respond ONLY with valid JSON, no markdown, no code blocks, just the JSON object:
{{"grade": "one of: like_new, very_good, good, acceptable, for_parts", "confidence": 0.85, "defects": [{{"type": "scratch or dent or stain or crack or wear or missing_part or screen_damage or broken", "severity": "minor or moderate or severe"}}], "explanation": "Brief explanation of what you see in the image"}}""".format(
        category=product_category,
        description=text_description or "No description provided",
    )

    # Convert bytes to PIL Image for Gemini
    image = Image.open(io.BytesIO(image_bytes))

    model = genai.GenerativeModel("models/gemini-2.5-flash")

    response = model.generate_content(
        [prompt, image],
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=1024,
        ),
    )

    result_text = response.text
    return _parse_grading_response(result_text)


def grade_product_condition(
    rekognition_labels: list,
    product_category: str,
    text_description: str = "",
) -> dict:
    """
    Text-only grading using Gemini (no image, just labels).
    Fallback when image bytes aren't available.
    """
    labels_text = ", ".join(
        [f"{l['Name']} ({l['Confidence']:.0f}%)" for l in rekognition_labels]
    )

    prompt = f"""You are a product condition grading expert.
Analyze the following detected labels from a returned product image.

Product category: {product_category}
Detected visual labels: {labels_text}
Seller description: {text_description or 'No description provided'}

Grade this product. Respond ONLY with valid JSON, no markdown:
{{"grade": "one of: like_new, very_good, good, acceptable, for_parts", "confidence": 0.85, "defects": [{{"type": "scratch or dent or stain or crack or wear or missing_part", "severity": "minor or moderate or severe"}}], "explanation": "Brief explanation"}}"""

    model = genai.GenerativeModel("models/gemini-2.5-flash")
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=1024,
        ),
    )
    return _parse_grading_response(response.text)


def _parse_grading_response(result_text: str) -> dict:
    """Parse JSON response from the model."""
    # Clean up common issues
    result_text = result_text.strip()

    # Try direct JSON parse
    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try extracting any JSON object
    json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Last resort
    return {
        "grade": "good",
        "confidence": 0.5,
        "defects": [],
        "explanation": f"Could not parse model response. Raw: {result_text[:200]}",
    }
