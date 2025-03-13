"""
Unit tests for the Lambda functions
"""
import json
import pytest
from functions.order_validator import handler as validator_handler, validate_order
from functions.inventory_service import handler as inventory_handler, check_order_inventory
from functions.payment_service import handler as payment_handler, process_payment
from functions.order_fulfillment import handler as fulfillment_handler
from functions.notification_service import handler as notification_handler
from lib.models import Order


def test_validate_order(sample_order):
    """Test the order validation function"""
    # Create an order object
    order = Order(**sample_order)
    
    # Validate the order
    is_valid, message = validate_order(order)
    
    # Check that the validation passed
    assert is_valid
    assert "valid" in message.lower()


def test_validate_order_missing_fields():
    """Test validation with missing fields"""
    # Create an incomplete order
    incomplete_order = Order(
        customer={
            "customer_id": "cust-12345",
            "email": "",  # Missing email
            "name": "Test Customer"
        },
        items=[
            {
                "product_id": "product-1",
                "quantity": 2,
                "unit_price": 19.99
            }
        ],
        shipping_address={
            "street": "123 Main St",
            "city": "Anytown",
            # Missing postal_code
            "country": "US"
        },
        payment={
            "payment_method": "credit_card"
        }
    )
    
    # Validate the order
    is_valid, message = validate_order(incomplete_order)
    
    # Check that the validation failed due to missing fields
    assert not is_valid
    assert "missing" in message.lower() or "incomplete" in message.lower()


def test_validator_handler(orders_table, inventory_table, lambda_context, sample_order):
    """Test the order validator Lambda handler"""
    # Create an order first
    order = Order(**sample_order)
    orders_table.put_item(Item=order.to_dynamo_dict())
    
    # Create event for validator handler
    event = {"order_id": order.order_id}
    
    # Call the validator handler
    response = validator_handler(event, lambda_context)
    
    # Check that validation was successful
    assert response["status"] == "success"
    assert response["order_id"] == order.order_id


def test_check_inventory(orders_table, inventory_table, lambda_context, sample_order):
    """Test the inventory check function"""
    # Create an order
    order = Order(**sample_order)
    
    # Check inventory
    inventory_results = check_order_inventory(order)
    
    # Check that all items are available
    assert all(result["available"] for result in inventory_results)
    assert len(inventory_results) == len(order.items)


def test_inventory_handler(orders_table, inventory_table, lambda_context, sample_order):
    """Test the inventory service Lambda handler"""
    # Create an order first
    order = Order(**sample_order)
    order.status = "VALIDATED"  # Set appropriate status
    orders_table.put_item(Item=order.to_dynamo_dict())
    
    # Create event for inventory handler
    event = {"order_id": order.order_id}
    
    # Call the inventory handler
    response = inventory_handler(event, lambda_context)
    
    # Check that inventory check was successful
    assert response["status"] == "success"
    assert response["order_id"] == order.order_id
    assert "All items available" in response["message"]


def test_process_payment(sample_order):
    """Test the payment processing function"""
    # Create an order
    order = Order(**sample_order)
    
    # Process payment
    payment_result = process_payment(order)
    
    # Check the payment result
    assert "success" in payment_result
    if payment_result["success"]:
        assert "transaction_id" in payment_result
        assert "amount" in payment_result
    else:
        assert "error" in payment_result


def test_payment_handler(orders_table, inventory_table, lambda_context, sample_order, monkeypatch):
    """Test the payment service Lambda handler"""
    # Create an order first
    order = Order(**sample_order)
    order.status = "INVENTORY_CHECKED"  # Set appropriate status
    orders_table.put_item(Item=order.to_dynamo_dict())
    
    # Mock the payment process to always succeed
    def mock_process_payment(order):
        return {
            "success": True,
            "transaction_id": "mock-transaction-id",
            "amount": order.calculate_total()
        }
    
    monkeypatch.setattr("functions.payment_service.process_payment", mock_process_payment)
    
    # Create event for payment handler
    event = {"order_id": order.order_id}
    
    # Call the payment handler
    response = payment_handler(event, lambda_context)
    
    # Check that payment was successful
    assert response["status"] == "success"
    assert response["order_id"] == order.order_id
    assert "transaction_id" in response


def test_fulfillment_handler(orders_table, inventory_table, lambda_context, sample_order, monkeypatch):
    """Test the order fulfillment Lambda handler"""
    # Create an order first
    order = Order(**sample_order)
    order.status = "PAYMENT_PROCESSED"  # Set appropriate status
    orders_table.put_item(Item=order.to_dynamo_dict())
    
    # Create event for fulfillment handler
    event = {"order_id": order.order_id}
    
    # Call the fulfillment handler
    response = fulfillment_handler(event, lambda_context)
    
    # Check that fulfillment was successful
    assert response["status"] == "success"
    assert response["order_id"] == order.order_id
    assert "tracking_id" in response


def test_notification_handler(orders_table, lambda_context, sample_order):
    """Test the notification service Lambda handler"""
    # Create an order first
    order = Order(**sample_order)
    order.status = "FULFILLED"  # Set appropriate status
    orders_table.put_item(Item=order.to_dynamo_dict())
    
    # Create event for notification handler
    event = {"order_id": order.order_id}
    
    # Call the notification handler
    response = notification_handler(event, lambda_context)
    
    # Check that notification was sent successfully
    assert response["status"] == "success"
    assert response["order_id"] == order.order_id
    assert "message_id" in response