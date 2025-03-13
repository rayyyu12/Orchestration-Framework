import json
import logging
from datetime import datetime
from typing import Dict, Any, List

import boto3
from lib.models import Order, OrderStatus
from lib.utils import (
    api_response, 
    lambda_handler_decorator, 
    orders_table,
    get_order,
    get_order_created_at
)

logger = logging.getLogger()


@lambda_handler_decorator
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main API handler for order-related operations
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    http_method = event.get("httpMethod")
    path = event.get("path", "")
    path_parameters = event.get("pathParameters") or {}
    
    # GET /orders - List orders
    if http_method == "GET" and not path_parameters.get("orderId"):
        return list_orders(event)
    
    # GET /orders/{orderId} - Get order details
    elif http_method == "GET" and path_parameters.get("orderId"):
        return get_order_details(path_parameters["orderId"])
    
    # POST /orders - Create a new order
    elif http_method == "POST" and not path_parameters.get("orderId"):
        return create_order(event)
    
    # Unsupported route
    return api_response(404, {"error": "Route not found"})


def list_orders(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    List orders with optional filtering
    
    Args:
        event: API Gateway event
        
    Returns:
        API Gateway response with list of orders
    """
    query_parameters = event.get("queryStringParameters") or {}
    status_filter = query_parameters.get("status")
    limit = int(query_parameters.get("limit", 10))
    
    try:
        if status_filter:
            # Query by status using GSI
            response = orders_table.query(
                IndexName="status-index",
                KeyConditionExpression="status = :status",
                ExpressionAttributeValues={":status": status_filter},
                Limit=limit,
                ScanIndexForward=False  # Sort by created_at descending
            )
        else:
            # Scan for all orders (limited to specified limit)
            response = orders_table.scan(Limit=limit)
        
        orders = response.get("Items", [])
        
        return api_response(200, {
            "orders": orders,
            "count": len(orders)
        })
        
    except Exception as e:
        logger.error(f"Error listing orders: {str(e)}")
        return api_response(500, {"error": "Failed to list orders"})


def get_order_details(order_id: str) -> Dict[str, Any]:
    """
    Get details of a specific order
    
    Args:
        order_id: ID of the order
        
    Returns:
        API Gateway response with order details
    """
    try:
        order_item = get_order(order_id)
        return api_response(200, order_item)
        
    except ValueError:
        return api_response(404, {"error": f"Order not found: {order_id}"})
        
    except Exception as e:
        logger.error(f"Error getting order details: {str(e)}")
        return api_response(500, {"error": "Failed to get order details"})


def create_order(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new order
    
    Args:
        event: API Gateway event with order data
        
    Returns:
        API Gateway response with created order
    """
    try:
        # Parse the request body
        body = json.loads(event.get("body", "{}"))
        
        # Create a new Order object
        order = Order(**body)
        
        # Calculate the total amount
        order.total_amount = order.calculate_total()
        
        # Save to DynamoDB
        orders_table.put_item(Item=order.to_dynamo_dict())
        
        # Return the created order
        return api_response(201, order.to_dynamo_dict())
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return api_response(400, {"error": f"Validation error: {str(e)}"})
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return api_response(500, {"error": "Failed to create order"})