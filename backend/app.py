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