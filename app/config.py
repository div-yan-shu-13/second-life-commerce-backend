import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "second-life-commerce-images")
    MODEL_PATH: str = os.getenv("MODEL_PATH", "trained_models/")
    # Google Gemini API key (free tier: 15 RPM, 1500/day)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # Set to "false" to skip AI grading and use rule-based fallback only
    USE_BEDROCK: bool = os.getenv("USE_BEDROCK", "true").lower() == "true"


settings = Settings()
