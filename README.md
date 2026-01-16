# Lumina Gallery API Documentation

## Overview

Lumina Gallery is an Instagram-like image management service built with Flask, AWS S3, DynamoDB, and Lambda functions. It provides a complete solution for image upload, storage, retrieval, and management.

## Architecture

```
┌─────────────┐
│   Frontend  │
│  (React)    │
└──────┬──────┘
       │
       ├─────────────────────────────┐
       │                             │
┌──────▼──────┐              ┌───────▼────────┐
│ API Gateway │              │  CloudFront    │
│             │              │  (Static)      │
└──────┬──────┘              └────────────────┘
       │
┌──────▼──────┐
│   Lambda    │
│ (Flask API) │
└──────┬──────┘
       │
       ├────────────────┬─────────────────┬──────────────┐
       │                │                 │              │
┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼───────┐  ┌──▼─────┐
│     S3      │  │  DynamoDB   │  │   Lambda     │  │ Others │
│  (Images)   │  │  (Metadata) │  │ (Processor)  │  │        │
└─────────────┘  └─────────────┘  └──────────────┘  └────────┘
```

## Tech Stack

- **Backend**: Flask (Python 3.11)
- **Storage**: AWS S3 (images), DynamoDB (metadata)
- **Processing**: AWS Lambda (thumbnail generation, image processing)
- **Deployment**: AWS Lambda + API Gateway
- **Frontend**: React with Tailwind CSS

## API Endpoints

### Base URL
```
Local: http://localhost:8001/api
Production: https://<api-gateway-id>.execute-api.<region>.amazonaws.com/prod/api
```

### 1. Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-16T10:00:00Z"
}
```

---

### 2. Upload Image
```http
POST /api/images/upload
```

**Headers:**
```
Content-Type: multipart/form-data
```

**Form Data:**
- `file` (required): Image file
- `uploader` (required): Name of the uploader
- `tags` (optional): Comma-separated tags
- `description` (optional): Image description

**Example Request (cURL):**
```bash
curl -X POST http://localhost:8001/api/images/upload \
  -F "file=@/path/to/image.jpg" \
  -F "uploader=John Doe" \
  -F "tags=nature,landscape,mountain" \
  -F "description=Beautiful mountain landscape"
```

**Response (201 Created):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "mountain.jpg",
  "file_size": 2048576,
  "file_type": "image/jpeg",
  "uploader": "John Doe",
  "tags": ["nature", "landscape", "mountain"],
  "description": "Beautiful mountain landscape",
  "upload_date": "2025-01-16T10:00:00+00:00",
  "url": "/api/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890/file"
}
```

---

### 3. List All Images
```http
GET /api/images
```

**Query Parameters:**
- `date_from` (optional): Filter by upload date (ISO format)
- `date_to` (optional): Filter by upload date (ISO format)
- `uploader` (optional): Filter by uploader name
- `tags` (optional): Filter by tags (comma-separated)

**Example Requests:**
```bash
# Get all images
curl http://localhost:8001/api/images

# Filter by uploader
curl "http://localhost:8001/api/images?uploader=John%20Doe"

# Filter by tags
curl "http://localhost:8001/api/images?tags=nature,landscape"

# Filter by date range
curl "http://localhost:8001/api/images?date_from=2025-01-01T00:00:00Z&date_to=2025-01-31T23:59:59Z"

# Combined filters
curl "http://localhost:8001/api/images?uploader=John%20Doe&tags=nature"
```

**Response (200 OK):**
```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "filename": "mountain.jpg",
    "file_size": 2048576,
    "file_type": "image/jpeg",
    "uploader": "John Doe",
    "tags": ["nature", "landscape"],
    "description": "Beautiful landscape",
    "upload_date": "2025-01-16T10:00:00+00:00",
    "url": "/api/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890/file"
  }
]
```

---

### 4. Get Image Metadata
```http
GET /api/images/{image_id}
```

**Example Request:**
```bash
curl http://localhost:8001/api/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response (200 OK):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "mountain.jpg",
  "s3_key": "a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg",
  "file_size": 2048576,
  "file_type": "image/jpeg",
  "uploader": "John Doe",
  "tags": ["nature", "landscape"],
  "description": "Beautiful landscape",
  "upload_date": "2025-01-16T10:00:00+00:00",
  "url": "/api/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890/file"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Image not found"
}
```

---

### 5. Download/View Image
```http
GET /api/images/{image_id}/file
```

**Example Request:**
```bash
# View in browser
open http://localhost:8001/api/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890/file

# Download with cURL
curl -O http://localhost:8001/api/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890/file
```

**Response (200 OK):**
Binary image data with appropriate `Content-Type` header

---

### 6. Delete Image
```http
DELETE /api/images/{image_id}
```

**Example Request:**
```bash
curl -X DELETE http://localhost:8001/api/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response (200 OK):**
```json
{
  "message": "Image deleted successfully",
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Image not found"
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error message description"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (invalid input)
- `404` - Not Found
- `500` - Internal Server Error

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- AWS Account with credentials
- AWS CLI configured
- Node.js 18+ (for frontend)

### Backend Setup

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Configure AWS credentials:**
Update `backend/.env` with your AWS credentials:
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
DYNAMODB_TABLE_NAME=LuminaGalleryImages
```

3. **Create S3 bucket:**
```bash
aws s3 mb s3://your-bucket-name --region us-east-1
```

4. **Create DynamoDB table:**
```bash
python create_dynamodb_table.py
```

5. **Run the Flask application:**
```bash
python app.py
```

The API will be available at `http://localhost:8001/api`

### Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
yarn install
```

2. **Configure backend URL:**
Update `frontend/.env` with your backend URL:
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

3. **Start the development server:**
```bash
yarn start
```

The frontend will be available at `http://localhost:3000`

---

## AWS Lambda Deployment

### Deploy Image Processor Lambda

1. **Create IAM role:**
```bash
cd deployment
chmod +x create_lambda_role.sh
./create_lambda_role.sh
```

2. **Deploy Lambda function:**
```bash
chmod +x lambda_deploy.sh
./lambda_deploy.sh
```

### Deploy Flask API to Lambda + API Gateway

**Option 1: AWS SAM (Recommended)**
```bash
# Install AWS SAM CLI
pip install aws-sam-cli

# Deploy
cd deployment
sam build
sam deploy --guided
```

**Option 2: Zappa**
```bash
# Install Zappa
pip install zappa

# Initialize and deploy
cd backend
zappa init
zappa deploy production
```

---

## Testing

### Run Unit Tests
```bash
cd tests
pytest test_flask_api.py -v
```

### Test with cURL

**Upload an image:**
```bash
curl -X POST http://localhost:8001/api/images/upload \
  -F "file=@test.jpg" \
  -F "uploader=Test User" \
  -F "tags=test,demo"
```

**List images:**
```bash
curl http://localhost:8001/api/images
```

**Get specific image:**
```bash
curl http://localhost:8001/api/images/{image_id}
```

**Delete image:**
```bash
curl -X DELETE http://localhost:8001/api/images/{image_id}
```

---

## Lambda Function Details

The image processor Lambda function (`lambda_function.py`) performs:

1. **Thumbnail Generation**: Creates 300x300 thumbnails
2. **Metadata Extraction**: Extracts image dimensions
3. **DynamoDB Update**: Updates image record with processing info

**Invocation:**
The Lambda function is automatically invoked after image upload. You can also invoke it manually:

```bash
aws lambda invoke \
  --function-name lumina-image-processor \
  --payload '{"bucket":"your-bucket","s3_key":"image.jpg","image_id":"uuid"}' \
  response.json
```

---

## Best Practices

1. **Security**:
   - Never commit AWS credentials to version control
   - Use IAM roles with minimum required permissions
   - Enable S3 bucket encryption
   - Use pre-signed URLs for secure image access

2. **Performance**:
   - Enable CloudFront CDN for image delivery
   - Use DynamoDB on-demand billing for variable workloads
   - Implement pagination for large image collections
   - Use S3 Transfer Acceleration for faster uploads

3. **Cost Optimization**:
   - Set S3 lifecycle policies to move old images to Glacier
   - Use Lambda provisioned concurrency only if needed
   - Monitor DynamoDB read/write capacity

4. **Monitoring**:
   - Enable CloudWatch logs for Lambda functions
   - Set up CloudWatch alarms for API errors
   - Track S3 bucket metrics
   - Monitor DynamoDB performance

---

## Troubleshooting

### Issue: AWS credentials not found
**Solution**: Ensure `.env` file has correct AWS credentials or use AWS CLI default profile.

### Issue: DynamoDB table doesn't exist
**Solution**: Run `python create_dynamodb_table.py` to create the table.

### Issue: S3 bucket access denied
**Solution**: Check IAM permissions for S3 access. Ensure bucket policy allows your IAM user/role.

### Issue: Lambda function timeout
**Solution**: Increase Lambda timeout in `template.yaml` or AWS console (max 15 minutes).

### Issue: CORS errors in frontend
**Solution**: Verify CORS configuration in Flask app and API Gateway.

---

## License

MIT License

## Support

For issues and questions, please open an issue on the GitHub repository.