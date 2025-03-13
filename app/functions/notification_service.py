import json
import logging
import time
from typing import Dict, Any

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
    Lambda handler for sending notifications about order status
    
    This function is triggered by the stream processor when an order
    has been fulfilled (status = FULFILLED)
    
    Args:
        event: Lambda event with order details
        context: Lambda context
        
    Returns:
        Result of notification sending
    """
    order_id = event.get("order_id")
    if not order_id:
        raise ValueError("No order_id provided in event")
    
    try:
        # Get the order from DynamoDB
        order_data = get_order(order_id)
        order = Order.from_dynamo_dict(order_data)
        
        # Send the notification
        notification_result = send_notification(order)
        
        if notification_result["success"]:
            # Update order status to COMPLETED
            update_order_status(
                order_id, 
                OrderStatus.COMPLETED, 
                f"Notification sent to customer: {notification_result['message_id']}"
            )
            
            logger.info(f"Order {order_id} notification sent successfully")
            return {
                "status": "success",
                "order_id": order_id,
                "message": "Notification sent successfully",
                "message_id": notification_result["message_id"]
            }
        else:
            # Log the failure but don't change order status
            # Order is still fulfilled even if notification fails
            logger.warning(
                f"Order {order_id} notification failed: {notification_result['error']}"
            )
            return {
                "status": "failed",
                "order_id": order_id,
                "message": f"Notification failed: {notification_result['error']}"
            }
    
    except Exception as e:
        logger.error(f"Error sending notification for order {order_id}: {str(e)}")
        raise


def send_notification(order: Order) -> Dict[str, Any]:
    """
    Send a notification to the customer about their order (mock implementation)
    
    In a real application, this would integrate with an email or SMS service
    
    Args:
        order: Order object with customer information
        
    Returns:
        Dictionary with notification result
    """
    try:
        # Mock notification sending - in a real app, this would call an email or SMS API
        customer_email = order.customer.email
        customer_name = order.customer.name
        order_id = order.order_id
        
        # Log what would be sent
        notification_content = {
            "to": customer_email,
            "subject": f"Your order {order_id} has been fulfilled",
            "body": f"""
                Hello {customer_name},
                
                Great news! Your order {order_id} has been fulfilled and is on its way.
                You can track your shipment using the tracking number provided in your account.
                
                Thank you for your business!
                
                The ServerlessOrch Team
            """
        }
        
        logger.info(f"Would send notification: {json.dumps(notification_content)}")
        
        # Simulate slight delay for notification sending
        time.sleep(0.2)
        
        # Generate a mock message ID
        message_id = f"MSG-{int(time.time())}-{order_id[-6:]}"
        
        return {
            "success": True,
            "message_id": message_id
        }
    
    except Exception as e:
        logger.error(f"Error in notification service: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }