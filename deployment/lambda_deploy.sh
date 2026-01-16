#!/bin/bash
# Lambda Deployment Script

set -e

echo "===================================="
echo "Lambda Function Deployment Script"
echo "===================================="
echo ""

# Configuration
LAMBDA_FUNCTION_NAME="lumina-image-processor"
LAMBDA_RUNTIME="python3.11"
LAMBDA_HANDLER="lambda_function.lambda_handler"
LAMBDA_ROLE_NAME="LuminaGalleryLambdaRole"
LAMBDA_TIMEOUT=60
LAMBDA_MEMORY=512

echo "Function Name: $LAMBDA_FUNCTION_NAME"
echo "Runtime: $LAMBDA_RUNTIME"
echo ""

# Create deployment package
echo "Creating deployment package..."
cd ../backend

# Create temporary directory
mkdir -p lambda_package
cd lambda_package

# Copy lambda function
cp ../lambda_function.py .

# Install dependencies
echo "Installing dependencies..."
pip install Pillow boto3 -t .

# Create ZIP file
echo "Creating ZIP package..."
zip -r ../lambda_function.zip .

# Clean up
cd ..
rm -rf lambda_package

echo "Package created: lambda_function.zip"
echo ""

# Check if function exists
echo "Checking if Lambda function exists..."
if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME 2>/dev/null; then
    echo "Function exists. Updating..."
    aws lambda update-function-code \
        --function-name $LAMBDA_FUNCTION_NAME \
        --zip-file fileb://lambda_function.zip
    echo "Lambda function updated successfully!"
else
    echo "Function does not exist. Creating..."
    
    # Get IAM role ARN
    ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")
    
    if [ -z "$ROLE_ARN" ]; then
        echo "Error: IAM role '$LAMBDA_ROLE_NAME' not found."
        echo "Please create the IAM role first using create_lambda_role.sh"
        exit 1
    fi
    
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --runtime $LAMBDA_RUNTIME \
        --role $ROLE_ARN \
        --handler $LAMBDA_HANDLER \
        --zip-file fileb://lambda_function.zip \
        --timeout $LAMBDA_TIMEOUT \
        --memory-size $LAMBDA_MEMORY \
        --environment Variables='{DYNAMODB_TABLE_NAME=LuminaGalleryImages}'
    
    echo "Lambda function created successfully!"
fi

echo ""
echo "Deployment complete!"
echo "Function ARN: $(aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --query 'Configuration.FunctionArn' --output text)"