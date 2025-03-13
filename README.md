# ServerlessOrch - Serverless API Orchestration Framework

A scalable serverless application framework for processing e-commerce orders, built with AWS Lambda, API Gateway, DynamoDB, and CloudWatch.

## Features

- **Serverless Architecture**: Built on AWS Lambda and API Gateway for automatic scaling
- **Event-Driven Processing**: DynamoDB streams trigger Lambda functions for asynchronous processing
- **Fault Tolerance**: Error handling and retry mechanisms for reliable processing
- **Real-Time Monitoring**: CloudWatch dashboards and alarms for performance monitoring
- **Infrastructure as Code**: AWS CDK for automated deployment and resource management

## Architecture

The framework consists of the following components:

1. **API Gateway**: Exposes RESTful endpoints for order management
2. **Lambda Functions**:
   - Order API: Handles API requests for creating and retrieving orders
   - Order Validator: Validates order details
   - Inventory Service: Checks product availability
   - Payment Service: Processes payments (mocked)
   - Order Fulfillment: Prepares orders for shipping
   - Notification Service: Sends customer notifications (mocked)
   - Stream Processor: Orchestrates the workflow based on DynamoDB streams
3. **DynamoDB**: Stores order and inventory data
4. **CloudWatch**: Monitors system performance and errors

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Python 3.9 or higher
- Node.js 14 or higher (for CDK)

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/serverless-orch.git
   cd serverless-orch
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Deploy to AWS**:
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

   This script will:
   - Create required virtual environment (if it doesn't exist)
   - Install dependencies
   - Bootstrap CDK in your AWS account
   - Deploy all stacks (API, Database, Monitoring)
   - Output the API endpoint URL and CloudWatch Dashboard URL

## Running Local Tests

1. **Start DynamoDB Local** (if you want to test locally):
   ```bash
   docker run -p 8000:8000 amazon/dynamodb-local
   ```

2. **Set up local tables**:
   ```bash
   python scripts/local_test.py --setup-db
   ```

3. **Run test script with your API endpoint**:
   ```bash
   python scripts/local_test.py --api-url https://your-api-id.execute-api.us-east-1.amazonaws.com/dev
   ```

## API Endpoints

- **POST /orders**: Create a new order
  ```json
  {
    "customer": {
      "customer_id": "cust-12345",
      "email": "customer@example.com",
      "name": "John Doe"
    },
    "items": [
      {
        "product_id": "product-1",
        "quantity": 2,
        "unit_price": 19.99
      }
    ],
    "shipping_address": {
      "street": "123 Main St",
      "city": "Anytown",
      "state": "CA",
      "postal_code": "12345",
      "country": "US"
    },
    "payment": {
      "payment_method": "credit_card"
    }
  }
  ```

- **GET /orders**: List all orders
  - Optional query parameters:
    - `status`: Filter by order status
    - `limit`: Maximum number of orders to return

- **GET /orders/{orderId}**: Get details of a specific order

## Order Processing Flow

1. Customer submits an order via API Gateway
2. Order Validator checks order details
3. Inventory Service checks product availability
4. Payment Service processes the payment
5. Order Fulfillment updates inventory and prepares order for shipping
6. Notification Service sends confirmation to the customer
7. Order is marked as completed

## Monitoring and Observability

The framework includes a CloudWatch Dashboard that provides visibility into:

- API Gateway request volume and latency
- Lambda function duration, errors, and throttles
- DynamoDB read/write capacity utilization

CloudWatch Alarms are configured to notify of any issues with Lambda functions.

## Cost Optimization

This project is designed to be cost-effective:

- All services use AWS Free Tier limits where possible
- DynamoDB tables use on-demand capacity for cost efficiency
- TTL is configured for order records to avoid unnecessary storage costs
- Lambda functions are sized appropriately for their workload

## Cleanup

To avoid incurring any costs, you can remove all resources:

```bash
cdk destroy --all
```

## Extending the Framework

### Adding New Services

1. Create a new Lambda function in `app/functions/`
2. Add the function to the `ApiStack` in `infrastructure/api_stack.py`
3. Update the stream processor to trigger the new function at the appropriate step

### Customizing Business Logic

- Modify the order processing rules in the validator function
- Add additional validation steps or business rules as needed
- Integrate with real payment processors or shipping providers

## License

This project is licensed under the MIT License - see the LICENSE file for details.