"""
Pytest fixtures for testing the ServerlessOrch framework
"""
import json
import os
import pytest
import boto3
from moto import mock_dynamodb, mock_lambda, mock_logs


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for boto3"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def dynamodb(aws_credentials):
    """DynamoDB mock for testing"""
    with mock_dynamodb():
        yield boto3.resource("dynamodb", region_name="us-east-1")


@pytest.fixture(scope="function")
def lambda_client(aws_credentials):
    """Lambda client mock for testing"""
    with mock_lambda():
        yield boto3.client("lambda", region_name="us-east-1")


@pytest.fixture(scope="function")
def orders_table(dynamodb):
    """Create a mock Orders table for testing"""
    table = dynamodb.create_table(
        TableName="OrdersTable",
        KeySchema=[
            {"AttributeName": "order_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "order_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"}
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "status-index",
                "KeySchema": [
                    {"AttributeName": "status", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    
    # Set environment variable for Lambda functions
    os.environ["ORDERS_TABLE"] = "OrdersTable"
    return table


@pytest.fixture(scope="function")
def inventory_table(dynamodb):
    """Create a mock Inventory table for testing"""
    table = dynamodb.create_table(
        TableName="InventoryTable",
        KeySchema=[
            {"AttributeName": "product_id", "KeyType": "HASH"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "product_id", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    
    # Set environment variable for Lambda functions
    os.environ["INVENTORY_TABLE"] = "InventoryTable"
    
    # Add sample inventory items
    sample_items = [
        {
            "product_id": "product-1",
            "name": "Basic T-Shirt",
            "description": "Comfortable cotton t-shirt",
            "price": 19.99,
            "stock_quantity": 100
        },
        {
            "product_id": "product-2",
            "name": "Premium Jeans",
            "description": "High-quality denim jeans",
            "price": 49.99,
            "stock_quantity": 50
        }
    ]
    
    for item in sample_items:
        table.put_item(Item=item)
    
    return table


@pytest.fixture(scope="function")
def sample_order():
    """Create a sample order for testing"""
    return {
        "customer": {
            "customer_id": "cust-12345",
            "email": "test@example.com",
            "name": "Test Customer"
        },
        "items": [
            {
                "product_id": "product-1",
                "quantity": 2,
                "unit_price": 19.99
            },
            {
                "product_id": "product-2",
                "quantity": 1,
                "unit_price": 49.99
            }
        ],
        "shipping_address": {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "postal_code": "12345",
            "country": "US"
        },
        "payment": {
            "payment_method": "credit_card"
        }
    }


@pytest.fixture(scope="function")
def api_gateway_event(sample_order):
    """Create a sample API Gateway event for testing"""
    return {
        "httpMethod": "POST",
        "path": "/orders",
        "pathParameters": None,
        "queryStringParameters": None,
        "body": json.dumps(sample_order),
        "headers": {
            "Content-Type": "application/json"
        },
        "requestContext": {
            "requestId": "test-request-id"
        }
    }


@pytest.fixture(scope="function")
def lambda_context():
    """Create a mock Lambda context for testing"""
    class MockContext:
        def __init__(self):
            self.function_name = "test-function"
            self.function_version = "$LATEST"
            self.memory_limit_in_mb = 128
            self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
            self.aws_request_id = "test-request-id"
            self.log_group_name = "/aws/lambda/test-function"
            self.log_stream_name = "2023/10/01/[$LATEST]abcdef123456"
            self.identity = None
            self.client_context = None
            self.remaining_time_in_millis = 3000
        
        def get_remaining_time_in_millis(self):
            return self.remaining_time_in_millis
    
    return MockContext()