#!/usr/bin/env python3
"""Script to create DynamoDB table for Lumina Gallery"""

import boto3
from botocore.exceptions import ClientError
from config import Config
import sys

def create_table():
    """
    Create DynamoDB table with the following schema:
    - Primary Key: id (String)
    - Attributes: filename, s3_key, file_size, file_type, uploader, tags, description, upload_date
    """
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
        
        table_name = Config.DYNAMODB_TABLE_NAME
        
        # Check if table already exists
        try:
            existing_table = dynamodb.Table(table_name)
            existing_table.load()
            print(f"Table '{table_name}' already exists!")
            print(f"Table status: {existing_table.table_status}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Create table
        print(f"Creating DynamoDB table: {table_name}...")
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'  # String
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand billing
        )
        
        # Wait for table to be created
        print("Waiting for table to be created...")
        table.wait_until_exists()
        
        print(f"Table '{table_name}' created successfully!")
        print(f"Table ARN: {table.table_arn}")
        print(f"Table status: {table.table_status}")
        return True
    
    except ClientError as e:
        print(f"Error creating DynamoDB table: {e}")
        print(f"Error code: {e.response['Error']['Code']}")
        print(f"Error message: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == '__main__':
    if not Config.validate():
        print("\nPlease update backend/.env with your AWS credentials before running this script.")
        sys.exit(1)
    
    print("DynamoDB Table Creation Script")
    print("=" * 50)
    print(f"Region: {Config.AWS_REGION}")
    print(f"Table Name: {Config.DYNAMODB_TABLE_NAME}")
    print("=" * 50)
    print()
    
    if create_table():
        print("\nSuccess! Your DynamoDB table is ready.")
        sys.exit(0)
    else:
        print("\nFailed to create DynamoDB table.")
        sys.exit(1)