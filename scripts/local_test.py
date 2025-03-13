#!/usr/bin/env python3
"""
Local testing script for the ServerlessOrch API
"""

import argparse
import json
import os
import sys
import uuid
import requests
from typing import Dict, Any


def setup_dynamodb_local():
    """
    Set up local DynamoDB tables using AWS CLI
    """
    print("Setting up local DynamoDB tables...")
    
    # Create Orders table
    os.system("""
    aws dynamodb create-table \
        --table-name OrdersTable \
        --attribute-definitions \
            AttributeName=order_id,AttributeType=S \
            AttributeName=created_at,AttributeType=S \
            AttributeName=status,AttributeType=S \
        --key-schema \
            AttributeName=order_id,KeyType=HASH \
            AttributeName=created_at,KeyType=RANGE \
        --global-secondary-indexes \
            "IndexName=status-index,KeySchema=[{AttributeName=status,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}],Projection={ProjectionType=ALL}" \
        --billing-mode PAY_PER_REQUEST \
        --endpoint-url http://localhost:8000
    """)
    
    # Create Inventory table
    os.system("""
    aws dynamodb create-table \
        --table-name InventoryTable \
        --attribute-definitions \
            AttributeName=product_id,AttributeType=S \
        --key-schema \
            AttributeName=product_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --endpoint-url http://localhost:8000
    """)
    
    # Add sample inventory data
    inventory_items = [
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
        },
        {
            "product_id": "product-3",
            "name": "Leather Jacket",
            "description": "Stylish leather jacket",
            "price": 199.99,
            "stock_quantity": 20
        }
    ]
    
    for item in inventory_items:
        os.system(f"""
        aws dynamodb put-item \
            --table-name InventoryTable \
            --item '{json.dumps({"product_id": {"S": item["product_id"]}, "name": {"S": item["name"]}, "description": {"S": item["description"]}, "price": {"N": str(item["price"])}, "stock_quantity": {"N": str(item["stock_quantity"])}})}' \
            --endpoint-url http://localhost:8000
        """)
    
    print("Local DynamoDB tables created successfully!")


def create_test_order(api_url: str) -> Dict[str, Any]:
    """
    Create a test order via the API
    
    Args:
        api_url: URL of the API Gateway
    
    Returns:
        Response from the API
    """
    print("Creating a test order...")
    
    # Sample order data
    order_data = {
        "customer": {
            "customer_id": f"cust-{uuid.uuid4().hex[:8]}",
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
    
    # Send POST request to create order
    response = requests.post(
        f"{api_url}/orders", 
        json=order_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {json.dumps(response.json(), indent=2)}")
    
    return response.json()


def get_order(api_url: str, order_id: str) -> Dict[str, Any]:
    """
    Get an order via the API
    
    Args:
        api_url: URL of the API Gateway
        order_id: ID of the order to retrieve
    
    Returns:
        Response from the API
    """
    print(f"Getting order {order_id}...")
    
    # Send GET request to retrieve order
    response = requests.get(f"{api_url}/orders/{order_id}")
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {json.dumps(response.json(), indent=2)}")
    
    return response.json()


def list_orders(api_url: str, status: str = None) -> Dict[str, Any]:
    """
    List orders via the API
    
    Args:
        api_url: URL of the API Gateway
        status: Optional status to filter by
    
    Returns:
        Response from the API
    """
    print("Listing orders...")
    
    # Build URL with optional status filter
    url = f"{api_url}/orders"
    if status:
        url += f"?status={status}"
    
    # Send GET request to list orders
    response = requests.get(url)
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {json.dumps(response.json(), indent=2)}")
    
    return response.json()


def run_test(api_url: str):
    """
    Run a full test of the API
    
    Args:
        api_url: URL of the API Gateway
    """
    # Create a test order
    order_response = create_test_order(api_url)
    order_id = order_response.get("order_id")
    
    if not order_id:
        print("Failed to create order - no order_id in response")
        return
    
    # Get the order details
    get_order(api_url, order_id)
    
    # List all orders
    list_orders(api_url)
    
    print("\nTest completed successfully!")
    print(f"Order ID: {order_id}")
    print(f"Check order status: {api_url}/orders/{order_id}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test the ServerlessOrch API")
    parser.add_argument("--api-url", help="API Gateway URL")
    parser.add_argument("--setup-db", action="store_true", help="Set up local DynamoDB tables")
    args = parser.parse_args()
    
    # Set up local DynamoDB if requested
    if args.setup_db:
        setup_dynamodb_local()
        return
    
    # Check if API URL was provided
    api_url = args.api_url
    if not api_url:
        api_url = input("Enter the API Gateway URL: ")
    
    # Remove trailing slash if present
    api_url = api_url.rstrip("/")
    
    # Run the test
    run_test(api_url)


if __name__ == "__main__":
    main()