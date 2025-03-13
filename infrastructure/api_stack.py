from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_lambda_event_sources as lambda_events,
)
from constructs import Construct

class ApiStack(Stack):
    def __init__(
        self, 
        scope: Construct, 
        id: str, 
        orders_table: dynamodb.Table,
        inventory_table: dynamodb.Table,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Common Lambda settings
        lambda_runtime = lambda_.Runtime.PYTHON_3_9
        lambda_env = {
            "ORDERS_TABLE": orders_table.table_name,
            "INVENTORY_TABLE": inventory_table.table_name,
            "LOG_LEVEL": "INFO",
        }
        
        # Lambda layer for common code
        common_layer = lambda_.LayerVersion(
            self, "CommonLayer",
            code=lambda_.Code.from_asset("app/lib"),
            compatible_runtimes=[lambda_runtime],
            description="Common utilities and models"
        )

        # Create Lambda functions
        self.order_api_lambda = lambda_.Function(
            self, "OrderApiFunction",
            runtime=lambda_runtime,
            code=lambda_.Code.from_asset("app"),
            handler="functions.order_api.handler",
            environment=lambda_env,
            timeout=Duration.seconds(10),
            memory_size=256,
            layers=[common_layer]
        )
        
        self.validator_lambda = lambda_.Function(
            self, "ValidatorFunction",
            runtime=lambda_runtime,
            code=lambda_.Code.from_asset("app"),
            handler="functions.order_validator.handler",
            environment=lambda_env,
            timeout=Duration.seconds(15),
            memory_size=256,
            layers=[common_layer]
        )
        
        self.inventory_lambda = lambda_.Function(
            self, "InventoryFunction",
            runtime=lambda_runtime,
            code=lambda_.Code.from_asset("app"),
            handler="functions.inventory_service.handler",
            environment=lambda_env,
            timeout=Duration.seconds(15),
            memory_size=256,
            layers=[common_layer]
        )
        
        self.payment_lambda = lambda_.Function(
            self, "PaymentFunction",
            runtime=lambda_runtime,
            code=lambda_.Code.from_asset("app"),
            handler="functions.payment_service.handler",
            environment=lambda_env,
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[common_layer]
        )
        
        self.fulfillment_lambda = lambda_.Function(
            self, "FulfillmentFunction",
            runtime=lambda_runtime,
            code=lambda_.Code.from_asset("app"),
            handler="functions.order_fulfillment.handler",
            environment=lambda_env,
            timeout=Duration.seconds(15),
            memory_size=256,
            layers=[common_layer]
        )
        
        self.notification_lambda = lambda_.Function(
            self, "NotificationFunction",
            runtime=lambda_runtime,
            code=lambda_.Code.from_asset("app"),
            handler="functions.notification_service.handler",
            environment=lambda_env,
            timeout=Duration.seconds(10),
            memory_size=256,
            layers=[common_layer]
        )
        
        # Stream processor Lambda for handling DynamoDB streams
        self.stream_processor_lambda = lambda_.Function(
            self, "StreamProcessorFunction",
            runtime=lambda_runtime,
            code=lambda_.Code.from_asset("app"),
            handler="functions.stream_processor.handler",
            environment=lambda_env,
            timeout=Duration.seconds(60),
            memory_size=512,
            layers=[common_layer]
        )
        
        # Add DynamoDB Stream as event source for the processor Lambda
        self.stream_processor_lambda.add_event_source(
            lambda_events.DynamoEventSource(
                orders_table,
                starting_position=lambda_.StartingPosition.LATEST,
                batch_size=10,
                retry_attempts=3
            )
        )
        
        # Grant permissions to Lambda functions
        orders_table.grant_read_write_data(self.order_api_lambda)
        orders_table.grant_read_write_data(self.validator_lambda)
        orders_table.grant_read_write_data(self.inventory_lambda)
        orders_table.grant_read_write_data(self.payment_lambda)
        orders_table.grant_read_write_data(self.fulfillment_lambda)
        orders_table.grant_read_write_data(self.notification_lambda)
        orders_table.grant_read_write_data(self.stream_processor_lambda)
        
        inventory_table.grant_read_data(self.inventory_lambda)
        
        # Create API Gateway REST API
        api = apigw.RestApi(
            self, "OrdersApi",
            rest_api_name="Orders Service API",
            description="API for processing orders",
            deploy_options=apigw.StageOptions(
                stage_name="dev",
                throttling_rate_limit=100,
                throttling_burst_limit=50,
                logging_level=apigw.MethodLoggingLevel.INFO,
                metrics_enabled=True
            )
        )
        
        # Create API resources and methods
        orders = api.root.add_resource("orders")
        
        # POST /orders - Create a new order
        orders.add_method(
            "POST",
            apigw.LambdaIntegration(self.order_api_lambda)
        )
        
        # GET /orders - List orders
        orders.add_method(
            "GET",
            apigw.LambdaIntegration(self.order_api_lambda)
        )
        
        # GET /orders/{orderId} - Get a specific order
        order = orders.add_resource("{orderId}")
        order.add_method(
            "GET",
            apigw.LambdaIntegration(self.order_api_lambda)
        )
        
        # Export outputs
        self.api_endpoint = api.url
        
        # Store references to all resources
        self.lambdas = [
            self.order_api_lambda,
            self.validator_lambda,
            self.inventory_lambda,
            self.payment_lambda,
            self.fulfillment_lambda,
            self.notification_lambda,
            self.stream_processor_lambda
        ]