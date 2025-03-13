import os

# DynamoDB table names
ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "OrdersTable")
INVENTORY_TABLE = os.environ.get("INVENTORY_TABLE", "InventoryTable")

# API settings
API_RATE_LIMIT = 100  # requests per second
API_BURST_LIMIT = 50

# Lambda settings
DEFAULT_LAMBDA_TIMEOUT = 10  # seconds
DEFAULT_LAMBDA_MEMORY = 256  # MB

# Business logic settings
ORDER_EXPIRY_DAYS = 7  # TTL for orders in DynamoDB

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Common settings for development/testing
IS_LOCAL = os.environ.get("AWS_SAM_LOCAL") == "true"