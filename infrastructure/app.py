#!/usr/bin/env python3
import os
from aws_cdk import App, Environment
from infrastructure.api_stack import ApiStack
from infrastructure.database_stack import DatabaseStack
from infrastructure.monitoring_stack import MonitoringStack

app = App()

# Define deployment environment
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", "123456789012"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
)

# Project name for resource naming
project_name = "serverless-orch"

# Create the stacks
database_stack = DatabaseStack(app, f"{project_name}-database", env=env)
api_stack = ApiStack(
    app, 
    f"{project_name}-api", 
    env=env,
    orders_table=database_stack.orders_table,
    inventory_table=database_stack.inventory_table
)
monitoring_stack = MonitoringStack(
    app,
    f"{project_name}-monitoring",
    env=env,
    api_stack=api_stack,
    database_stack=database_stack
)

# Add tags to all resources
for stack in [database_stack, api_stack, monitoring_stack]:
    stack.add_tags({
        "Project": project_name,
        "Environment": "dev",
        "ManagedBy": "CDK"
    })

app.synth()