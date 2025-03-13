import json
import logging
import time
import uuid
from typing import Dict, Any

from lib.models import Order, OrderStatus, PaymentStatus
from lib.utils import (
    lambda_handler_decorator,
    get_order,
    orders_table,
    update_order_status
)

logger = logging.getLogger()


@lambda_handler_decorator
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing payment for an order
    
    This function is triggered by the stream processor when an order
    has passed inventory check (status = INVENTORY_CHECKED)
    
    Args:
        event: Lambda event with order details
        context: Lambda context
        
    Returns:
        Result of payment processing
    """
    order_id = event.get("order_id")
    if not order_id:
        raise ValueError("No order_id provided in event")
    
    try:
        # Get the order from DynamoDB
        order_data = get_order(order_id)
        order = Order.from_dynamo_dict(order_data)
        
        # Process the payment
        payment_result = process_payment(order)
        
        if payment_result["success"]:
            # Update order payment information in DynamoDB
            update_payment_info(
                order_id,
                order.created_at,
                payment_result["transaction_id"],
                PaymentStatus.COMPLETED,
                payment_result["amount"]
            )
            
            # Update order status
            update_order_status(
                order_id, 
                OrderStatus.PAYMENT_PROCESSED, 
                "Payment processed successfully"
            )
            
            logger.info(f"Order {order_id} payment processed successfully")
            return {
                "status": "success",
                "order_id": order_id,
                "message": "Payment processed successfully",
                "transaction_id": payment_result["transaction_id"],
                "amount": payment_result["amount"]
            }
        else:
            # Update payment status to FAILED
            update_payment_info(
                order_id,
                order.created_at,
                None,
                PaymentStatus.FAILED,
                order.total_amount
            )
            
            # Update order status
            update_order_status(
                order_id, 
                OrderStatus.FAILED, 
                f"Payment failed: {payment_result['error']}"
            )
            
            logger.warning(f"Order {order_id} payment failed: {payment_result['error']}")
            return {
                "status": "failed",
                "order_id": order_id,
                "message": f"Payment failed: {payment_result['error']}"
            }
    
    except Exception as e:
        logger.error(f"Error processing payment for order {order_id}: {str(e)}")
        # Update order status to FAILED
        try:
            update_order_status(
                order_id, 
                OrderStatus.FAILED, 
                f"Payment processing error: {str(e)}"
            )
        except Exception:
            pass  # Ignore errors in error handling
        
        raise


def process_payment(order: Order) -> Dict[str, Any]:
    """
    Process payment for an order (mock implementation)
    
    In a real application, this would integrate with a payment gateway
    
    Args:
        order: Order object with payment information
        
    Returns:
        Dictionary with payment result
    """
    # Calculate the total amount
    amount = order.total_amount or order.calculate_total()
    
    # Simulate payment processing latency
    time.sleep(0.5)
    
    # Mock payment processing - in a real app, this would call a payment gateway
    # For demo purposes, we'll simulate successful payments for most orders
    # and occasional failures based on order amount
    if amount > 1000:
        # Simulate an occasional payment failure for large orders
        success = order.order_id[-1] not in "12"  # 20% chance of failure
    else:
        # Most regular orders succeed
        success = order.order_id[-1] not in "1"  # 10% chance of failure
    
    if success:
        return {
            "success": True,
            "transaction_id": f"TX-{uuid.uuid4()}",
            "amount": amount
        }
    else:
        return {
            "success": False,
            "error": "Payment declined by processor",
            "amount": amount
        }


def update_payment_info(
    order_id: str,
    created_at: str,
    transaction_id: str = None,
    status: PaymentStatus = PaymentStatus.PENDING,
    amount: float = None
) -> None:
    """
    Update payment information for an order
    
    Args:
        order_id: ID of the order
        created_at: Created timestamp of the order
        transaction_id: Payment transaction ID
        status: Payment status
        amount: Payment amount
    """
    update_expression = (
        "SET payment.status = :status, "
        "updated_at = :updated_at"
    )
    
    expression_attr_values = {
        ":status": status,
        ":updated_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    }
    
    if transaction_id is not None:
        update_expression += ", payment.transaction_id = :transaction_id"
        expression_attr_values[":transaction_id"] = transaction_id
    
    if amount is not None:
        update_expression += ", payment.amount = :amount"
        expression_attr_values[":amount"] = amount
    
    orders_table.update_item(
        Key={"order_id": order_id, "created_at": created_at},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attr_values
    )