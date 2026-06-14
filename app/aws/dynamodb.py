import boto3
from decimal import Decimal
from app.config import settings

dynamodb = boto3.resource(
    "dynamodb",
    region_name=settings.AWS_DEFAULT_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def _sanitize_for_dynamo(obj):
    """Recursively convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(round(obj, 6)))
    elif isinstance(obj, dict):
        return {k: _sanitize_for_dynamo(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_dynamo(v) for v in obj]
    return obj


def get_table(table_name: str):
    return dynamodb.Table(table_name)


def put_item(table_name: str, item: dict):
    table = get_table(table_name)
    item = _sanitize_for_dynamo(item)
    table.put_item(Item=item)
    return item


def get_item(table_name: str, key: dict):
    table = get_table(table_name)
    response = table.get_item(Key=key)
    return response.get("Item")


def update_item(table_name: str, key: dict, update_expression: str, expression_values: dict):
    table = get_table(table_name)
    response = table.update_item(
        Key=key,
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ReturnValues="ALL_NEW",
    )
    return response.get("Attributes")


def query_items(table_name: str, key_condition: str, expression_values: dict, index_name: str = None):
    table = get_table(table_name)
    kwargs = {
        "KeyConditionExpression": key_condition,
        "ExpressionAttributeValues": expression_values,
    }
    if index_name:
        kwargs["IndexName"] = index_name
    response = table.query(**kwargs)
    return response.get("Items", [])


def scan_items(table_name: str, filter_expression: str = None, expression_values: dict = None):
    table = get_table(table_name)
    kwargs = {}
    if filter_expression:
        kwargs["FilterExpression"] = filter_expression
    if expression_values:
        kwargs["ExpressionAttributeValues"] = expression_values
    response = table.scan(**kwargs)
    return response.get("Items", [])
