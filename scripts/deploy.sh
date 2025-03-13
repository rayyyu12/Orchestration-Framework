#!/bin/bash
set -e

# Default environment if not specified
ENVIRONMENT=${1:-dev}
REGION=${2:-us-east-1}

echo "Deploying ServerlessOrch to $ENVIRONMENT environment in $REGION region"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Bootstrap CDK (if needed)
echo "Bootstrapping CDK in account..."
cdk bootstrap aws://$AWS_ACCOUNT/$REGION

# Deploy with CDK
echo "Deploying with CDK..."
cdk deploy --all --require-approval never

echo "Deployment completed successfully!"

# Output API endpoint
echo "API Gateway endpoint URL:"
aws cloudformation describe-stacks \
    --stack-name serverless-orch-api \
    --query "Stacks[0].Outputs[?OutputKey=='OrdersApiEndpoint'].OutputValue" \
    --output text \
    --region $REGION

echo ""
echo "Dashboard URL:"
echo "https://$REGION.console.aws.amazon.com/cloudwatch/home?region=$REGION#dashboards:name=ServerlessOrch-Dashboard"

echo ""
echo "Cleanup instructions:"
echo "When you're done with the project, run: cdk destroy --all"