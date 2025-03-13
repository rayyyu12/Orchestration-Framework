from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
)
from constructs import Construct
from infrastructure.api_stack import ApiStack
from infrastructure.database_stack import DatabaseStack

class MonitoringStack(Stack):
    def __init__(
        self, 
        scope: Construct, 
        id: str, 
        api_stack: ApiStack,
        database_stack: DatabaseStack,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Create SNS topic for alerts
        alerts_topic = sns.Topic(
            self, "AlertsTopic",
            display_name="ServerlessOrch Alerts"
        )
        
        # Create CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(
            self, "ServerlessOrchDashboard",
            dashboard_name="ServerlessOrch-Dashboard"
        )
        
        # Add API Gateway metrics
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="API Gateway Requests",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="Count",
                        dimension_map={
                            "ApiName": "OrdersApi"
                        },
                        statistic="Sum",
                        period=Duration.minutes(1)
                    )
                ]
            ),
            cloudwatch.GraphWidget(
                title="API Gateway Latency",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="Latency",
                        dimension_map={
                            "ApiName": "OrdersApi"
                        },
                        statistic="Average",
                        period=Duration.minutes(1)
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="Latency",
                        dimension_map={
                            "ApiName": "OrdersApi"
                        },
                        statistic="p99",
                        period=Duration.minutes(1)
                    )
                ]
            )
        )
        
        # Add Lambda metrics
        lambda_widgets = []
        for i, lambda_function in enumerate(api_stack.lambdas):
            lambda_name = lambda_function.function_name
            
            # Create Lambda duration and error widgets
            lambda_widgets.append(
                cloudwatch.GraphWidget(
                    title=f"{lambda_name} - Duration",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Duration",
                            dimension_map={
                                "FunctionName": lambda_name
                            },
                            statistic="Average",
                            period=Duration.minutes(1)
                        ),
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Duration",
                            dimension_map={
                                "FunctionName": lambda_name
                            },
                            statistic="p95",
                            period=Duration.minutes(1)
                        )
                    ]
                )
            )
            
            lambda_widgets.append(
                cloudwatch.GraphWidget(
                    title=f"{lambda_name} - Errors and Throttles",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Errors",
                            dimension_map={
                                "FunctionName": lambda_name
                            },
                            statistic="Sum",
                            period=Duration.minutes(1)
                        ),
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Throttles",
                            dimension_map={
                                "FunctionName": lambda_name
                            },
                            statistic="Sum",
                            period=Duration.minutes(1)
                        )
                    ]
                )
            )
            
            # Create alarms for high Lambda error rates
            error_alarm = cloudwatch.Alarm(
                self, f"{lambda_name}ErrorAlarm",
                metric=cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimension_map={
                        "FunctionName": lambda_name
                    },
                    statistic="Sum",
                    period=Duration.minutes(1)
                ),
                evaluation_periods=3,
                threshold=5,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                alarm_description=f"Alarm if {lambda_name} has more than 5 errors in 3 consecutive periods"
            )
            
            # Add alarm actions
            error_alarm.add_alarm_action(
                cloudwatch_actions.SnsAction(alerts_topic)
            )
        
        # Add Lambda metrics to dashboard in rows of 2
        for i in range(0, len(lambda_widgets), 2):
            widgets_row = lambda_widgets[i:i+2]
            if len(widgets_row) == 1:
                widgets_row.append(cloudwatch.GraphWidget(title="Empty"))
            dashboard.add_widgets(*widgets_row)
        
        # Add DynamoDB metrics
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="DynamoDB - Orders Table",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="ConsumedReadCapacityUnits",
                        dimension_map={
                            "TableName": database_stack.orders_table.table_name
                        },
                        statistic="Sum",
                        period=Duration.minutes(5)
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="ConsumedWriteCapacityUnits",
                        dimension_map={
                            "TableName": database_stack.orders_table.table_name
                        },
                        statistic="Sum",
                        period=Duration.minutes(5)
                    )
                ]
            ),
            cloudwatch.GraphWidget(
                title="DynamoDB - Inventory Table",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="ConsumedReadCapacityUnits",
                        dimension_map={
                            "TableName": database_stack.inventory_table.table_name
                        },
                        statistic="Sum",
                        period=Duration.minutes(5)
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/DynamoDB",
                        metric_name="ConsumedWriteCapacityUnits",
                        dimension_map={
                            "TableName": database_stack.inventory_table.table_name
                        },
                        statistic="Sum",
                        period=Duration.minutes(5)
                    )
                ]
            )
        )