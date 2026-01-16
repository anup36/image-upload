"""AWS Lambda Function for Image Processing

This Lambda function processes uploaded images:
- Generates thumbnails
- Validates image format
- Extracts metadata
- Updates DynamoDB with processed info

Deploy this to AWS Lambda and configure S3 trigger or invoke from API.
"""

import json
import boto3
from PIL import Image
import io
import os

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """
    Lambda handler for image processing
    
    Event format:
    {
        "bucket": "bucket-name",
        "s3_key": "image-key",
        "image_id": "uuid"
    }
    """
    try:
        # Parse event
        bucket = event.get('bucket')
        s3_key = event.get('s3_key')
        image_id = event.get('image_id')
        
        if not all([bucket, s3_key, image_id]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Download image from S3
        response = s3_client.get_object(Bucket=bucket, Key=s3_key)
        image_data = response['Body'].read()
        
        # Open image with PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Get image dimensions
        width, height = image.size
        
        # Generate thumbnail
        thumbnail_key = f"thumbnails/{s3_key}"
        thumbnail = image.copy()
        thumbnail.thumbnail((300, 300), Image.Resampling.LANCZOS)
        
        # Save thumbnail to buffer
        thumbnail_buffer = io.BytesIO()
        thumbnail.save(thumbnail_buffer, format=image.format or 'JPEG')
        thumbnail_buffer.seek(0)
        
        # Upload thumbnail to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=thumbnail_key,
            Body=thumbnail_buffer,
            ContentType=response['ContentType']
        )
        
        # Update DynamoDB with processing info
        table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'LuminaGalleryImages')
        table = dynamodb.Table(table_name)
        
        table.update_item(
            Key={'id': image_id},
            UpdateExpression='SET width = :w, height = :h, thumbnail_key = :t, processed = :p',
            ExpressionAttributeValues={
                ':w': width,
                ':h': height,
                ':t': thumbnail_key,
                ':p': True
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Image processed successfully',
                'image_id': image_id,
                'dimensions': {'width': width, 'height': height},
                'thumbnail_key': thumbnail_key
            })
        }
    
    except Exception as e:
        print(f"Error processing image: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }