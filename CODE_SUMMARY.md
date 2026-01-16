# Lumina Gallery - Complete Code Summary

## Project Structure

```
/app/
├── backend/
│   ├── .env                      # AWS credentials (CONFIGURE THIS!)
│   ├── config.py                 # Configuration management
│   ├── aws_services.py           # AWS S3, DynamoDB, Lambda services
│   ├── app.py                    # Flask API application
│   ├── wsgi_handler.py           # Lambda WSGI handler
│   ├── lambda_function.py        # Lambda image processor
│   ├── create_dynamodb_table.py  # DynamoDB table setup script
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js               # Main React app
│   │   ├── App.css              # Custom styles
│   │   ├── index.js             # React entry point
│   │   └── pages/
│   │       └── Gallery.jsx      # Main gallery component
│   ├── .env                     # Frontend configuration
│   └── package.json             # Node dependencies
├── deployment/
│   ├── template.yaml            # AWS SAM template
│   ├── lambda_deploy.sh         # Lambda deployment script
│   ├── create_lambda_role.sh    # IAM role creation script
│   └── api_gateway_deploy.sh    # API Gateway deployment guide
├── tests/
│   └── test_flask_api.py        # API unit tests
├── design_guidelines.json       # UI/UX design specifications
└── README.md                    # Complete documentation

```

---

## Backend Files

### 1. `/app/backend/.env` (CONFIGURE YOUR AWS CREDENTIALS HERE!)

```env
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET_NAME=lumina-gallery-images
DYNAMODB_TABLE_NAME=LuminaGalleryImages
CORS_ORIGINS=*
```

### 2. `/app/backend/config.py`

```python
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

class Config:
    """Application configuration"""
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'lumina-gallery-images')
    DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'LuminaGalleryImages')
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    
    # Lambda Configuration
    LAMBDA_FUNCTION_NAME = os.environ.get('LAMBDA_FUNCTION_NAME', 'image-processor')
    
    @staticmethod
    def validate():
        """Validate required configuration"""
        required = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION', 'S3_BUCKET_NAME']
        missing = [key for key in required if not os.environ.get(key)]
        if missing:
            print(f"Warning: Missing AWS configuration: {', '.join(missing)}")
            print("Please update .env file with your AWS credentials")
            return False
        return True
```

### 3. `/app/backend/aws_services.py`

```python
import boto3
from botocore.exceptions import ClientError
from config import Config
import logging

logger = logging.getLogger(__name__)

class AWSServices:
    """AWS Services Manager for S3 and DynamoDB operations"""
    
    def __init__(self):
        self.s3_client = None
        self.dynamodb = None
        self.dynamodb_table = None
        self.lambda_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize AWS service clients"""
        try:
            # S3 Client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                region_name=Config.AWS_REGION
            )
            
            # DynamoDB Resource
            self.dynamodb = boto3.resource(
                'dynamodb',
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                region_name=Config.AWS_REGION
            )
            self.dynamodb_table = self.dynamodb.Table(Config.DYNAMODB_TABLE_NAME)
            
            # Lambda Client
            self.lambda_client = boto3.client(
                'lambda',
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                region_name=Config.AWS_REGION
            )
            
            logger.info("AWS clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
    
    # S3 Operations
    def upload_to_s3(self, file_obj, file_name, content_type):
        """Upload file to S3 bucket"""
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                Config.S3_BUCKET_NAME,
                file_name,
                ExtraArgs={'ContentType': content_type}
            )
            return True
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return False
    
    def download_from_s3(self, file_name):
        """Download file from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=Config.S3_BUCKET_NAME,
                Key=file_name
            )
            return response['Body'].read(), response['ContentType']
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            return None, None
    
    def delete_from_s3(self, file_name):
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=Config.S3_BUCKET_NAME,
                Key=file_name
            )
            return True
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            return False
    
    # DynamoDB Operations
    def put_item(self, item):
        """Put item in DynamoDB table"""
        try:
            self.dynamodb_table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"DynamoDB put_item failed: {e}")
            return False
    
    def get_item(self, image_id):
        """Get item from DynamoDB table"""
        try:
            response = self.dynamodb_table.get_item(Key={'id': image_id})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"DynamoDB get_item failed: {e}")
            return None
    
    def scan_items(self, filter_expression=None, expression_values=None):
        """Scan DynamoDB table with optional filter"""
        try:
            if filter_expression and expression_values:
                response = self.dynamodb_table.scan(
                    FilterExpression=filter_expression,
                    ExpressionAttributeValues=expression_values
                )
            else:
                response = self.dynamodb_table.scan()
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"DynamoDB scan failed: {e}")
            return []
    
    def delete_item(self, image_id):
        """Delete item from DynamoDB table"""
        try:
            self.dynamodb_table.delete_item(Key={'id': image_id})
            return True
        except ClientError as e:
            logger.error(f"DynamoDB delete_item failed: {e}")
            return False
    
    # Lambda Operations
    def invoke_lambda(self, function_name, payload):
        """Invoke Lambda function"""
        try:
            import json
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            result = json.loads(response['Payload'].read())
            return result
        except ClientError as e:
            logger.error(f"Lambda invocation failed: {e}")
            return None

# Global instance
aws_services = AWSServices()
```

### 4. `/app/backend/app.py` (Main Flask API)

```python
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import uuid
from datetime import datetime, timezone
import logging
from io import BytesIO
from config import Config
from aws_services import aws_services

app = Flask(__name__)
CORS(app, origins=Config.CORS_ORIGINS.split(','))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate configuration on startup
Config.validate()


@app.route('/api/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        'message': 'Lumina Gallery API',
        'version': '1.0.0',
        'services': 'Flask + AWS S3 + DynamoDB'
    })


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()})


@app.route('/api/images/upload', methods=['POST'])
def upload_image():
    """
    Upload image with metadata to S3 and DynamoDB
    
    Form Data:
    - file: Image file (required)
    - uploader: Uploader name (required)
    - tags: Comma-separated tags (optional)
    - description: Image description (optional)
    """
    try:
        # Validate file
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate content type
        if not file.content_type or not file.content_type.startswith('image/'):
            return jsonify({'error': 'Only image files are allowed'}), 400
        
        # Get metadata
        uploader = request.form.get('uploader')
        if not uploader:
            return jsonify({'error': 'Uploader name is required'}), 400
        
        tags = request.form.get('tags', '')
        description = request.form.get('description')
        
        # Generate unique ID and filename
        image_id = str(uuid.uuid4())
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
        s3_key = f"{image_id}.{file_extension}"
        
        # Upload to S3
        file.seek(0)
        if not aws_services.upload_to_s3(file, s3_key, file.content_type):
            return jsonify({'error': 'Failed to upload image to S3'}), 500
        
        # Get file size
        file.seek(0, 2)
        file_size = file.tell()
        
        # Parse tags
        tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []
        
        # Create metadata
        upload_date = datetime.now(timezone.utc).isoformat()
        metadata = {
            'id': image_id,
            'filename': file.filename,
            's3_key': s3_key,
            'file_size': file_size,
            'file_type': file.content_type,
            'uploader': uploader,
            'tags': tags_list,
            'description': description,
            'upload_date': upload_date
        }
        
        # Save to DynamoDB
        if not aws_services.put_item(metadata):
            # Rollback: delete from S3
            aws_services.delete_from_s3(s3_key)
            return jsonify({'error': 'Failed to save metadata to DynamoDB'}), 500
        
        # Invoke Lambda for image processing (thumbnail generation)
        try:
            lambda_payload = {
                'bucket': Config.S3_BUCKET_NAME,
                's3_key': s3_key,
                'image_id': image_id
            }
            aws_services.invoke_lambda(Config.LAMBDA_FUNCTION_NAME, lambda_payload)
        except Exception as e:
            logger.warning(f"Lambda invocation failed (non-critical): {e}")
        
        # Return response
        return jsonify({
            'id': image_id,
            'filename': file.filename,
            'file_size': file_size,
            'file_type': file.content_type,
            'uploader': uploader,
            'tags': tags_list,
            'description': description,
            'upload_date': upload_date,
            'url': f'/api/images/{image_id}/file'
        }), 201
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/images', methods=['GET'])
def list_images():
    """
    List all images with optional filters
    
    Query Parameters:
    - date_from: ISO format date string
    - date_to: ISO format date string
    - uploader: Filter by uploader name
    - tags: Comma-separated tags
    """
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        uploader = request.args.get('uploader')
        tags = request.args.get('tags')
        
        # Fetch all items from DynamoDB
        items = aws_services.scan_items()
        
        # Apply filters
        filtered_items = []
        for item in items:
            # Date range filter
            if date_from and item.get('upload_date', '') < date_from:
                continue
            if date_to and item.get('upload_date', '') > date_to:
                continue
            
            # Uploader filter
            if uploader and item.get('uploader') != uploader:
                continue
            
            # Tags filter
            if tags:
                search_tags = [t.strip() for t in tags.split(',') if t.strip()]
                item_tags = item.get('tags', [])
                if not any(tag in item_tags for tag in search_tags):
                    continue
            
            filtered_items.append(item)
        
        # Sort by upload date (newest first)
        filtered_items.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
        
        # Add URL to each item
        for item in filtered_items:
            item['url'] = f"/api/images/{item['id']}/file"
        
        return jsonify(filtered_items), 200
    
    except Exception as e:
        logger.error(f"List images error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/images/<image_id>', methods=['GET'])
def get_image(image_id):
    """
    Get metadata for a specific image
    """
    try:
        item = aws_services.get_item(image_id)
        
        if not item:
            return jsonify({'error': 'Image not found'}), 404
        
        item['url'] = f"/api/images/{image_id}/file"
        return jsonify(item), 200
    
    except Exception as e:
        logger.error(f"Get image error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/images/<image_id>/file', methods=['GET'])
def download_image(image_id):
    """
    Download or view the actual image file from S3
    """
    try:
        # Get metadata from DynamoDB
        item = aws_services.get_item(image_id)
        
        if not item:
            return jsonify({'error': 'Image not found'}), 404
        
        s3_key = item.get('s3_key')
        filename = item.get('filename')
        
        # Download from S3
        file_data, content_type = aws_services.download_from_s3(s3_key)
        
        if not file_data:
            return jsonify({'error': 'Failed to download image from S3'}), 500
        
        # Return file
        return send_file(
            BytesIO(file_data),
            mimetype=content_type,
            as_attachment=False,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Download image error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/images/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    """
    Delete an image from S3 and DynamoDB
    """
    try:
        # Get metadata from DynamoDB
        item = aws_services.get_item(image_id)
        
        if not item:
            return jsonify({'error': 'Image not found'}), 404
        
        s3_key = item.get('s3_key')
        
        # Delete from S3
        if not aws_services.delete_from_s3(s3_key):
            logger.error(f"Failed to delete from S3: {s3_key}")
        
        # Delete from DynamoDB
        if not aws_services.delete_item(image_id):
            return jsonify({'error': 'Failed to delete image metadata'}), 500
        
        return jsonify({
            'message': 'Image deleted successfully',
            'id': image_id
        }), 200
    
    except Exception as e:
        logger.error(f"Delete image error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=True)
```

### 5. `/app/backend/lambda_function.py` (Image Processor)

```python
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
```

### 6. `/app/backend/create_dynamodb_table.py`

```python
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
```

### 7. `/app/backend/requirements.txt`

```
Flask==3.0.0
flask-cors==4.0.0
boto3==1.34.129
python-dotenv==1.0.1
Pillow==12.1.0
pytest==9.0.2
pytest-flask==1.3.0
requests==2.31.0
```

---

## Setup & Usage Instructions

### Step 1: Configure AWS Credentials

Edit `/app/backend/.env`:
```bash
AWS_ACCESS_KEY_ID=YOUR_ACTUAL_KEY
AWS_SECRET_ACCESS_KEY=YOUR_ACTUAL_SECRET
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
DYNAMODB_TABLE_NAME=LuminaGalleryImages
```

### Step 2: Create AWS Resources

```bash
# Create S3 bucket
aws s3 mb s3://your-bucket-name --region us-east-1

# Create DynamoDB table
cd /app/backend
python create_dynamodb_table.py
```

### Step 3: Run Flask API Locally

```bash
cd /app/backend
python app.py
# API available at http://localhost:8001/api
```

### Step 4: Test APIs with cURL

```bash
# Health check
curl http://localhost:8001/api/health

# Upload image
curl -X POST http://localhost:8001/api/images/upload \
  -F "file=@test.jpg" \
  -F "uploader=John Doe" \
  -F "tags=nature,landscape" \
  -F "description=Beautiful scene"

# List images
curl http://localhost:8001/api/images

# Get specific image
curl http://localhost:8001/api/images/{IMAGE_ID}

# Delete image
curl -X DELETE http://localhost:8001/api/images/{IMAGE_ID}
```

### Step 5: Deploy to AWS Lambda (Optional)

```bash
# Create IAM role
cd /app/deployment
./create_lambda_role.sh

# Deploy Lambda function
./lambda_deploy.sh

# Deploy API with SAM
sam build
sam deploy --guided
```

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/` | Root endpoint |
| GET | `/api/health` | Health check |
| POST | `/api/images/upload` | Upload image |
| GET | `/api/images` | List images with filters |
| GET | `/api/images/{id}` | Get image metadata |
| GET | `/api/images/{id}/file` | Download image |
| DELETE | `/api/images/{id}` | Delete image |

---

## Key Features

✅ **Flask API** with AWS integration
✅ **S3** for image storage
✅ **DynamoDB** for metadata
✅ **Lambda** for image processing (thumbnails)
✅ **API Gateway** deployment ready
✅ **Complete documentation** in README.md
✅ **Unit tests** with mocked AWS services
✅ **React frontend** with Instagram-like UI
✅ **Multiple filters**: date range, uploader, tags

---

## Files Location Reference

All code is in `/app/` directory:
- Backend: `/app/backend/`
- Frontend: `/app/frontend/src/`
- Tests: `/app/tests/`
- Deployment: `/app/deployment/`
- Documentation: `/app/README.md`
