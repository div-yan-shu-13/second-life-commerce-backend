"""
Vision grading using Google Gemini API (free tier).
Bedrock was throttled on free AWS accounts, so we use Gemini as the
primary vision model. Still stores data in AWS (S3 + DynamoDB).
Supports two API keys for failover when daily limits are hit.
"""
import json
import re
import google.generativeai as genai
from PIL import Image
import io
from app.config import settings

# Track which key is active
_active_key_index = 0


def _get_api_keys():
    keys = [settings.GEMINI_API_KEY]
    if settings.GEMINI_API_KEY_2:
        keys.append(settings.GEMINI_API_KEY_2)
    return keys


def _configure_gemini(key_index: int = 0):
    """Configure Gemini with the specified key."""
    keys = _get_api_keys()
    if key_index < len(keys):
        genai.configure(api_key=keys[key_index])


# Configure with primary key on startup
_configure_gemini(0)


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

FIRST: Validate the image:
1. Does this image show a physical product (like a phone, laptop, clothing, appliance, book, toy, etc.)?
   - If NO (e.g., landscape, selfie, meme, screenshot, food, nature), respond with:
   {{"error": true, "message": "Image does not appear to show a product. Please upload a clear photo of the item you are returning."}}

2. Does the product in the image match the category "{category}"?
   - Electronics = phones, laptops, tablets, headphones, cameras, consoles, etc.
   - Clothing = shirts, pants, dresses, shoes, jackets, accessories, etc.
   - Home = furniture, kitchen items, decor, tools, appliances, etc.
   - Books = books, notebooks, journals, etc.
   - Toys = toys, games, puzzles, figures, etc.
   - If the product clearly does NOT match the category, respond with:
   {{"error": true, "message": "The image appears to show a [what you see], but the return is filed under '{category}'. Please upload a photo of the correct product."}}

3. If the image passes both checks, assess its physical condition.

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

    # Try with current key, failover to backup if rate limited
    global _active_key_index
    keys = _get_api_keys()

    for attempt in range(len(keys)):
        try:
            _configure_gemini(_active_key_index)
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
        except Exception as e:
            error_str = str(e).lower()
            if "429" in str(e) or "quota" in error_str or "rate" in error_str or "exhausted" in error_str:
                print(f"Gemini key {_active_key_index + 1} rate limited, switching...")
                _active_key_index = (_active_key_index + 1) % len(keys)
            else:
                raise e

    raise Exception("All Gemini API keys exhausted")


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

    global _active_key_index
    keys = _get_api_keys()

    for attempt in range(len(keys)):
        try:
            _configure_gemini(_active_key_index)
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )
            return _parse_grading_response(response.text)
        except Exception as e:
            error_str = str(e).lower()
            if "429" in str(e) or "quota" in error_str or "rate" in error_str or "exhausted" in error_str:
                print(f"Gemini key {_active_key_index + 1} rate limited, switching...")
                _active_key_index = (_active_key_index + 1) % len(keys)
            else:
                raise e

    raise Exception("All Gemini API keys exhausted")


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
