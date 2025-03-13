import json
import logging
import uuid
from typing import Dict, Any, List

from lib.models import Order, OrderStatus
from lib.utils import (
    lambda_handler_decorator,
    get_order,
    update_order_status,
    update_inventory
)

logger = logging.getLogger()


@lambda_handler_decorator
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for fulfilling an order
    
    This function is triggered by the stream processor when an order
    has been paid for (status = PAYMENT_PROCESSED)
    
    Args:
        event: Lambda event with order details
        context: Lambda context
        
    Returns:
        Result of order fulfillment
    """
    order_id = event.get("order_id")
    if not order_id:
        raise ValueError("No order_id provided in event")
    
    try:
        # Get the order from DynamoDB
        order_data = get_order(order_id)
        order = Order.from_dynamo_dict(order_data)
        
        # Fulfill the order
        fulfillment_result = fulfill_order(order)
        
        if fulfillment_result["success"]:
            # Update order status
            update_order_status(
                order_id, 
                OrderStatus.FULFILLED, 
                f"Order fulfilled. Tracking ID: {fulfillment_result['tracking_id']}"
            )
            
            logger.info(f"Order {order_id} fulfilled successfully")
            return {
                "status": "success",
                "order_id": order_id,
                "message": "Order fulfilled successfully",
                "tracking_id": fulfillment_result["tracking_id"]
            }
        else:
            # Update order status
            update_order_status(
                order_id, 
                OrderStatus.FAILED, 
                f"Fulfillment failed: {fulfillment_result['error']}"
            )
            
            logger.warning(f"Order {order_id} fulfillment failed: {fulfillment_result['error']}")
            return {
                "status": "failed",
                "order_id": order_id,
                "message": f"Fulfillment failed: {fulfillment_result['error']}"
            }
    
    except Exception as e:
        logger.error(f"Error fulfilling order {order_id}: {str(e)}")
        # Update order status to FAILED
        try:
            update_order_status(
                order_id, 
                OrderStatus.FAILED, 
                f"Fulfillment error: {str(e)}"
            )
        except Exception:
            pass  # Ignore errors in error handling
        
        raise


def fulfill_order(order: Order) -> Dict[str, Any]:
    """
    Fulfill an order by updating inventory and generating tracking info
    
    Args:
        order: Order object to fulfill
        
    Returns:
        Dictionary with fulfillment result
    """
    # Update inventory for all items
    inventory_updates = []
    
    for item in order.items:
        success = update_inventory(item.product_id, item.quantity)
        inventory_updates.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "success": success
        })
    
    # Check if all inventory updates were successful
    if all(update["success"] for update in inventory_updates):
        # Generate a tracking ID (in a real system, this would come from a shipping API)
        tracking_id = f"TRK-{uuid.uuid4().hex[:12].upper()}"
        
        return {
            "success": True,
            "tracking_id": tracking_id,
            "inventory_updates": inventory_updates
        }
    else:
        # Some inventory updates failed
        failed_updates = [
            update for update in inventory_updates 
            if not update["success"]
        ]
        
        return {
            "success": False,
            "error": f"Failed to update inventory for {len(failed_updates)} item(s)",
            "inventory_updates": inventory_updates
        }