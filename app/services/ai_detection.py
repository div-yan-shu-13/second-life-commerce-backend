"""
AI-generated image detection using SightEngine API.
Free tier: 2000 operations/month.
Sign up: https://sightengine.com (no credit card needed)
"""
import requests
from app.config import settings


def check_ai_generated(image_bytes: bytes, filename: str = "image.jpg") -> dict:
    """
    Check if an image is AI-generated using SightEngine.

    Returns:
        {
            "is_ai_generated": bool,
            "ai_score": float (0-1, higher = more likely AI),
            "passed": bool (True = real image, safe to proceed)
        }

    If SightEngine is not configured or fails, returns passed=True (don't block).
    """
    if not settings.SIGHTENGINE_API_USER or not settings.SIGHTENGINE_API_SECRET:
        # Not configured — skip check, allow through
        return {"is_ai_generated": False, "ai_score": 0.0, "passed": True}

    try:
        response = requests.post(
            "https://api.sightengine.com/1.0/check.json",
            files={"media": (filename, image_bytes)},
            data={
                "models": "genai",
                "api_user": settings.SIGHTENGINE_API_USER,
                "api_secret": settings.SIGHTENGINE_API_SECRET,
            },
            timeout=10,
        )

        if response.status_code != 200:
            print(f"SightEngine error: {response.status_code} {response.text[:200]}")
            return {"is_ai_generated": False, "ai_score": 0.0, "passed": True}

        result = response.json()

        # SightEngine returns: {"type": {"ai_generated": 0.95}} 
        ai_score = result.get("type", {}).get("ai_generated", 0.0)

        # Threshold: if AI confidence > 0.7, flag as AI-generated
        is_ai = ai_score > 0.7

        return {
            "is_ai_generated": is_ai,
            "ai_score": round(ai_score, 3),
            "passed": not is_ai,
        }

    except Exception as e:
        print(f"SightEngine check failed: {e}")
        # On failure, don't block the user
        return {"is_ai_generated": False, "ai_score": 0.0, "passed": True}
