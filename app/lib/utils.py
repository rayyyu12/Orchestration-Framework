import json
import logging
import os
import time
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import boto3
from pythonjsonlogger import jsonlogger

# Configure logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(LOG_LEVEL)

# Initialize DynamoDB resources
dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ.get("ORDERS_TABLE", "OrdersTable"))
inventory_table = dynamodb.Table(os.environ.get("INVENTORY_TABLE", "InventoryTable"))


def api_response(status_code: int, body: Any) -> Dict[str, Any]:
    """
    Create a standardized API Gateway response
    
    Args:
        status_code: HTTP status code
        body: Response body (will be converted to JSON)
        
    Returns:
        API Gateway response dictionary
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True
        },
        "body": json.dumps(body)
    }


def lambda_handler_decorator(func: Callable) -> Callable:
    """
    Decorator for Lambda handler functions to add logging, error handling,
    and performance metrics
    
    Args:
        func: Lambda handler function
        
    Returns:
        Wrapped Lambda handler function
    """
    @wraps(func)
    def wrapper(event, context):
        request_id = context.aws_request_id
        start_time = time.time()
        
        logger.info({
            "message": "Lambda invocation started",
            "request_id": request_id,
            "event_type": type(event).__name__
        })
        
        try:
            # Call the original handler
            response = func(event, context)
            
            # Log execution time
            execution_time = (time.time() - start_time) * 1000
            logger.info({
                "message": "Lambda invocation completed",
                "request_id": request_id,
                "execution_time_ms": execution_time
            })
            
            return response
            
        except Exception as e:
            # Log the error
            execution_time = (time.time() - start_time) * 1000
            logger.error({
                "message": "Lambda invocation failed",
                "request_id": request_id,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "execution_time_ms": execution_time
            })
            
            # For API Gateway handlers, return an error response
            if "httpMethod" in event or "routeKey" in event:
                return api_response(500, {"error": "Internal server error"})
            
            # Re-raise the exception for other types of Lambda handlers
            raise
            
    return wrapper


def update_order_status(order_id: str, status: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Update the status of an order in DynamoDB
    
    Args:
        order_id: ID of the order to update
        status: New status value
        notes: Optional notes to add to the order
        
    Returns:
        Updated order item from DynamoDB
    """
    update_expression = "SET #status = :status, updated_at = :updated_at"
    expression_attr_names = {"#status": "status"}
    expression_attr_values = {
        ":status": status,
        ":updated_at": datetime.utcnow().isoformat()
    }
    
    if notes:
        update_expression += ", notes = :notes"
        expression_attr_values[":notes"] = notes
    
    response = orders_table.update_item(
        Key={"order_id": order_id, "created_at": get_order_created_at(order_id)},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attr_names,
        ExpressionAttributeValues=expression_attr_values,
        ReturnValues="ALL_NEW"
    )
    
    return response.get("Attributes", {})


def get_order_created_at(order_id: str) -> str:
    """
    Get the created_at timestamp for an order
    
    Args:
        order_id: ID of the order
        
    Returns:
        created_at timestamp string
    """
    response = orders_table.query(
        KeyConditionExpression="order_id = :order_id",
        ExpressionAttributeValues={":order_id": order_id},
        ProjectionExpression="created_at",
        Limit=1
    )
    
    items = response.get("Items", [])
    if not items:
        raise ValueError(f"Order not found: {order_id}")
    
    return items[0]["created_at"]


def get_order(order_id: str) -> Dict[str, Any]:
    """
    Get an order from DynamoDB
    
    Args:
        order_id: ID of the order
        
    Returns:
        Order item from DynamoDB
    """
    response = orders_table.get_item(
        Key={"order_id": order_id, "created_at": get_order_created_at(order_id)}
    )
    
    item = response.get("Item")
    if not item:
        raise ValueError(f"Order not found: {order_id}")
    
    return item


def check_inventory(product_id: str, quantity: int) -> bool:
    """
    Check if there is sufficient inventory for a product
    
    Args:
        product_id: ID of the product
        quantity: Quantity requested
        
    Returns:
        True if sufficient inventory, False otherwise
    """
    try:
        response = inventory_table.get_item(
            Key={"product_id": product_id},
            ProjectionExpression="stock_quantity"
        )
        
        item = response.get("Item")
        if not item:
            logger.warning({
                "message": "Product not found in inventory",
                "product_id": product_id
            })
            return False
        
        stock_quantity = item.get("stock_quantity", 0)
        result = stock_quantity >= quantity
        
        if not result:
            logger.warning({
                "message": "Insufficient inventory",
                "product_id": product_id,
                "requested": quantity,
                "available": stock_quantity
            })
        
        return result
    
    except Exception as e:
        logger.error({
            "message": "Error checking inventory",
            "product_id": product_id,
            "error": str(e)
        })
        return False


def update_inventory(product_id: str, quantity: int) -> bool:
    """
    Update inventory for a product (decrement by quantity)
    
    Args:
        product_id: ID of the product
        quantity: Quantity to decrement
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Use conditional update to ensure we don't go below zero
        inventory_table.update_item(
            Key={"product_id": product_id},
            UpdateExpression="SET stock_quantity = stock_quantity - :quantity",
            ConditionExpression="stock_quantity >= :quantity",
            ExpressionAttributeValues={":quantity": quantity}
        )
        return True
    
    except boto3.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning({
                "message": "Conditional check failed when updating inventory",
                "product_id": product_id,
                "quantity": quantity
            })
        else:
            logger.error({
                "message": "Error updating inventory",
                "product_id": product_id,
                "quantity": quantity,
                "error": str(e)
            })
        return False
    
    except Exception as e:
        logger.error({
            "message": "Error updating inventory",
            "product_id": product_id,
            "quantity": quantity,
            "error": str(e)
        })
        return False