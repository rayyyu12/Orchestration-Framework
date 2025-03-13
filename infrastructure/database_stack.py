from aws_cdk import (
    Stack, 
    RemovalPolicy,
    Duration,
    aws_dynamodb as dynamodb,
)
from constructs import Construct

class DatabaseStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Create Orders table with stream enabled
        self.orders_table = dynamodb.Table(
            self, 
            "OrdersTable",
            partition_key=dynamodb.Attribute(
                name="order_id", 
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            time_to_live_attribute="expiration_time",
            removal_policy=RemovalPolicy.DESTROY  # Use RETAIN in production
        )
        
        # Create a GSI for order status queries
        self.orders_table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(
                name="status", 
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Create Inventory table
        self.inventory_table = dynamodb.Table(
            self, 
            "InventoryTable",
            partition_key=dynamodb.Attribute(
                name="product_id", 
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY  # Use RETAIN in production
        )