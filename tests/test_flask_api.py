import pytest
import json
import os
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from app import app

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_aws():
    """Mock AWS services"""
    with patch('aws_services.aws_services') as mock:
        # Mock S3 operations
        mock.upload_to_s3 = Mock(return_value=True)
        mock.get_s3_url = Mock(return_value='https://s3.amazonaws.com/bucket/image.jpg')
        mock.download_from_s3 = Mock(return_value=(b'fake_image_data', 'image/jpeg'))
        mock.delete_from_s3 = Mock(return_value=True)
        
        # Mock DynamoDB operations
        mock.put_item = Mock(return_value=True)
        mock.get_item = Mock(return_value={
            'id': 'test-id',
            'filename': 'test.jpg',
            's3_key': 'test-id.jpg',
            'file_size': 1024,
            'file_type': 'image/jpeg',
            'uploader': 'Test User',
            'tags': ['test'],
            'description': 'Test image',
            'upload_date': '2025-01-01T00:00:00+00:00'
        })
        mock.scan_items = Mock(return_value=[
            {
                'id': 'test-id-1',
                'filename': 'test1.jpg',
                's3_key': 'test-id-1.jpg',
                'file_size': 1024,
                'file_type': 'image/jpeg',
                'uploader': 'User1',
                'tags': ['nature'],
                'upload_date': '2025-01-01T00:00:00+00:00'
            },
            {
                'id': 'test-id-2',
                'filename': 'test2.jpg',
                's3_key': 'test-id-2.jpg',
                'file_size': 2048,
                'file_type': 'image/jpeg',
                'uploader': 'User2',
                'tags': ['urban'],
                'upload_date': '2025-01-02T00:00:00+00:00'
            }
        ])
        mock.delete_item = Mock(return_value=True)
        mock.invoke_lambda = Mock(return_value={'statusCode': 200})
        
        yield mock

def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get('/api/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data
    assert data['message'] == 'Lumina Gallery API'

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

@patch('app.aws_services')
def test_upload_image(mock_aws_module, client):
    """Test image upload"""
    # Setup mocks
    mock_aws_module.upload_to_s3.return_value = True
    mock_aws_module.put_item.return_value = True
    mock_aws_module.invoke_lambda.return_value = {'statusCode': 200}
    
    data = {
        'file': (BytesIO(b'fake image data'), 'test.jpg'),
        'uploader': 'Test User',
        'tags': 'test, nature',
        'description': 'Test image'
    }
    
    response = client.post('/api/images/upload', 
                          data=data,
                          content_type='multipart/form-data')
    
    assert response.status_code == 201
    result = json.loads(response.data)
    assert result['uploader'] == 'Test User'
    assert 'test' in result['tags']
    assert 'nature' in result['tags']

@patch('app.aws_services')
def test_upload_no_file(mock_aws_module, client):
    """Test upload without file"""
    response = client.post('/api/images/upload', 
                          data={'uploader': 'Test'},
                          content_type='multipart/form-data')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

@patch('app.aws_services')
def test_upload_no_uploader(mock_aws_module, client):
    """Test upload without uploader"""
    data = {
        'file': (BytesIO(b'fake image data'), 'test.jpg')
    }
    
    response = client.post('/api/images/upload',
                          data=data,
                          content_type='multipart/form-data')
    
    assert response.status_code == 400
    result = json.loads(response.data)
    assert 'error' in result

@patch('app.aws_services')
def test_list_images(mock_aws_module, client):
    """Test listing images"""
    mock_aws_module.scan_items.return_value = [
        {
            'id': 'test-id',
            'filename': 'test.jpg',
            'uploader': 'Test User',
            'tags': ['test'],
            'upload_date': '2025-01-01T00:00:00+00:00'
        }
    ]
    
    response = client.get('/api/images')
    assert response.status_code == 200
    
    images = json.loads(response.data)
    assert len(images) >= 1
    assert images[0]['uploader'] == 'Test User'

@patch('app.aws_services')
def test_filter_by_uploader(mock_aws_module, client):
    """Test filtering by uploader"""
    mock_aws_module.scan_items.return_value = [
        {'id': '1', 'uploader': 'User1', 'upload_date': '2025-01-01T00:00:00+00:00', 'tags': []},
        {'id': '2', 'uploader': 'User2', 'upload_date': '2025-01-02T00:00:00+00:00', 'tags': []}
    ]
    
    response = client.get('/api/images?uploader=User1')
    assert response.status_code == 200
    
    images = json.loads(response.data)
    assert len(images) == 1
    assert images[0]['uploader'] == 'User1'

@patch('app.aws_services')
def test_filter_by_tags(mock_aws_module, client):
    """Test filtering by tags"""
    mock_aws_module.scan_items.return_value = [
        {'id': '1', 'uploader': 'User', 'tags': ['nature'], 'upload_date': '2025-01-01T00:00:00+00:00'},
        {'id': '2', 'uploader': 'User', 'tags': ['urban'], 'upload_date': '2025-01-02T00:00:00+00:00'}
    ]
    
    response = client.get('/api/images?tags=nature')
    assert response.status_code == 200
    
    images = json.loads(response.data)
    assert len(images) == 1
    assert 'nature' in images[0]['tags']

@patch('app.aws_services')
def test_get_image(mock_aws_module, client):
    """Test getting image metadata"""
    mock_aws_module.get_item.return_value = {
        'id': 'test-id',
        'filename': 'test.jpg',
        'uploader': 'Test User'
    }
    
    response = client.get('/api/images/test-id')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['id'] == 'test-id'
    assert data['uploader'] == 'Test User'

@patch('app.aws_services')
def test_get_nonexistent_image(mock_aws_module, client):
    """Test getting non-existent image"""
    mock_aws_module.get_item.return_value = None
    
    response = client.get('/api/images/nonexistent')
    assert response.status_code == 404

@patch('app.aws_services')
def test_download_image(mock_aws_module, client):
    """Test downloading image"""
    mock_aws_module.get_item.return_value = {
        'id': 'test-id',
        'filename': 'test.jpg',
        's3_key': 'test.jpg'
    }
    mock_aws_module.download_from_s3.return_value = (b'image_data', 'image/jpeg')
    
    response = client.get('/api/images/test-id/file')
    assert response.status_code == 200
    assert response.content_type == 'image/jpeg'

@patch('app.aws_services')
def test_delete_image(mock_aws_module, client):
    """Test deleting image"""
    mock_aws_module.get_item.return_value = {
        'id': 'test-id',
        's3_key': 'test.jpg'
    }
    mock_aws_module.delete_from_s3.return_value = True
    mock_aws_module.delete_item.return_value = True
    
    response = client.delete('/api/images/test-id')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'deleted successfully' in data['message'].lower()

@patch('app.aws_services')
def test_delete_nonexistent_image(mock_aws_module, client):
    """Test deleting non-existent image"""
    mock_aws_module.get_item.return_value = None
    
    response = client.delete('/api/images/nonexistent')
    assert response.status_code == 404