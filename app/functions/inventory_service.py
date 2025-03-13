import json
import logging
from typing import Dict, Any, List

from lib.models import Order, OrderStatus
from lib.utils import (
    lambda_handler_decorator,
    get_order,
    update_order_status,
    check_inventory
)

logger = logging.getLogger()


@lambda_handler_decorator
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for checking inventory for order items
    
    This function is triggered by the stream processor when an order 
    has been validated (status = VALIDATED)
    
    Args:
        event: Lambda event with order details
        context: Lambda context
        
    Returns:
        Result of inventory check
    """
    order_id = event.get("order_id")
    if not order_id:
        raise ValueError("No order_id provided in event")
    
    try:
        # Get the order from DynamoDB
        order_data = get_order(order_id)
        order = Order.from_dynamo_dict(order_data)
        
        # Check inventory for all items
        inventory_results = check_order_inventory(order)
        
        # If all items are available, update order status
        if all(result["available"] for result in inventory_results):
            update_order_status(
                order_id, 
                OrderStatus.INVENTORY_CHECKED, 
                "All items available in inventory"
            )
            logger.info(f"Order {order_id} inventory check passed")
            return {
                "status": "success",
                "order_id": order_id,
                "message": "All items available in inventory",
                "inventory_results": inventory_results
            }
        else:
            # Some items are not available
            unavailable_items = [
                result for result in inventory_results 
                if not result["available"]
            ]
            update_order_status(
                order_id, 
                OrderStatus.FAILED, 
                f"Inventory check failed: {len(unavailable_items)} item(s) unavailable"
            )
            logger.warning(f"Order {order_id} inventory check failed: {unavailable_items}")
            return {
                "status": "failed",
                "order_id": order_id,
                "message": "Some items are unavailable",
                "inventory_results": inventory_results
            }
    
    except Exception as e:
        logger.error(f"Error checking inventory for order {order_id}: {str(e)}")
        # Update order status to FAILED
        try:
            update_order_status(
                order_id, 
                OrderStatus.FAILED, 
                f"Inventory check error: {str(e)}"
            )
        except Exception:
            pass  # Ignore errors in error handling
        
        raise


def check_order_inventory(order: Order) -> List[Dict[str, Any]]:
    """
    Check inventory availability for all items in an order
    
    Args:
        order: Order object with items to check
        
    Returns:
        List of inventory check results for each item
    """
    results = []
    
    for item in order.items:
        available = check_inventory(item.product_id, item.quantity)
        
        results.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "available": available
        })
    
    return results