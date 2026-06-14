import boto3
from app.config import settings

s3_client = boto3.client(
    "s3",
    region_name=settings.AWS_DEFAULT_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def upload_image(file_bytes: bytes, key: str, content_type: str = "image/jpeg") -> str:
    """Upload image bytes to S3, return the S3 key."""
    s3_client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return key


def get_presigned_url(key: str, expiration: int = 3600) -> str:
    """Generate a presigned URL for downloading an object."""
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expiration,
    )
    return url


def delete_object(key: str):
    """Delete an object from S3."""
    s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
