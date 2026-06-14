import boto3
from app.config import settings

rekognition_client = boto3.client(
    "rekognition",
    region_name=settings.AWS_DEFAULT_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def detect_labels(s3_key: str, max_labels: int = 20, min_confidence: float = 70.0) -> list:
    """Detect labels in an image stored in S3."""
    response = rekognition_client.detect_labels(
        Image={
            "S3Object": {
                "Bucket": settings.S3_BUCKET_NAME,
                "Name": s3_key,
            }
        },
        MaxLabels=max_labels,
        MinConfidence=min_confidence,
    )
    return response.get("Labels", [])


def detect_moderation_labels(s3_key: str, min_confidence: float = 70.0) -> list:
    """Detect moderation labels (inappropriate content check)."""
    response = rekognition_client.detect_moderation_labels(
        Image={
            "S3Object": {
                "Bucket": settings.S3_BUCKET_NAME,
                "Name": s3_key,
            }
        },
        MinConfidence=min_confidence,
    )
    return response.get("ModerationLabels", [])
