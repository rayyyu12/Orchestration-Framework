import json
import logging
import boto3
import os
from typing import Dict, Any, List

from lib.models import OrderStatus
from lib.utils import lambda_handler_decorator

logger = logging.getLogger()

# Initialize the Lambda client
lambda_client = boto3.client("lambda")


@lambda_handler_decorator
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing DynamoDB streams from the orders table
    
    This function routes events to the appropriate service based on the
    order status
    
    Args:
        event: DynamoDB stream event
        context: Lambda context
        
    Returns:
        Results of processing
    """
    results = []
    
    # Process each record in the batch
    for record in event.get("Records", []):
        try:
            # Only process new or modified records
            if record["eventName"] not in ["INSERT", "MODIFY"]:
                continue
            
            # Parse the new image (current state) of the record
            new_image = record["dynamodb"].get("NewImage")
            if not new_image:
                continue
            
            # Convert DynamoDB format to regular dict
            order_data = dynamodb_to_dict(new_image)
            
            # Get the order ID and status
            order_id = order_data.get("order_id")
            status = order_data.get("status")
            
            if not order_id or not status:
                logger.warning("Missing order_id or status in record")
                continue
            
            # Process based on order status
            result = process_order_status(order_id, status)
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            results.append({
                "status": "error",
                "error": str(e)
            })
    
    return {
        "processed_count": len(results),
        "results": results
    }


def process_order_status(order_id: str, status: str) -> Dict[str, Any]:
    """
    Process an order based on its current status
    
    Args:
        order_id: ID of the order
        status: Current status of the order
        
    Returns:
        Result of processing
    """
    try:
        # Define which Lambda function to invoke based on status
        status_to_function = {
            OrderStatus.RECEIVED: "ValidatorFunction",
            OrderStatus.VALIDATED: "InventoryFunction",
            OrderStatus.INVENTORY_CHECKED: "PaymentFunction",
            OrderStatus.PAYMENT_PROCESSED: "FulfillmentFunction",
            OrderStatus.FULFILLED: "NotificationFunction"
        }
        
        # Get the function name for this status
        function_suffix = status_to_function.get(status)
        
        if not function_suffix:
            # No processing needed for this status
            return {
                "order_id": order_id,
                "status": status,
                "message": "No processing required for this status"
            }
        
        # Construct the full function name
        stack_name = os.environ.get("AWS_SAM_LOCAL", "serverless-orch-api")
        function_name = f"{stack_name}-{function_suffix}"
        
        # Prepare the payload
        payload = {
            "order_id": order_id
        }
        
        # Invoke the Lambda function asynchronously
        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="Event",  # Asynchronous
            Payload=json.dumps(payload)
        )
        
        logger.info(f"Invoked {function_name} for order {order_id} with status {status}")
        
        return {
            "order_id": order_id,
            "status": status,
            "invoked_function": function_name,
            "message": "Successfully invoked Lambda function"
        }
    
    except Exception as e:
        logger.error(f"Error processing order {order_id} with status {status}: {str(e)}")
        return {
            "order_id": order_id,
            "status": status,
            "error": str(e),
            "message": "Failed to process order"
        }


def dynamodb_to_dict(dynamodb_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert DynamoDB item format to a regular Python dictionary
    
    Args:
        dynamodb_item: Item in DynamoDB format
        
    Returns:
        Item as a regular dictionary
    """
    result = {}
    
    for key, value in dynamodb_item.items():
        # Handle different DynamoDB types
        if "S" in value:
            result[key] = value["S"]
        elif "N" in value:
            result[key] = float(value["N"])
        elif "BOOL" in value:
            result[key] = value["BOOL"]
        elif "NULL" in value:
            result[key] = None
        elif "M" in value:
            result[key] = dynamodb_to_dict(value["M"])
        elif "L" in value:
            result[key] = [dynamodb_to_dict(item) if "M" in item else item for item in value["L"]]
    
    return result