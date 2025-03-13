import json
import logging
from typing import Dict, Any, List, Tuple

from lib.models import Order, OrderStatus
from lib.utils import (
    lambda_handler_decorator,
    get_order,
    update_order_status
)

logger = logging.getLogger()


@lambda_handler_decorator
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for validating new orders
    
    This function is triggered by the stream processor when a new order
    is created with status RECEIVED
    
    Args:
        event: Lambda event with order details
        context: Lambda context
        
    Returns:
        Result of validation
    """
    order_id = event.get("order_id")
    if not order_id:
        raise ValueError("No order_id provided in event")
    
    try:
        # Get the order from DynamoDB
        order_data = get_order(order_id)
        order = Order.from_dynamo_dict(order_data)
        
        # Validate the order
        is_valid, validation_message = validate_order(order)
        
        if is_valid:
            # Update order status to VALIDATED
            update_order_status(
                order_id, 
                OrderStatus.VALIDATED, 
                "Order validated successfully"
            )
            logger.info(f"Order {order_id} validated successfully")
            return {
                "status": "success",
                "order_id": order_id,
                "message": "Order validated successfully"
            }
        else:
            # Update order status to FAILED
            update_order_status(
                order_id, 
                OrderStatus.FAILED, 
                f"Validation failed: {validation_message}"
            )
            logger.warning(f"Order {order_id} validation failed: {validation_message}")
            return {
                "status": "failed",
                "order_id": order_id,
                "message": f"Validation failed: {validation_message}"
            }
    
    except Exception as e:
        logger.error(f"Error validating order {order_id}: {str(e)}")
        # Update order status to FAILED
        try:
            update_order_status(
                order_id, 
                OrderStatus.FAILED, 
                f"Validation error: {str(e)}"
            )
        except Exception:
            pass  # Ignore errors in error handling
        
        raise


def validate_order(order: Order) -> Tuple[bool, str]:
    """
    Validate an order by checking various business rules
    
    Args:
        order: Order object to validate
        
    Returns:
        Tuple of (is_valid, validation_message)
    """
    # Check if customer info is complete
    if not order.customer.email or not order.customer.name:
        return False, "Customer information is incomplete"
    
    # Check if shipping address is complete
    required_address_fields = ["street", "city", "postal_code", "country"]
    for field in required_address_fields:
        if field not in order.shipping_address or not order.shipping_address[field]:
            return False, f"Shipping address is missing {field}"
    
    # Check if order has items
    if not order.items:
        return False, "Order has no items"
    
    # Check payment information
    if not order.payment.payment_method:
        return False, "Payment method is required"
    
    # Validate email format (basic check)
    if "@" not in order.customer.email or "." not in order.customer.email:
        return False, "Invalid email format"
    
    # Additional business logic validations could be added here
    
    # All validations passed
    return True, "Order is valid"